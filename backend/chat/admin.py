from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from datetime import datetime, timedelta
import uuid
import json
import asyncio
from asgiref.sync import sync_to_async
from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt, ConversationSummary


# Custom form for message content
class MessageInlineForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = '__all__'
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'cols': 80, 'placeholder': 'Enter message content...'}),
        }


# Inline admin for messages within conversations
class MessageInline(admin.TabularInline):
    model = Message
    form = MessageInlineForm
    fields = ['sender_type', 'content', 'feedback', 'timestamp']
    readonly_fields = ['timestamp']
    extra = 0  # Don't show empty forms by default
    ordering = ['timestamp']
    
    def get_extra(self, request, obj=None, **kwargs):
        """Show empty forms for new conversations"""
        if obj is None:  # New conversation being created
            return 5  # Show 5 empty message forms for new conversations
        elif obj and obj.messages.count() == 0:  # Existing conversation with no messages
            return 3  # Show 3 empty forms for empty conversations
        return 1  # Show 1 empty form for existing conversations with messages
    
    def get_formset(self, request, obj=None, **kwargs):
        """Customize formset for better UX"""
        formset = super().get_formset(request, obj, **kwargs)
        if obj is None:  # New conversation
            # Pre-populate with sample conversation pattern
            formset.form.base_fields['sender_type'].initial = 'user'
        return formset


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['uuid_short', 'user_link', 'title_display', 'total_messages', 'analysis_summary', 'analysis_source_display', 'quality_score', 'issues_detected', 'satisfaction_level', 'created_at_local', 'is_active']
    list_filter = ['is_active', 'created_at', 'updated_at', 'satisfaction_score']
    search_fields = ['user__username', 'user__email', 'title']
    readonly_fields = [
        'uuid', 'created_at', 'updated_at', 'total_messages',
        'user_display_info', 'conversation_stats', 'technical_details'
    ]
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-updated_at']
    actions = ['add_sample_messages', 'analyze_with_langextract', 'bulk_analyze_langextract', 'auto_analyze_conversations']
    actions_selection_counter = True
    actions_on_top = True
    actions_on_bottom = False
    inlines = [MessageInline]  # Add inline message editing
    
    def get_object(self, request, object_id, from_field=None):
        """Override get_object to handle UUID lookup for security"""
        try:
            # Try to parse as UUID first
            uuid_obj = uuid.UUID(str(object_id))
            return self.get_queryset(request).get(uuid=uuid_obj)
        except (ValueError, TypeError):
            # Fallback to PK for backward compatibility
            try:
                return self.get_queryset(request).get(pk=object_id)
            except (ValueError, Conversation.DoesNotExist):
                return None
        except Conversation.DoesNotExist:
            return None
    
    def get_urls(self):
        """Override admin URLs with UUID-based ones for security"""
        from django.urls import path
        urls = super().get_urls()
        
        # Create wrapper views that convert UUID to string for admin compatibility
        def uuid_change_view(request, object_id):
            return self.change_view(request, str(object_id))
        
        def uuid_delete_view(request, object_id):
            return self.delete_view(request, str(object_id))
            
        def uuid_history_view(request, object_id):
            return self.history_view(request, str(object_id))
        
        # Override default admin URLs with UUID-based ones
        custom_urls = [
            path('<uuid:object_id>/change/', self.admin_site.admin_view(uuid_change_view), 
                 name='chat_conversation_change'),
            path('<uuid:object_id>/delete/', self.admin_site.admin_view(uuid_delete_view), 
                 name='chat_conversation_delete'),
            path('<uuid:object_id>/history/', self.admin_site.admin_view(uuid_history_view), 
                 name='chat_conversation_history'),
        ]
        return custom_urls + urls
    
    def response_change(self, request, obj):
        """Redirect to UUID-based URLs after form submission"""
        import re
        response = super().response_change(request, obj)
        if hasattr(response, 'url') and response.url:
            pattern = r'/admin/chat/conversation/\d+/'
            replacement = f'/admin/chat/conversation/{obj.uuid}/'
            response.url = re.sub(pattern, replacement, response.url)
        return response
    
    fieldsets = (
        (_('Conversation Details'), {
            'fields': ('user', 'title', 'is_active')
        }),
        (_('Analytics'), {
            'fields': ('satisfaction_score', 'langextract_analysis'),
            'classes': ('collapse',),
            'description': _('Analytics data will be populated automatically after analysis')
        }),
        (_('Metadata'), {
            'fields': (
                'uuid',
                ('created_at', 'updated_at'),
                'total_messages',
                'user_display_info',
                'conversation_stats',
                'technical_details'
            ),
            'description': _('Essential conversation metadata and technical information')
        })
    )
    
    def uuid_short(self, obj):
        """Display first 4 characters of UUID followed by ... as a clickable link"""
        url = reverse('admin:chat_conversation_change', args=[obj.uuid])
        uuid_display = f"{str(obj.uuid)[:4]}..."
        return format_html('<a href="{}">{}</a>', url, uuid_display)
    uuid_short.short_description = _('ID')
    uuid_short.admin_order_field = 'uuid'
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
    
    def title_display(self, obj):
        title = obj.get_title()
        return title[:50] + "..." if len(title) > 50 else title
    title_display.short_description = _('Title')
    
    def analysis_status(self, obj):
        try:
            analysis = obj.analysis
            if analysis:
                # Show sentiment with colored text (no emojis)
                colors = {'positive': 'green', 'negative': 'red', 'neutral': 'orange'}
                color = colors.get(analysis.sentiment, 'black')
                
                url = reverse('admin:analytics_conversationanalysis_change', args=[analysis.id])
                return format_html(
                    '<a href="{}" style="color: {}; font-weight: bold;">[{}]</a>', 
                    url, color, analysis.sentiment.upper()
                )
            else:
                return format_html('<span style="color: gray;">Not analyzed</span>')
        except Exception as e:
            # Add debugging to see why analysis isn't showing
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Analysis status check for conversation {obj.id}: {e}")
            try:
                # Check if analysis exists in database
                from analytics.models import ConversationAnalysis
                analysis_exists = ConversationAnalysis.objects.filter(conversation=obj).exists()
                logger.info(f"Analysis exists in database for conversation {obj.id}: {analysis_exists}")
            except Exception as db_error:
                logger.error(f"Database check failed: {db_error}")
            return format_html('<span style="color: gray;">Not analyzed</span>')
    analysis_status.short_description = _('Analysis Status')
    
    def analysis_summary(self, obj):
        """Display comprehensive conversation analysis summary from new structure"""
        if not obj.langextract_analysis or obj.langextract_analysis == {}:
            return format_html('<span style="color: #999;">Not analyzed</span>')
        
        analysis = obj.langextract_analysis
        
        # Try new structure first
        customer_insights = analysis.get('customer_insights', {})
        conversation_patterns = analysis.get('conversation_patterns', {})
        
        if (customer_insights and not customer_insights.get('fallback_used')) or (conversation_patterns and not conversation_patterns.get('fallback_used')):
            # New structure - extract from customer_insights and conversation_patterns
            total_messages = obj.total_messages  # Get from model method
            user_messages = obj.messages.filter(sender_type='user').count()
            
            # Get issues from customer_insights
            if customer_insights and not customer_insights.get('fallback_used'):
                issue_extraction = customer_insights.get('issue_extraction', {})
                primary_issues = issue_extraction.get('primary_issues', [])
                total_issues = len(primary_issues)
                
                sentiment_analysis = customer_insights.get('sentiment_analysis', {})
                avg_satisfaction = sentiment_analysis.get('satisfaction_score', 0)
                
                urgency_assessment = customer_insights.get('urgency_assessment', {})
                urgency_level = urgency_assessment.get('urgency_level', 'medium')
                urgent_count = 1 if urgency_level in ['high', 'critical'] else 0
            else:
                total_issues = 0
                avg_satisfaction = 0
                urgent_count = 0
        else:
            # Fallback to old structure
            message_counts = analysis.get('message_counts', {})
            total_messages = message_counts.get('total_messages', 0)
            user_messages = message_counts.get('user_messages', 0)
            
            issue_analysis = analysis.get('issue_analysis', {})
            total_issues = issue_analysis.get('total_issues_detected', 0)
            
            satisfaction_analysis = analysis.get('satisfaction_analysis', {})
            avg_satisfaction = satisfaction_analysis.get('average_satisfaction_score', 0)
            
            importance_analysis = analysis.get('importance_analysis', {})
            urgent_count = importance_analysis.get('urgent_messages_count', 0)
        
        # Build summary with color coding
        summary_parts = []
        summary_parts.append(f'{total_messages} msgs')
        
        if total_issues > 0:
            color = 'red' if total_issues > 2 else 'orange'
            summary_parts.append(f'<span style="color: {color};">{total_issues} issues</span>')
        
        if avg_satisfaction > 0:
            if avg_satisfaction >= 7:
                color = 'green'
                icon = '[+]'
            elif avg_satisfaction >= 5:
                color = 'orange' 
                icon = '[~]'
            else:
                color = 'red'
                icon = '[-]'
            summary_parts.append(f'<span style="color: {color};">{icon} {avg_satisfaction:.1f}</span>')
        
        if urgent_count > 0:
            summary_parts.append(f'<span style="color: red; font-weight: bold;">{urgent_count} urgent</span>')
        
        return format_html(' | '.join(summary_parts))
    analysis_summary.short_description = _('Analysis Summary')
    
    def analysis_source_display(self, obj):
        """Display the source of analysis (LLM model or Local)"""
        if not obj.langextract_analysis or obj.langextract_analysis == {}:
            return format_html('<span style="color: #999;">Not analyzed</span>')
        
        analysis = obj.langextract_analysis
        analysis_source = analysis.get('analysis_source', 'Missing Source')
        analysis_method = analysis.get('analysis_method', 'unknown')
        
        # Color coding for different sources
        if 'LLM' in analysis_source or 'gemini' in analysis_source.lower() or 'LangExtract' in analysis_source:
            # LLM analysis - green
            color = 'green'
            icon = '🤖'
        elif 'Local' in analysis_source:
            # Local analysis - blue  
            color = 'blue'
            icon = '🔧'
        elif 'Fallback' in analysis_source or 'Emergency' in analysis_source:
            # Fallback analysis - orange
            color = 'orange'
            icon = '⚠️'
        elif analysis_source == 'Missing Source':
            # Missing source - red (shouldn't happen after fix)
            color = 'red'
            icon = '❌'
            analysis_source = 'Missing Source'
        else:
            # Unknown/other - gray
            color = 'gray'
            icon = '❓'
        
        # Display with icon and color
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, analysis_source
        )
    analysis_source_display.short_description = _('Analysis Source')
    
    def quality_score(self, obj):
        """Display conversation quality metrics from new analysis structure"""
        if not obj.langextract_analysis or obj.langextract_analysis == {}:
            return format_html('<span style="color: #999;">-</span>')
        
        analysis = obj.langextract_analysis
        
        # Try new structure first (conversation_patterns)
        conversation_patterns = analysis.get('conversation_patterns', {})
        if conversation_patterns and not conversation_patterns.get('fallback_used'):
            conversation_flow = conversation_patterns.get('conversation_flow', {})
            overall_quality = conversation_flow.get('conversation_quality', 0)
            
            # Convert 1-10 scale to percentage
            overall_quality = (overall_quality * 10) if overall_quality <= 10 else overall_quality
        else:
            # Fallback to old structure if available
            quality_metrics = analysis.get('quality_metrics', {})
            completeness = quality_metrics.get('conversation_completeness_score', 0)
            engagement = quality_metrics.get('user_engagement_score', 0)
            analysis_coverage = quality_metrics.get('message_analysis_coverage', 0)
            
            # Calculate overall quality score
            overall_quality = (completeness + engagement + analysis_coverage) / 3 if any([completeness, engagement, analysis_coverage]) else 0
        
        if overall_quality >= 80:
            color = 'green'
            rating = _('Excellent')
        elif overall_quality >= 60:
            color = 'orange'
            rating = _('Good')
        elif overall_quality >= 40:
            color = 'blue'
            rating = _('Average')
        else:
            color = 'red'
            rating = _('Poor')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>{}%</small>',
            color, rating, int(overall_quality)
        )
    quality_score.short_description = _('Quality')
    
    def issues_detected(self, obj):
        """Display detected issues summary"""
        if not obj.langextract_analysis or obj.langextract_analysis == {}:
            return format_html('<span style="color: #999;">-</span>')
        
        analysis = obj.langextract_analysis
        issue_analysis = analysis.get('issue_analysis', {})
        total_issues = issue_analysis.get('total_issues_detected', 0)
        top_issues = issue_analysis.get('top_issues', [])
        
        if total_issues == 0:
            return format_html('<span style="color: green;">{}</span>', _('No issues'))
        
        # Show top 2 issues
        issue_display = []
        for i, (issue_type, data) in enumerate(top_issues[:2]):
            count = data['count']
            confidence = data.get('average_confidence', 0)
            color = 'red' if confidence > 70 else 'orange' if confidence > 40 else 'gray'
            
            # Translate issue types
            issue_translations = {
                'question': _('Question'),
                'technical_critical_hardware': _('Critical Hardware Issue'),
                'technical_urgent': _('Urgent Technical Issue'),
                'technical_problem': _('Technical Problem'),
                'billing_issue': _('Billing Issue'),
                'login_problem': _('Login Problem'),
                'performance_issue': _('Performance Issue'),
                'security_concern': _('Security Concern'),
                'feature_request': _('Feature Request'),
                'integration_issue': _('Integration Issue'),
                'data_issue': _('Data Issue'),
                'documentation_gap': _('Documentation Gap'),
                'ui_ux_feedback': _('UI/UX Feedback'),
            }
            
            translated_issue = issue_translations.get(issue_type, issue_type)
            
            issue_display.append(f'<span style="color: {color};">{translated_issue} ({count})</span>')
        
        result = '<br>'.join(issue_display)
        if len(top_issues) > 2:
            remaining = sum(data['count'] for _, data in top_issues[2:])
            result += f'<br><small style="color: #666;">+{remaining} more</small>'
        
        return format_html(result)
    issues_detected.short_description = _('Issues Detected')
    
    def satisfaction_level(self, obj):
        """Display conversation satisfaction analysis from new structure"""
        if not obj.langextract_analysis or obj.langextract_analysis == {}:
            return format_html('<span style="color: #999;">-</span>')
        
        analysis = obj.langextract_analysis
        
        # Try new structure first (customer_insights)
        customer_insights = analysis.get('customer_insights', {})
        if customer_insights and not customer_insights.get('fallback_used'):
            sentiment_analysis = customer_insights.get('sentiment_analysis', {})
            avg_score = sentiment_analysis.get('satisfaction_score', 0)
            overall_sentiment = sentiment_analysis.get('overall_sentiment', 'neutral')
            
            # Map sentiment to satisfaction percentages
            if overall_sentiment in ['very_positive', 'positive']:
                satisfied_pct = 80 if overall_sentiment == 'very_positive' else 65
                dissatisfied_pct = 5
            elif overall_sentiment in ['very_negative', 'negative']:
                satisfied_pct = 5
                dissatisfied_pct = 80 if overall_sentiment == 'very_negative' else 65
            else:  # neutral
                satisfied_pct = 50
                dissatisfied_pct = 20
        else:
            # Fallback to old structure if available
            satisfaction_analysis = analysis.get('satisfaction_analysis', {})
            avg_score = satisfaction_analysis.get('average_satisfaction_score', 0)
            percentages = satisfaction_analysis.get('satisfaction_percentage', {})
            satisfied_pct = percentages.get('satisfied', 0)
            dissatisfied_pct = percentages.get('dissatisfied', 0)
        
        # Determine overall satisfaction level
        if satisfied_pct > 50:
            level = _('Satisfied')
            color = 'green'
        elif dissatisfied_pct > 30:
            level = _('Dissatisfied')  
            color = 'red'
        elif satisfied_pct > 20:
            level = _('Mixed')
            color = 'orange'
        else:
            level = _('Neutral')
            color = 'blue'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>Score: {} | {}% satisfied</small>',
            color, level, f'{avg_score:.1f}', int(satisfied_pct)
        )
    satisfaction_level.short_description = _('Satisfaction')
    
    def created_at_local(self, obj):
        """Display created_at converted from UTC to user's local timezone"""
        if not obj.created_at:
            return None
        # Convert the stored UTC time to the current user's local time
        # The middleware will have activated the correct timezone for this request
        localized_time = timezone.localtime(obj.created_at)
        
        # Format with timezone info for clarity
        return localized_time.strftime('%Y-%m-%d %H:%M:%S %Z')
    
    created_at_local.admin_order_field = 'created_at'
    created_at_local.short_description = _('Created At')
    
    def user_display_info(self, obj):
        """Display comprehensive user information"""
        user = obj.user
        user_info = [
            f"<strong>Username:</strong> {user.username}",
            f"<strong>Email:</strong> {user.email or 'Not provided'}",
            f"<strong>Full Name:</strong> {user.get_full_name() or 'Not provided'}",
            f"<strong>User ID:</strong> {user.id}",
            f"<strong>Active:</strong> {'Yes' if user.is_active else 'No'}",
            f"<strong>Staff:</strong> {'Yes' if user.is_staff else 'No'}",
            f"<strong>Last Login:</strong> {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}",
            f"<strong>Date Joined:</strong> {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        return format_html('<br>'.join(user_info))
    user_display_info.short_description = _('User Information')
    
    def conversation_stats(self, obj):
        """Display conversation statistics and metrics"""
        messages = obj.messages.all()
        user_messages = messages.filter(sender_type='user')
        bot_messages = messages.filter(sender_type='bot')
        
        # Calculate conversation duration
        if messages.exists():
            first_message = messages.order_by('timestamp').first()
            last_message = messages.order_by('timestamp').last()
            duration = last_message.timestamp - first_message.timestamp
            duration_hours = duration.total_seconds() / 3600
        else:
            duration_hours = 0
        
        # Calculate average response times
        response_times = [msg.response_time for msg in bot_messages if msg.response_time]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate feedback stats
        positive_feedback = messages.filter(feedback='positive').count()
        negative_feedback = messages.filter(feedback='negative').count()
        
        stats_info = [
            f"<strong>Total Messages:</strong> {messages.count()}",
            f"<strong>User Messages:</strong> {user_messages.count()}",
            f"<strong>Bot Messages:</strong> {bot_messages.count()}",
            f"<strong>Conversation Duration:</strong> {duration_hours:.2f} hours",
            f"<strong>Average Response Time:</strong> {avg_response_time:.2f}s",
            f"<strong>Positive Feedback:</strong> {positive_feedback}",
            f"<strong>Negative Feedback:</strong> {negative_feedback}",
            f"<strong>Satisfaction Score:</strong> {obj.satisfaction_score or 'Not calculated'}",
        ]
        return format_html('<br>'.join(stats_info))
    conversation_stats.short_description = _('Conversation Statistics')
    
    def technical_details(self, obj):
        """Display technical metadata and system information"""
        # Get latest message metadata for LLM info
        latest_bot_message = obj.messages.filter(sender_type='bot').order_by('-timestamp').first()
        
        # Calculate total tokens if available
        total_tokens = sum(msg.tokens_used for msg in obj.messages.all() if msg.tokens_used)
        
        technical_info = [
            f"<strong>Conversation UUID:</strong> <code>{obj.uuid}</code>",
            f"<strong>Database ID:</strong> {obj.id}",
            f"<strong>Status:</strong> {'Active' if obj.is_active else 'Inactive'}",
            f"<strong>Title Generated:</strong> {obj.get_title()}",
            f"<strong>Last Updated:</strong> {obj.updated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"<strong>Created:</strong> {obj.created_at.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"<strong>Total Tokens Used:</strong> {total_tokens or 'Not tracked'}",
        ]
        
        if latest_bot_message:
            technical_info.extend([
                f"<strong>Latest LLM Model:</strong> {latest_bot_message.llm_model_used or 'Not recorded'}",
                f"<strong>Latest Response Time:</strong> {latest_bot_message.response_time or 0}s",
                f"<strong>Latest Message Tokens:</strong> {latest_bot_message.tokens_used or 'Not tracked'}"
            ])
        
        # Add LangExtract analysis info if available
        if obj.langextract_analysis:
            technical_info.extend([
                "<strong>LangExtract Analysis:</strong> Available",
                f"<strong>Analysis Data Size:</strong> {len(str(obj.langextract_analysis))} characters"
            ])
        else:
            technical_info.append("<strong>LangExtract Analysis:</strong> Not analyzed")
        
        return format_html('<br>'.join(technical_info))
    technical_details.short_description = _('Technical Details')
    
    def add_sample_messages(self, request, queryset):
        """Admin action to quickly add sample messages to empty conversations"""
        from django.contrib import messages
        
        # Filter to only empty conversations
        empty_conversations = queryset.filter(messages__isnull=True).distinct()
        
        if not empty_conversations.exists():
            messages.warning(request, "No empty conversations selected. All selected conversations already have messages.")
            return
        
        # Sample conversation templates
        message_templates = [
            {
                'content': "Hi, I need help with my account. I'm having some issues.",
                'sender_type': 'user'
            },
            {
                'content': "Of course! I'd be happy to help you with your account. What specific issue are you experiencing?",
                'sender_type': 'bot'
            },
            {
                'content': "I can't access my dashboard and I'm getting error messages. This is quite frustrating.",
                'sender_type': 'user'
            },
            {
                'content': "I understand your frustration. Let me help you resolve this dashboard access issue step by step. First, let's try clearing your browser cache.",
                'sender_type': 'bot'
            },
            {
                'content': "That worked perfectly! Thank you so much for your help. The dashboard is loading fine now.",
                'sender_type': 'user'
            }
        ]
        
        added_count = 0
        for conversation in empty_conversations:
            # Add sample messages to each conversation
            for template in message_templates:
                Message.objects.create(
                    conversation=conversation,
                    content=template['content'],
                    sender_type=template['sender_type']
                )
            added_count += 1
        
        messages.success(
            request, 
            f"Added sample messages to {added_count} conversations. "
            f"Each conversation now has {len(message_templates)} messages ready for LangExtract analysis."
        )
    add_sample_messages.short_description = _("Add Sample Messages to Empty Conversations")
    
    def analyze_with_langextract(self, request, queryset):
        """Admin action to analyze selected conversations with LangExtract"""
        try:
            from analytics.langextract_service import LangExtractService
            from django.contrib import messages
            import threading
            import time
            
            # Get initial count and show immediate feedback
            conversation_count = queryset.count()
            
            # Quick validation first to give immediate feedback
            if conversation_count == 0:
                messages.error(request, "No conversations selected for analysis.")
                return
            
            service = LangExtractService()
            
            # Check configuration with detailed feedback
            if not service.is_configured():
                config_status = service.get_configuration_status()
                if not config_status['langextract_installed']:
                    messages.error(
                        request, 
                        'LangExtract library not installed. Please install with: pip install langextract'
                    )
                elif not config_status['api_key_configured']:
                    messages.error(
                        request, 
                        'API key not configured. Please set up API keys in Admin → API Configurations first.'
                    )
                else:
                    messages.error(
                        request, 
                        f'LangExtract not properly configured. Status: {config_status}'
                    )
                return
            
            # Filter out empty conversations before processing
            conversation_ids = list(queryset.values_list('id', flat=True))
            empty_conversations = []
            valid_conversations = []
            
            for conv_id in conversation_ids:
                conv = queryset.get(id=conv_id)
                if conv.messages.count() == 0:
                    empty_conversations.append(conv_id)
                else:
                    valid_conversations.append(conv_id)
            
            if empty_conversations:
                messages.warning(
                    request,
                    f"Skipping {len(empty_conversations)} empty conversation(s). "
                    f"Use 'Add Sample Messages' first for conversations without messages."
                )
            
            if not valid_conversations:
                messages.error(
                    request,
                    "No conversations with messages found to analyze. Please add messages first."
                )
                return
            
            # Initialize progress tracking in session
            request.session['langextract_progress'] = {
                'status': 'starting',
                'current_step': 'Initializing analysis...',
                'processed': 0,
                'total': len(valid_conversations),
                'errors': [],
                'success_count': 0,
                'error_count': 0
            }
            request.session.save()
            
            # Show immediate success message that processing started
            messages.success(
                request,
                f"LangExtract analysis started in background! Processing {len(valid_conversations)} conversation(s). "
                f"Using model: {service.default_model}. You can monitor progress in real-time. "
                f"The analysis will continue even if you navigate away from this page."
            )
            
            # Store session key for background thread
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            
            # Start background processing thread
            def background_analysis():
                """Run analysis in background thread"""
                try:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Background thread started for {len(valid_conversations)} conversations")
                    
                    # Import Django session engine
                    from django.contrib.sessions.backends.db import SessionStore
                    
                    # Create a new session store with the same key
                    session = SessionStore(session_key=session_key)
                    logger.info(f"Session recreated in background thread: {session_key}")
                    
                    # Create a mock request object for the background thread
                    class MockRequest:
                        def __init__(self, session):
                            self.session = session
                    
                    mock_request = MockRequest(session)
                    
                    # Run the analysis with the mock request
                    logger.info("Starting LangExtract analysis in background thread...")
                    service.bulk_analyze_conversations_with_progress(valid_conversations, mock_request)
                    logger.info("Background analysis completed successfully")
                    
                except Exception as e:
                    # Update progress with error status
                    try:
                        from django.contrib.sessions.backends.db import SessionStore
                        session = SessionStore(session_key=session_key)
                        progress = session.get('langextract_progress', {})
                        progress['status'] = 'error'
                        progress['current_step'] = f'Background analysis failed: {str(e)}'
                        session['langextract_progress'] = progress
                        session.save()
                    except Exception as session_error:
                        # Log the error if session update fails
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Background analysis failed: {e}")
                        logger.error(f"Session update failed: {session_error}")
            
            # Start the background thread
            thread = threading.Thread(target=background_analysis)
            thread.daemon = True  # Dies when main program dies
            thread.start()
            
            # Return immediately - don't wait for processing to complete
            return
                
        except ImportError as e:
            messages.error(
                request, 
                f"LangExtract library not available: {e}. Please install with: pip install langextract"
            )
        except Exception as e:
            messages.error(
                request, 
                f"Unexpected error during analysis: {type(e).__name__}: {str(e)}"
            )
            messages.info(
                request,
                "Check Django server logs for detailed error information."
            )
            
    analyze_with_langextract.short_description = _('Analyze with LangExtract')
    
    def verify_api_connection(self, request, queryset):
        """Verify LangExtract API connection and show network details"""
        from django.contrib import messages
        from analytics.langextract_service import LangExtractService
        import logging
        
        # Enable verbose logging
        logging.getLogger('analytics.langextract_service').setLevel(logging.INFO)
        
        service = LangExtractService()
        config_status = service.get_configuration_status()
        
        messages.info(request, f"LangExtract Configuration Status: {config_status}")
        
        # Additional debugging
        try:
            import langextract as lx
            messages.info(request, f"LangExtract library version: {getattr(lx, '__version__', 'unknown')}")
        except ImportError as e:
            messages.error(request, f"LangExtract import failed: {e}")
            return
        
        # Check API key format
        if service.api_key:
            key_preview = f"{service.api_key[:8]}...{service.api_key[-4:]}" if len(service.api_key) > 12 else "short_key"
            messages.info(request, f"API key format check: {key_preview} (length: {len(service.api_key)})")
            
            # Check if it looks like a valid Gemini key
            if service.api_key.startswith('AIza'):
                messages.info(request, "API key format: Valid Gemini key format detected")
            else:
                messages.warning(request, f"API key format: Does not look like Gemini key (starts with: {service.api_key[:4]})")
        
        if not service.is_configured():
            messages.error(request, "LangExtract not configured. Cannot test API connection.")
            return
        
        # Test with a simple conversation from selected items
        selected_conversation = queryset.first()
        if not selected_conversation or selected_conversation.messages.count() == 0:
            messages.warning(request, "Please select a conversation with messages to test API connection.")
            return
        
        try:
            # Get conversation messages
            messages_list = []
            for msg in selected_conversation.messages.all():
                messages_list.append({
                    'role': 'user' if msg.sender_type == 'user' else 'assistant',
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                })
            
            # Test the analysis - this will generate detailed logs
            result = service.analyze_conversation(messages_list)
            
            # Add detailed debugging
            messages.info(request, f"Analysis result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            messages.info(request, f"Analysis version: {result.get('analysis_version', 'No version found')}")
            
            if result.get('analysis_version') == 'langextract_v1.0':
                messages.success(request, 
                    "API Connection Verified: Real LangExtract API was successfully called. "
                    f"Model used: {result.get('model_used', 'Unknown')}. "
                    "Check Django logs for detailed network activity.")
            elif result.get('analysis_version') == 'simulated_v1.0':
                messages.warning(request, 
                    "Using Simulated Analysis: LangExtract library not installed or API call failed. "
                    "Check Django logs for error details.")
                
                # Add more debugging info
                if 'error' in result:
                    messages.error(request, f"Specific error: {result.get('error')}")
                    
            else:
                messages.error(request, 
                    f"Unexpected result: {result.get('analysis_version', 'Unknown version')}. "
                    f"Full result: {str(result)[:200]}... "
                    "Check Django logs for details.")
                    
        except Exception as e:
            messages.error(request, f"API connection test failed: {e}")
    
    verify_api_connection.short_description = _('Verify API Connection')
    
    def bulk_analyze_langextract(self, request, queryset):
        """Admin action to bulk analyze unanalyzed conversations"""
        try:
            from analytics.langextract_service import LangExtractService
            
            service = LangExtractService()
            if not service.is_configured():
                self.message_user(
                    request,
                    _('LangExtract not configured. Please set up API keys first.'),
                    level='ERROR'
                )
                return
            
            # Analyze all conversations without analysis
            result = service.bulk_analyze_conversations()
            
            if result['success'] > 0:
                self.message_user(
                    request,
                    f"Bulk analysis completed: {result['success']} successful, {result['failed']} failed.",
                    level='SUCCESS' if result['failed'] == 0 else 'WARNING'
                )
            else:
                self.message_user(
                    request,
                    f"Bulk analysis failed: {result.get('error', 'Unknown error')}",
                    level='ERROR'
                )
        except ImportError as e:
            self.message_user(
                request,
                f"LangExtract service not available: {e}",
                level='ERROR'
            )
        except Exception as e:
            self.message_user(
                request,
                f"Bulk analysis error: {e}",
                level='ERROR'
            )
    bulk_analyze_langextract.short_description = _('Bulk Analyze Unanalyzed Conversations')
    
    def auto_analyze_conversations(self, request, queryset):
        """Admin action to automatically analyze conversations using the new automatic analysis service"""
        from django.contrib import messages
        import asyncio
        import threading
        
        try:
            from core.services.automatic_analysis_service import automatic_analysis_service
            
            conversation_count = queryset.count()
            
            if conversation_count == 0:
                messages.error(request, "No conversations selected for automatic analysis.")
                return
            
            # Show immediate success message
            messages.success(
                request,
                f"Automatic analysis started for {conversation_count} conversation(s)! "
                f"The system will analyze conversations that meet the criteria (3+ messages, inactive for 5+ minutes). "
                f"Results will be saved to the database automatically."
            )
            
            def background_auto_analysis():
                """Run automatic analysis in background thread"""
                try:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Starting automatic analysis for {conversation_count} conversations")
                    
                    success_count = 0
                    skipped_count = 0
                    error_count = 0
                    
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        for conversation in queryset:
                            try:
                                # Trigger analysis if needed
                                result = loop.run_until_complete(
                                    automatic_analysis_service.trigger_analysis_if_needed(conversation)
                                )
                                
                                if result:
                                    success_count += 1
                                    logger.info(f"Analyzed conversation {conversation.uuid}")
                                else:
                                    skipped_count += 1
                                    logger.debug(f"Skipped conversation {conversation.uuid}")
                                    
                            except Exception as e:
                                error_count += 1
                                logger.error(f"Error analyzing conversation {conversation.uuid}: {e}")
                        
                        logger.info(f"Automatic analysis completed: {success_count} analyzed, {skipped_count} skipped, {error_count} errors")
                        
                    finally:
                        loop.close()
                        
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Background automatic analysis failed: {e}")
            
            # Start background thread
            thread = threading.Thread(target=background_auto_analysis)
            thread.daemon = True
            thread.start()
            
        except ImportError as e:
            messages.error(
                request,
                f"Automatic analysis service not available: {e}"
            )
        except Exception as e:
            messages.error(
                request,
                f"Error starting automatic analysis: {e}"
            )
    
    auto_analyze_conversations.short_description = _('Auto-Analyze with Smart Criteria')


# Custom filters for message analysis
class IssueTypeFilter(admin.SimpleListFilter):
    title = _('Filter by Issue Type')
    parameter_name = 'issue_type'

    def lookups(self, request, model_admin):
        return (
            ('login_problems', _('Issue Type: Login Problems')),
            ('billing_issues', _('Issue Type: Billing Issues')),
            ('technical_problems', _('Issue Type: Technical Problems')),
            ('feature_requests', _('Issue Type: Feature Requests')),
            ('integration_issues', _('Issue Type: Integration Issues')),
            ('performance_issues', _('Issue Type: Performance Issues')),
            ('data_issues', _('Issue Type: Data Issues')),
            ('ui_ux_feedback', _('Issue Type: UI/UX Feedback')),
            ('documentation_gaps', _('Issue Type: Documentation Gaps')),
            ('security_concerns', _('Issue Type: Security Concerns')),
        )

    def queryset(self, request, queryset):
        if self.value():
            issue_type_map = {
                'login_problems': 'Login Problems',
                'billing_issues': 'Billing Issues',
                'technical_problems': 'Technical Problems',
                'feature_requests': 'Feature Requests',
                'integration_issues': 'Integration Issues',
                'performance_issues': 'Performance Issues',
                'data_issues': 'Data Issues',
                'ui_ux_feedback': 'UI/UX Feedback',
                'documentation_gaps': 'Documentation Gaps',
                'security_concerns': 'Security Concerns',
            }
            issue_name = issue_type_map.get(self.value())
            if issue_name:
                return queryset.filter(message_analysis__issues_raised__contains=[{'issue_type': issue_name}])
        return queryset


class SatisfactionLevelFilter(admin.SimpleListFilter):
    title = _('Filter by Satisfaction')
    parameter_name = 'satisfaction_level'

    def lookups(self, request, model_admin):
        return (
            ('satisfied', _('Satisfaction: Satisfied')),
            ('dissatisfied', _('Satisfaction: Dissatisfied')),
            ('neutral', _('Satisfaction: Neutral')),
            ('unknown', _('Satisfaction: Unknown')),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(message_analysis__satisfaction_level__level=self.value())
        return queryset


class ImportanceLevelFilter(admin.SimpleListFilter):
    title = _('Filter by Importance')
    parameter_name = 'importance_level'

    def lookups(self, request, model_admin):
        return (
            ('high', _('Importance: High')),
            ('medium', _('Importance: Medium')),
            ('low', _('Importance: Low')),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(message_analysis__importance_level__level=self.value())
        return queryset


class DocumentationPotentialFilter(admin.SimpleListFilter):
    title = _('Filter by Doc Potential')
    parameter_name = 'doc_potential'

    def lookups(self, request, model_admin):
        return (
            ('high', _('Doc Potential: High')),
            ('medium', _('Doc Potential: Medium')),
            ('low', _('Doc Potential: Low')),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(message_analysis__doc_improvement_potential__potential_level=self.value())
        return queryset


class FAQPotentialFilter(admin.SimpleListFilter):
    title = _('Filter by FAQ Potential')
    parameter_name = 'faq_potential'

    def lookups(self, request, model_admin):
        return (
            ('high', _('FAQ Potential: High')),
            ('medium', _('FAQ Potential: Medium')),
            ('low', _('FAQ Potential: Low')),
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(message_analysis__faq_potential__faq_potential=self.value())
        return queryset


class AnalysisStatusFilter(admin.SimpleListFilter):
    title = _('Filter by Analysis Status')
    parameter_name = 'analysis_status'

    def lookups(self, request, model_admin):
        return (
            ('analyzed', _('Analysis: Completed')),
            ('not_analyzed', _('Analysis: Not Done')),
            ('user_only', _('Type: User Messages Only')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'analyzed':
            return queryset.exclude(message_analysis__exact={})
        elif self.value() == 'not_analyzed':
            return queryset.filter(message_analysis__exact={})
        elif self.value() == 'user_only':
            return queryset.filter(sender_type='user')
        return queryset


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'uuid_short', 'conversation_link', 'sender_type', 'content_preview', 
        'feedback_display', 'analysis_source_message', 'issues_summary', 'satisfaction_display', 
        'importance_display', 'doc_potential_display', 'faq_potential_display', 'timestamp'
    ]
    list_filter = [
        'sender_type', 'feedback', AnalysisStatusFilter, IssueTypeFilter, 
        SatisfactionLevelFilter, ImportanceLevelFilter, DocumentationPotentialFilter, 
        FAQPotentialFilter, 'timestamp', 'llm_model_used'
    ]
    search_fields = [
        'content', 'conversation__user__username', 'conversation__title',
        'conversation__user__email', 'llm_model_used'
    ]
    readonly_fields = ['timestamp', 'response_time', 'message_analysis']
    list_per_page = 50
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        """Optimize queryset for admin performance"""
        return super().get_queryset(request).select_related('conversation__user')
    
    def get_object(self, request, object_id, from_field=None):
        """Override get_object to handle UUID lookup for security"""
        try:
            # Try to parse as UUID first
            uuid_obj = uuid.UUID(str(object_id))
            return self.get_queryset(request).get(uuid=uuid_obj)
        except (ValueError, TypeError):
            # Fallback to PK for backward compatibility
            try:
                return self.get_queryset(request).get(pk=object_id)
            except (ValueError, Message.DoesNotExist):
                return None
        except Message.DoesNotExist:
            return None
    
    def get_urls(self):
        """Override admin URLs with UUID-based ones for security"""
        from django.urls import path
        urls = super().get_urls()
        
        # Create wrapper views that convert UUID to string for admin compatibility
        def uuid_change_view(request, object_id):
            return self.change_view(request, str(object_id))
        
        def uuid_delete_view(request, object_id):
            return self.delete_view(request, str(object_id))
            
        def uuid_history_view(request, object_id):
            return self.history_view(request, str(object_id))
        
        # Custom UUID-based URLs (prioritized over default ones)
        custom_urls = [
            path('<uuid:object_id>/change/', uuid_change_view, name='chat_message_change'),
            path('<uuid:object_id>/delete/', uuid_delete_view, name='chat_message_delete'),
            path('<uuid:object_id>/history/', uuid_history_view, name='chat_message_history'),
        ]
        return custom_urls + urls
    
    def response_change(self, request, obj):
        """Redirect to UUID-based URLs after form submission"""
        import re
        response = super().response_change(request, obj)
        if hasattr(response, 'url') and response.url:
            pattern = r'/admin/chat/message/\d+/'
            replacement = f'/admin/chat/message/{obj.uuid}/'
            response.url = re.sub(pattern, replacement, response.url)
        return response
    
    def uuid_short(self, obj):
        """Display first 4 characters of UUID followed by ... as a clickable link"""
        url = reverse('admin:chat_message_change', args=[obj.uuid])
        uuid_display = f"{str(obj.uuid)[:4]}..."
        return format_html('<a href="{}">{}</a>', url, uuid_display)
    uuid_short.short_description = _('ID')
    uuid_short.admin_order_field = 'uuid'
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.uuid])
        title = obj.conversation.get_title()
        title_display = title[:30] + "..." if len(title) > 30 else title
        return format_html('<a href="{}" title="{}">{}</a>', url, title, title_display)
    conversation_link.short_description = _('Conversation')
    conversation_link.admin_order_field = 'conversation__title'
    
    def content_preview(self, obj):
        return obj.content[:60] + "..." if len(obj.content) > 60 else obj.content
    content_preview.short_description = _('Content')
    
    def feedback_display(self, obj):
        if obj.feedback == 'positive':
            return format_html('<span style="color: green; font-weight: bold;">+ Positive</span>')
        elif obj.feedback == 'negative':
            return format_html('<span style="color: red; font-weight: bold;">- Negative</span>')
        return _('-')
    feedback_display.short_description = _('Feedback')
    
    def analysis_source_message(self, obj):
        """Display analysis source for messages"""
        if not obj.message_analysis:
            return format_html('<span style="color: #999;">-</span>')
        
        analysis_source = obj.message_analysis.get('analysis_source', 'Missing')
        
        # Simplified display for message list
        if 'LLM' in analysis_source or 'gemini' in analysis_source.lower():
            return format_html('<span style="color: green; font-size: 11px;">🤖 LLM</span>')
        elif 'Local' in analysis_source:
            if 'Legacy' in analysis_source:
                return format_html('<span style="color: #4169E1; font-size: 11px;">🔧 Local (Legacy)</span>')
            else:
                return format_html('<span style="color: blue; font-size: 11px;">🔧 Local</span>')
        elif 'Fallback' in analysis_source:
            return format_html('<span style="color: orange; font-size: 11px;">⚠️ Fallback</span>')
        elif analysis_source == 'Missing':
            return format_html('<span style="color: red; font-size: 11px;">❌ Missing</span>')
        else:
            return format_html('<span style="color: gray; font-size: 11px;">❓ {}</span>', analysis_source[:10])
    analysis_source_message.short_description = _('Source')
    
    def issues_summary(self, obj):
        """Display summary of detected issues"""
        if not obj.message_analysis or not obj.message_analysis.get('issues_raised'):
            return format_html('<span style="color: #999;">{}</span>', _('No issues'))
        
        issues = obj.message_analysis.get('issues_raised', [])
        if not issues:
            return format_html('<span style="color: #999;">{}</span>', _('No issues'))
        
        # Show top 2 issues with confidence
        issue_summaries = []
        for issue in issues[:2]:
            issue_type = issue.get('issue_type', 'Unknown')
            confidence = issue.get('confidence', 0)
            color = 'red' if confidence > 70 else 'orange' if confidence > 40 else 'gray'
            
            # Translate issue types
            issue_translations = {
                'question': _('Question'),
                'technical_critical_hardware': _('Critical Hardware Issue'),
                'technical_urgent': _('Urgent Technical Issue'),
                'technical_problem': _('Technical Problem'),
                'billing_issue': _('Billing Issue'),
                'login_problem': _('Login Problem'),
                'performance_issue': _('Performance Issue'),
                'security_concern': _('Security Concern'),
                'feature_request': _('Feature Request'),
                'integration_issue': _('Integration Issue'),
                'data_issue': _('Data Issue'),
                'documentation_gap': _('Documentation Gap'),
                'ui_ux_feedback': _('UI/UX Feedback'),
            }
            translated_issue = issue_translations.get(issue_type, issue_type)
            
            issue_summaries.append(f'<span style="color: {color};">{translated_issue} ({confidence:.0f}%)</span>')
        
        result = '<br>'.join(issue_summaries)
        if len(issues) > 2:
            result += f'<br><small style="color: #666;">+{len(issues)-2} more</small>'
        
        return format_html(result)
    issues_summary.short_description = _('Issues Detected')
    
    def satisfaction_display(self, obj):
        """Display satisfaction level with visual indicators"""
        if not obj.message_analysis:
            return format_html('<span style="color: #999;">-</span>')
        
        satisfaction_data = obj.message_analysis.get('satisfaction_level', {})
        level = satisfaction_data.get('level', 'unknown')
        score = satisfaction_data.get('score', 0)
        confidence = satisfaction_data.get('confidence', 0)
        
        color_map = {
            'satisfied': 'green',
            'dissatisfied': 'red',
            'neutral': 'orange',
            'unknown': 'gray'
        }
        
        # Translation mapping for satisfaction levels
        level_translations = {
            'satisfied': _('Satisfied'),
            'dissatisfied': _('Dissatisfied'),
            'neutral': _('Neutral'),
            'unknown': _('Unknown')
        }
        
        color = color_map.get(level, 'gray')
        translated_level = level_translations.get(level, level.title())
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>{}: {} ({}%)</small>',
            color, translated_level, _('Score'), f'{score:.1f}', int(confidence)
        )
    satisfaction_display.short_description = _('Satisfaction')
    
    def importance_display(self, obj):
        """Display importance/urgency level"""
        if not obj.message_analysis:
            return format_html('<span style="color: #999;">-</span>')
        
        importance_data = obj.message_analysis.get('importance_level', {})
        level = importance_data.get('level', 'low')
        priority = importance_data.get('priority', 'low')
        urgency_score = importance_data.get('urgency_score', 0)
        
        color_map = {
            'high': 'red',
            'medium': 'orange',
            'low': 'green'
        }
        
        # Translation mapping for importance levels
        level_translations = {
            'high': _('High'),
            'medium': _('Medium'),
            'low': _('Low'),
            'critical': _('Critical'),
            'normal': _('Normal'),
            'urgent': _('Urgent'),
            'technical': _('Technical'),
            'hardware': _('Hardware'),
            'documentation': _('Documentation'),
            'question': _('Question')
        }
        
        color = color_map.get(level, 'gray')
        translated_level = level_translations.get(level, level)
        translated_priority = level_translations.get(priority, priority)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>{} {} ({})</small>',
            color, translated_level, translated_priority, _('priority'), urgency_score
        )
    importance_display.short_description = _('Importance')
    
    def doc_potential_display(self, obj):
        """Display documentation improvement potential"""
        if not obj.message_analysis:
            return format_html('<span style="color: #999;">-</span>')
        
        doc_data = obj.message_analysis.get('doc_improvement_potential', {})
        potential_level = doc_data.get('potential_level', 'low')
        score = doc_data.get('score', 0)
        improvement_areas = doc_data.get('improvement_areas', [])
        
        color_map = {
            'high': 'red',
            'medium': 'orange',
            'low': 'green'
        }
        
        # Translation mapping for potential levels
        level_translations = {
            'high': _('High'),
            'medium': _('Medium'),
            'low': _('Low')
        }
        
        color = color_map.get(potential_level, 'gray')
        translated_level = level_translations.get(potential_level, potential_level.title())
        areas_text = ', '.join(improvement_areas[:2]) if improvement_areas else _('None')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span><br><small>{}% - {}</small>',
            color, translated_level, score, areas_text[:30] + '...' if len(str(areas_text)) > 30 else areas_text
        )
    doc_potential_display.short_description = _('Doc Potential')
    
    def faq_potential_display(self, obj):
        """Display FAQ potential"""
        if not obj.message_analysis:
            return format_html('<span style="color: #999;">-</span>')
        
        faq_data = obj.message_analysis.get('faq_potential', {})
        potential_level = faq_data.get('faq_potential', 'low')
        score = faq_data.get('score', 0)
        question_type = faq_data.get('question_type', 'other')
        should_add = faq_data.get('should_add_to_faq', False)
        
        color_map = {
            'high': 'red',
            'medium': 'orange',
            'low': 'green'
        }
        
        # Translation mapping for potential levels
        level_translations = {
            'high': _('High'),
            'medium': _('Medium'),
            'low': _('Low')
        }
        
        color = color_map.get(potential_level, 'gray')
        translated_level = level_translations.get(potential_level, potential_level.title())
        add_indicator = ' [ADD]' if should_add else ''
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span><br><small>{}% - {}</small>',
            color, translated_level, add_indicator, score, question_type.replace('_', ' ').title()
        )
    faq_potential_display.short_description = _('FAQ Potential')


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['uuid_short', 'user_link', 'session_id_short', 'total_conversations', 'total_messages_sent', 'duration', 'started_at', 'is_active']
    list_filter = ['is_active', 'started_at', 'ended_at']
    search_fields = ['user__username', 'session_id']
    readonly_fields = ['started_at', 'ended_at']
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    
    def uuid_short(self, obj):
        """Display first 4 characters of UUID followed by ..."""
        return f"{str(obj.uuid)[:4]}..."
    uuid_short.short_description = _('ID')
    uuid_short.admin_order_field = 'uuid'
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
    
    def session_id_short(self, obj):
        return obj.session_id[:20] + "..." if len(obj.session_id) > 20 else obj.session_id
    session_id_short.short_description = _('Session ID')
    
    def duration(self, obj):
        if obj.ended_at and obj.started_at:
            delta = obj.ended_at - obj.started_at
            hours = delta.total_seconds() // 3600
            minutes = (delta.total_seconds() % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"
        elif obj.is_active:
            return _("Active")
        return _("Unknown")
    duration.short_description = _('Duration')




class APIConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for API configuration management"""
    list_display = ['provider_display', 'model_name_display', 'is_active_display', 'api_key_preview', 'updated_at_display']
    list_filter = ['provider', 'is_active', 'updated_at']
    search_fields = ['provider', 'model_name']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 20
    ordering = ['provider']
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "model_name":
            kwargs['widget'] = forms.TextInput(attrs={'placeholder': _('Input Model Name')})
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    fieldsets = (
        (_('Provider Information'), {
            'fields': ('provider', 'model_name', 'is_active')
        }),
        (_('API Settings'), {
            'fields': ('api_key',),
            'description': _('Configure API parameters for this provider')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def provider_display(self, obj):
        return obj.get_provider_display()
    provider_display.short_description = _('Provider')
    provider_display.admin_order_field = 'provider'
    
    def model_name_display(self, obj):
        return obj.model_name
    model_name_display.short_description = _('Model Name')
    model_name_display.admin_order_field = 'model_name'
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.short_description = _('Is Active')
    is_active_display.admin_order_field = 'is_active'
    is_active_display.boolean = True
    
    def updated_at_display(self, obj):
        if not obj.updated_at:
            return None
        # Use timezone-aware formatting with middleware-activated timezone
        localized_time = timezone.localtime(obj.updated_at)
        return localized_time.strftime('%Y-%m-%d %H:%M %Z')
    updated_at_display.short_description = _('Updated At')
    updated_at_display.admin_order_field = 'updated_at'
    
    def api_key_preview(self, obj):
        """Show masked preview of API key"""
        if obj.api_key:
            if len(obj.api_key) > 10:
                return f"{obj.api_key[:6]}...{obj.api_key[-4:]}"
            else:
                return f"{obj.api_key[:3]}..."
        return "-"
    api_key_preview.short_description = _('API Key')

# Register APIConfiguration
admin.site.register(APIConfiguration, APIConfigurationAdmin)




@admin.register(AdminPrompt)
class AdminPromptAdmin(admin.ModelAdmin):
    """Admin interface for admin prompt management"""
    list_display = [
        'name_display', 'prompt_type_display', 'language_display', 
        'is_default_display', 'is_active_display', 'usage_count_display', 'created_by_display', 'updated_at_display'
    ]
    list_filter = ['prompt_type', 'language', 'is_active', 'is_default', 'created_at', 'created_by']
    search_fields = ['name', 'prompt_text', 'description']
    readonly_fields = ['usage_count', 'last_used', 'created_at', 'updated_at']
    list_per_page = 25
    ordering = ['prompt_type', 'language', '-is_default', 'name']
    
    fieldsets = (
        (_('Prompt Information'), {
            'fields': ('name', 'prompt_type', 'language', 'description')
        }),
        (_('Prompt Content'), {
            'fields': ('prompt_text',),
            'description': _('The actual prompt text that will be sent to the LLM')
        }),
        (_('Settings'), {
            'fields': ('is_active', 'is_default'),
            'description': _('Only one default prompt per type and language is allowed')
        }),
        (_('Usage Statistics'), {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def name_display(self, obj):
        return obj.name
    name_display.short_description = _('Name')
    name_display.admin_order_field = 'name'
    
    def prompt_type_display(self, obj):
        return obj.get_prompt_type_display()
    prompt_type_display.short_description = _('Prompt Type')
    prompt_type_display.admin_order_field = 'prompt_type'
    
    def language_display(self, obj):
        return obj.get_language_display()
    language_display.short_description = _('Language')
    language_display.admin_order_field = 'language'
    
    def is_default_display(self, obj):
        if obj.is_default:
            return format_html('<span style="color: green; font-weight: bold;">✓ Default</span>')
        return format_html('<span style="color: gray;">-</span>')
    is_default_display.short_description = _('Is Default')
    is_default_display.admin_order_field = 'is_default'
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.short_description = _('Is Active')
    is_active_display.admin_order_field = 'is_active'
    is_active_display.boolean = True
    
    def usage_count_display(self, obj):
        return obj.usage_count
    usage_count_display.short_description = _('Usage Count')
    usage_count_display.admin_order_field = 'usage_count'
    
    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.username
        return _('Unknown')
    created_by_display.short_description = _('Created By')
    created_by_display.admin_order_field = 'created_by__username'
    
    def updated_at_display(self, obj):
        if not obj.updated_at:
            return None
        # Use timezone-aware formatting with middleware-activated timezone
        localized_time = timezone.localtime(obj.updated_at)
        return localized_time.strftime('%Y-%m-%d %H:%M %Z')
    updated_at_display.short_description = _('Updated At')
    updated_at_display.admin_order_field = 'updated_at'


# Customize admin site
admin.site.site_header = _('Chatbot Administration')
admin.site.site_title = _('Chatbot Admin')
admin.site.index_title = _('Welcome to Chatbot Administration')

# Add custom admin views
from django.urls import path
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse

def llm_chat_admin_view(request):
    """LLM Chat Interface integrated into Django admin"""
    from documents.models import Document
    
    context = {
        'title': 'LLM Chat Interface',
        'available_providers': ['openai', 'gemini', 'claude'],
        'total_documents': Document.objects.filter(is_active=True).count(),
        'processed_documents': Document.objects.filter(is_active=True, extracted_text__isnull=False).exclude(extracted_text='').count(),
        'opts': None,  # No model options for custom view
        'has_permission': True,
        'site_title': admin.site.site_title,
        'site_header': admin.site.site_header,
        'site_url': '/',
        'has_change_permission': True,
    }
    
    return TemplateResponse(request, 'admin/chat/llm_chat.html', context)




@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    """Admin interface for automatic LLM-generated conversation summaries"""
    
    list_display = [
        'summary_preview', 'analysis_period_display', 'messages_analyzed_count_display', 
        'critical_issues_found_display', 'trigger_reason_display', 'generated_at_display'
    ]
    list_filter = ['trigger_reason', 'generated_at', 'critical_issues_found']
    readonly_fields = [
        'uuid', 'llm_analysis', 'analysis_period', 'messages_analyzed_count',
        'critical_issues_found', 'generated_at', 'trigger_reason',
        'llm_model_used', 'llm_response_time'
    ]
    search_fields = ['llm_analysis', 'trigger_reason']
    
    # Make all fields read-only (no manual creation)
    def has_add_permission(self, request):
        return False  # Disable manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # Make read-only
    
    fieldsets = [
        (_('LLM Analysis'), {
            'fields': ['llm_analysis_display'],
        }),
        (_('Summary Information'), {
            'fields': ['analysis_period', 'messages_analyzed_count', 'critical_issues_found'],
        }),
        (_('Generation Details'), {
            'fields': ['trigger_reason', 'generated_at', 'llm_model_used', 'llm_response_time'],
            'classes': ['collapse']
        }),
        (_('System Information'), {
            'fields': ['uuid'],
            'classes': ['collapse']
        })
    ]
    
    actions = ['generate_automatic_summary']
    
    def generate_automatic_summary(self, request, queryset):
        """Admin action to generate new automatic summary"""
        try:
            import asyncio
            from .services.automatic_summary_service import AutomaticSummaryService
            
            async def create_summary():
                return await AutomaticSummaryService.generate_automatic_summary("admin_manual_trigger")
            
            summary = asyncio.run(create_summary())
            
            if summary:
                messages.success(request, f"Automatic summary generated successfully: {summary}")
            else:
                messages.warning(request, "No summary generated - no recent messages found")
                
        except Exception as e:
            messages.error(request, f"Failed to generate summary: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Admin summary generation error: {e}")
    
    generate_automatic_summary.short_description = _("Generate New Automatic Summary")
    
    def summary_preview(self, obj):
        preview = obj.get_preview(80)
        return preview
    summary_preview.short_description = _('Summary Preview')
    
    def generated_at_display(self, obj):
        return obj.generated_at.strftime('%Y-%m-%d %H:%M')
    generated_at_display.short_description = _('Generated At')
    
    def llm_analysis_display(self, obj):
        return format_html(
            '<div style="max-height: 500px; overflow-y: auto; padding: 15px; background: #f8f9fa; border-radius: 4px; white-space: pre-wrap; font-family: Arial, sans-serif; line-height: 1.5;">{}</div>', 
            obj.llm_analysis
        )
    llm_analysis_display.short_description = _('LLM Analysis')
    
    def analysis_period_display(self, obj):
        return obj.analysis_period
    analysis_period_display.short_description = _('Analysis Period')
    analysis_period_display.admin_order_field = 'analysis_period'
    
    def messages_analyzed_count_display(self, obj):
        return obj.messages_analyzed_count
    messages_analyzed_count_display.short_description = _('Messages Analyzed')
    messages_analyzed_count_display.admin_order_field = 'messages_analyzed_count'
    
    def critical_issues_found_display(self, obj):
        return obj.critical_issues_found
    critical_issues_found_display.short_description = _('Critical Issues Found')
    critical_issues_found_display.admin_order_field = 'critical_issues_found'
    
    def trigger_reason_display(self, obj):
        # Map trigger reason codes to user-friendly text
        trigger_translations = {
            'recent_activity': _('Recent activity'),
            'admin_manual_trigger': _('Manual trigger'),
            'scheduled': _('Scheduled'),
            'legacy_migration': _('Legacy migration'),
        }
        return trigger_translations.get(obj.trigger_reason, obj.trigger_reason)
    trigger_reason_display.short_description = _('Generation Trigger')
    trigger_reason_display.admin_order_field = 'trigger_reason'

