from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils import timezone
from django.conf import settings
from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt


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
    list_display = ['id', 'user_link', 'title_display', 'total_messages', 'satisfaction_score', 'analysis_status', 'created_at_local', 'is_active']
    list_filter = ['is_active', 'created_at', 'updated_at', 'satisfaction_score']
    search_fields = ['user__username', 'user__email', 'title']
    readonly_fields = ['created_at', 'updated_at', 'total_messages']
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-updated_at']
    actions = ['add_sample_messages', 'analyze_with_langextract', 'verify_api_connection', 'bulk_analyze_langextract']
    actions_selection_counter = True
    actions_on_top = True
    actions_on_bottom = False
    inlines = [MessageInline]  # Add inline message editing
    
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
            'fields': ('created_at', 'updated_at', 'total_messages'),
            'classes': ('collapse',)
        })
    )
    
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


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_link', 'sender_type', 'content_preview', 'feedback_display', 'timestamp']
    list_filter = ['sender_type', 'feedback', 'timestamp', 'llm_model_used']
    search_fields = ['content', 'conversation__user__username']
    readonly_fields = ['timestamp', 'response_time']
    list_per_page = 50
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">Conv #{}</a>', url, obj.conversation.id)
    conversation_link.short_description = _('Conversation')
    conversation_link.admin_order_field = 'conversation__id'
    
    def content_preview(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content
    content_preview.short_description = _('Content')
    
    def feedback_display(self, obj):
        if obj.feedback == 'positive':
            return format_html('<span style="color: green; font-weight: bold;">+ Positive</span>')
        elif obj.feedback == 'negative':
            return format_html('<span style="color: red; font-weight: bold;">- Negative</span>')
        return _('-')
    feedback_display.short_description = _('Feedback')


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'session_id_short', 'total_conversations', 'total_messages_sent', 'duration', 'started_at', 'is_active']
    list_filter = ['is_active', 'started_at', 'ended_at']
    search_fields = ['user__username', 'session_id']
    readonly_fields = ['started_at', 'ended_at']
    date_hierarchy = 'started_at'
    ordering = ['-started_at']
    
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

