from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.template.response import TemplateResponse
from django.utils import timezone
from .models import ConversationAnalysis, UserFeedback, AnalyticsSummary, DocumentUsage


# ConversationAnalysis admin removed - page completely disabled


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'message_link', 'feedback_display', 'rating', 'timestamp']
    list_filter = ['feedback_type', 'rating', 'timestamp']
    search_fields = ['user__username', 'comment', 'message__content']
    readonly_fields = ['timestamp']
    list_per_page = 50
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
    
    def message_link(self, obj):
        url = reverse('admin:chat_message_change', args=[obj.message.id])
        return format_html('<a href="{}">Msg #{}</a>', url, obj.message.id)
    message_link.short_description = _('Message')
    
    def feedback_display(self, obj):
        if obj.feedback_type == 'positive':
            return format_html('<span style="color: green;">Positive</span>')
        else:
            return format_html('<span style="color: red;">Negative</span>')
    feedback_display.short_description = _('Feedback')


@admin.register(AnalyticsSummary)
class AnalyticsSummaryAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_conversations', 'total_messages', 'unique_users', 'average_satisfaction', 'sentiment_ratio']
    list_filter = ['date', 'average_satisfaction']
    search_fields = ['date']
    readonly_fields = ['created_at']
    list_per_page = 50
    date_hierarchy = 'date'
    ordering = ['-date']
    
    fieldsets = (
        (_('Daily Metrics'), {
            'fields': ('date', 'total_conversations', 'total_messages', 'unique_users', 'average_satisfaction')
        }),
        (_('Sentiment Distribution'), {
            'fields': ('positive_conversations', 'negative_conversations', 'neutral_conversations')
        }),
        (_('Issue Tracking'), {
            'fields': ('total_issues_raised', 'resolved_issues', 'escalated_issues')
        }),
        (_('Performance'), {
            'fields': ('average_response_time', 'bot_vs_human_ratio'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def sentiment_ratio(self, obj):
        total = obj.positive_conversations + obj.negative_conversations + obj.neutral_conversations
        if total == 0:
            return _("No data")
        
        pos_pct = (obj.positive_conversations / total) * 100
        neg_pct = (obj.negative_conversations / total) * 100
        
        return format_html(
            '<span style="color: green;">{}%</span> / <span style="color: red;">{}%</span>',
            round(pos_pct, 1), round(neg_pct, 1)
        )
    sentiment_ratio.short_description = _('Pos/Neg Ratio')


class DocumentUsageGrouping:
    """Helper class to group document usage by user message"""
    def __init__(self, search_query, document, latest_usage):
        self.search_query = search_query
        self.document = document
        self.latest_usage = latest_usage
        self.usage_count = 0
        self.all_usages = []
        self.combined_keywords = set()
        self.combined_excerpts = []
    
    def add_usage(self, usage):
        self.usage_count += 1
        self.all_usages.append(usage)
        if usage.keywords_matched:
            self.combined_keywords.update(usage.keywords_matched)
        if usage.excerpt_used and usage.excerpt_used not in self.combined_excerpts:
            self.combined_excerpts.append(usage.excerpt_used)
        # Update latest usage if this one is more recent
        if usage.referenced_at > self.latest_usage.referenced_at:
            self.latest_usage = usage


@admin.register(DocumentUsage)
class DocumentUsageAdmin(admin.ModelAdmin):
    """Enhanced admin interface for document usage analytics focused on user messages"""
    
    
    list_display = [
        'user_message_display',
        'question_category_display', 
        'document_link',
        'usage_count_display',
        'excerpt_with_toggle',
        'keywords_matched_display',
        'last_used_display'
    ]
    
    list_filter = [
        'usage_type',
        'user_intent',
        'context_category',
        'referenced_at',
        'relevance_score',
        'document__category'
    ]
    
    search_fields = [
        'search_query',
        'document__name',
        'excerpt_used',
        'user_intent',
        'context_category'
    ]
    
    readonly_fields = [
        'referenced_at',
        'processing_time',
        'message_context_display',
        'usage_statistics_display',
        'full_excerpt_display'
    ]
    
    list_per_page = 25
    date_hierarchy = 'referenced_at'
    ordering = ['-referenced_at']
    
    def changelist_view(self, request, extra_context=None):
        """Add analytics dashboard link to the changelist view"""
        extra_context = extra_context or {}
        extra_context['analytics_url'] = reverse('admin:analytics_documentusage_analytics')
        return super().changelist_view(request, extra_context=extra_context)
    
    fieldsets = [
        (_('User Message & Context'), {
            'fields': [
                'search_query',
                'user_intent',
                'context_category',
                'message_context_display'
            ]
        }),
        (_('Document Usage'), {
            'fields': [
                'document',
                'usage_type',
                'relevance_score',
                'keywords_matched',
                'usage_statistics_display'
            ]
        }),
        (_('Excerpt Content'), {
            'fields': [
                'full_excerpt_display',
                ('excerpt_start_position', 'excerpt_length')
            ],
            'classes': ['collapse']
        }),
        (_('Technical Details'), {
            'fields': [
                'llm_model_used',
                'processing_time',
                'referenced_at'
            ],
            'classes': ['collapse']
        })
    ]
    
    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path('analytics/', self.admin_site.admin_view(self.usage_analytics_view), name='analytics_documentusage_analytics'),
            path('grouped/', self.admin_site.admin_view(self.grouped_usage_view), name='analytics_documentusage_grouped'),
            path('message-details/', self.admin_site.admin_view(self.message_details_view), name='analytics_documentusage_message_details'),
        ]
        return custom_urls + urls
    
    def usage_analytics_view(self, request):
        """Custom analytics dashboard for document usage"""
        from django.db.models import Count, Avg, Q
        from datetime import datetime, timedelta
        
        # Get time range (last 30 days by default)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Basic statistics
        total_usages = DocumentUsage.objects.filter(referenced_at__gte=start_date).count()
        unique_documents = DocumentUsage.objects.filter(referenced_at__gte=start_date).values('document').distinct().count()
        avg_relevance = DocumentUsage.objects.filter(referenced_at__gte=start_date).aggregate(Avg('relevance_score'))['relevance_score__avg'] or 0
        
        # Top documents by usage
        top_documents = (DocumentUsage.objects
                        .filter(referenced_at__gte=start_date)
                        .values('document__name')
                        .annotate(usage_count=Count('id'), avg_relevance=Avg('relevance_score'))
                        .order_by('-usage_count')[:10])
        
        # Usage by intent
        intent_stats = (DocumentUsage.objects
                       .filter(referenced_at__gte=start_date)
                       .values('user_intent')
                       .annotate(count=Count('id'))
                       .order_by('-count'))
        
        # Popular keywords
        all_keywords = []
        for usage in DocumentUsage.objects.filter(referenced_at__gte=start_date, keywords_matched__isnull=False):
            if usage.keywords_matched:
                all_keywords.extend(usage.keywords_matched)
        
        from collections import Counter
        keyword_counts = Counter(all_keywords).most_common(15)
        
        context = {
            'title': 'Document Usage Analytics',
            'opts': self.model._meta,
            'start_date': start_date,
            'end_date': end_date,
            'total_usages': total_usages,
            'unique_documents': unique_documents,
            'avg_relevance': round(avg_relevance, 2),
            'top_documents': top_documents,
            'intent_stats': intent_stats,
            'keyword_counts': keyword_counts
        }
        
        return TemplateResponse(request, 'admin/analytics/document_usage_analytics.html', context)
    
    def grouped_usage_view(self, request):
        """Custom grouped view with user message aggregation"""
        from django.db.models import Q
        from collections import defaultdict
        
        # Group usage data by search_query + document combination
        grouped_data = defaultdict(lambda: None)
        
        # Get all usage records ordered by most recent
        all_usages = DocumentUsage.objects.select_related('document', 'conversation', 'message').order_by('-referenced_at')
        
        for usage in all_usages:
            # Create unique key for grouping: normalize the search query + document
            normalized_query = usage.search_query.strip().lower()
            key = f"{normalized_query}::{usage.document.id}"
            
            if grouped_data[key] is None:
                # Create new group
                grouped_data[key] = DocumentUsageGrouping(
                    search_query=usage.search_query,
                    document=usage.document,
                    latest_usage=usage
                )
            
            # Add this usage to the group
            grouped_data[key].add_usage(usage)
        
        # Convert to list and sort by latest usage
        grouped_list = sorted(grouped_data.values(), key=lambda g: g.latest_usage.referenced_at, reverse=True)
        
        context = {
            'title': 'Document Usage Analytics - Grouped by User Messages',
            'grouped_usages': grouped_list,
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/analytics/document_usage_grouped_list_simple.html', context)
    
    def message_details_view(self, request):
        """Show detailed view of all instances of a specific message pattern"""
        search_query = request.GET.get('search_query', '')
        document_id = request.GET.get('document', '')
        
        if not search_query:
            from django.contrib import messages
            messages.error(request, 'No search query provided')
            return self.changelist_view(request)
        
        # Get all usage instances for this message pattern
        usage_filter = {'search_query__iexact': search_query}
        if document_id:
            usage_filter['document_id'] = document_id
            
        usage_instances = DocumentUsage.objects.filter(**usage_filter).select_related(
            'document', 'conversation', 'message', 'conversation__user'
        ).order_by('-referenced_at')
        
        context = {
            'title': f'All instances of: \"{search_query}\"',
            'search_query': search_query,
            'usage_instances': usage_instances,
            'total_count': usage_instances.count(),
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/analytics/message_details.html', context)
    
    # Display methods
    def user_message_display(self, obj):
        """Display the user message that triggered document usage - clickable for details"""
        message_preview = obj.search_query[:80] + "..." if len(obj.search_query) > 80 else obj.search_query
        detail_url = reverse('admin:analytics_documentusage_change', args=[obj.id])
        return format_html(
            '<a href="{}" title="Click to see all instances of this message">{}</a>', 
            detail_url, message_preview
        )
    user_message_display.short_description = _('User Message (Latest)')
    user_message_display.admin_order_field = 'search_query'
    
    def question_category_display(self, obj):
        """Display the category/type of user question"""
        category = obj.user_intent or obj.context_category or 'General'
        category_display = category.replace('_', ' ').title()
        
        # Color coding based on category
        color_map = {
            'Technical': '#1976D2',
            'Support': '#388E3C', 
            'Compliance': '#F57C00',
            'Services': '#7B1FA2',
            'General': '#616161'
        }
        color = color_map.get(category_display, '#616161')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, category_display
        )
    question_category_display.short_description = _('Question Category')
    question_category_display.admin_order_field = 'user_intent'
    
    def document_link(self, obj):
        """Link to document admin page showing full document name"""
        try:
            url = reverse('admin:documents_document_change', args=[obj.document.uuid])
            return format_html('<a href="{}" title="{}">{}</a>', 
                             url, obj.document.name, obj.document.name)
        except:
            return obj.document.name if obj.document else 'Unknown'
    document_link.short_description = _('Document')
    document_link.admin_order_field = 'document__name'
    
    def get_grouped_usage_data(self):
        """Get grouped usage data for template"""
        # This method will be used by the template
        pass
    
    def usage_count_display(self, obj):
        """Show how many times this same message pattern was used"""
        from django.db.models import Q
        
        # Count similar usage patterns (same search query + same document)
        similar_count = DocumentUsage.objects.filter(
            Q(search_query__iexact=obj.search_query) & Q(document=obj.document)
        ).count()
        
        return similar_count  # Return just the number
    usage_count_display.short_description = _('Usage Count')
    usage_count_display.admin_order_field = 'search_query'
    
    def excerpt_with_toggle(self, obj):
        """Display excerpt with simple truncation and tooltip"""
        if not obj.excerpt_used:
            return format_html('<span style="color: gray;">No excerpt</span>')
        
        if len(obj.excerpt_used) <= 150:
            return obj.excerpt_used
        
        # For long excerpts, show truncated version with tooltip
        preview = obj.excerpt_used[:150] + "..."
        return format_html(
            '<span title="{}" style="cursor: help; border-bottom: 1px dotted #666;">{}</span>',
            obj.excerpt_used.replace('"', '&quot;'),
            preview
        )
    excerpt_with_toggle.short_description = _('Excerpt Used')
    
    def last_used_display(self, obj):
        """Display when this document was last used for similar queries"""
        from django.db.models import Q
        
        # Find the most recent usage of same search query + document combination
        latest_usage = DocumentUsage.objects.filter(
            Q(search_query__iexact=obj.search_query) & Q(document=obj.document)
        ).order_by('-referenced_at').first()
        
        if latest_usage:
            timestamp = latest_usage.referenced_at.strftime('%Y-%m-%d %H:%M')
            return format_html('<span title="{}">{}</span>', 
                             latest_usage.referenced_at.strftime('%Y-%m-%d %H:%M:%S'), timestamp)
        return obj.referenced_at.strftime('%Y-%m-%d %H:%M')
    last_used_display.short_description = _('Last Used')
    last_used_display.admin_order_field = 'referenced_at'
    
    def keywords_matched_display(self, obj):
        """Display matched keywords as badges"""
        if not obj.keywords_matched:
            return format_html('<span style="color: gray;">None</span>')
        
        keywords = obj.keywords_matched[:5]  # Show first 5 keywords
        badges = []
        for keyword in keywords:
            badges.append(format_html('<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 2px;">{}</span>', keyword))
        
        extra = len(obj.keywords_matched) - 5
        if extra > 0:
            badges.append(format_html('<span style="color: gray; font-size: 11px;">+{} more</span>', extra))
        
        return mark_safe(''.join(str(badge) for badge in badges))
    keywords_matched_display.short_description = _('Keywords')
    
    
    # Detailed analysis methods for readonly fields
    def message_context_display(self, obj):
        """Display context about the user message and conversation"""
        parts = []
        
        # Conversation info
        conv_url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        parts.append(format_html('<strong>Conversation:</strong> <a href="{}"># {}</a>', conv_url, obj.conversation.id))
        
        # Message info  
        msg_url = reverse('admin:chat_message_change', args=[obj.message.id])
        parts.append(format_html('<strong>Message:</strong> <a href="{}"># {}</a>', msg_url, obj.message.id))
        
        # User info
        user_url = reverse('admin:auth_user_change', args=[obj.conversation.user.id])
        parts.append(format_html('<strong>User:</strong> <a href="{}">{}</a>', user_url, obj.conversation.user.username))
        
        # Timestamp
        parts.append(format_html('<strong>Asked At:</strong> {}', obj.referenced_at.strftime('%Y-%m-%d %H:%M:%S')))
        
        return format_html('<br>'.join(str(part) for part in parts))
    message_context_display.short_description = _('Message Context')
    
    def usage_statistics_display(self, obj):
        """Display usage statistics for this search query + document combination"""
        from django.db.models import Count, Q, Avg
        
        # Get statistics for this specific search query + document combination
        similar_usages = DocumentUsage.objects.filter(
            Q(search_query__iexact=obj.search_query) & Q(document=obj.document)
        )
        
        total_count = similar_usages.count()
        avg_relevance = similar_usages.aggregate(avg=Avg('relevance_score'))['avg'] or 0
        first_used = similar_usages.order_by('referenced_at').first()
        last_used = similar_usages.order_by('-referenced_at').first()
        
        parts = []
        parts.append(format_html('<strong>Total Usage Count:</strong> {}', total_count))
        parts.append(format_html('<strong>Average Relevance:</strong> {:.2f}', avg_relevance))
        
        if first_used:
            parts.append(format_html('<strong>First Used:</strong> {}', first_used.referenced_at.strftime('%Y-%m-%d %H:%M')))
        if last_used:
            parts.append(format_html('<strong>Last Used:</strong> {}', last_used.referenced_at.strftime('%Y-%m-%d %H:%M')))
            
        return format_html('<br>'.join(str(part) for part in parts))
    usage_statistics_display.short_description = _('Usage Statistics')
    
    def full_excerpt_display(self, obj):
        """Display the full excerpt used from the document"""
        if not obj.excerpt_used:
            return format_html('<p style="color: gray;">No excerpt was used from this document.</p>')
        
        # Build analysis parts
        parts = []
        parts.append(format_html('<strong>Excerpt Length:</strong> {} characters', len(obj.excerpt_used)))
        
        if obj.excerpt_start_position is not None:
            formatted_position = f'{obj.excerpt_start_position:,}'
            parts.append(format_html('<strong>Position in Document:</strong> Character {}', formatted_position))
        
        # Add the full excerpt with safe HTML
        excerpt_html = format_html(
            '<br><strong>Full Excerpt:</strong><br>'
            '<div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #007cba; margin: 10px 0; max-height: 300px; overflow-y: auto; white-space: pre-wrap;">{}</div>',
            obj.excerpt_used
        )
        parts.append(excerpt_html)
        
        return format_html('<br>'.join(str(part) for part in parts))
    full_excerpt_display.short_description = _('Full Excerpt')
