from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import ConversationAnalysis, UserFeedback, AnalyticsSummary, DocumentUsage


@admin.register(ConversationAnalysis)
class ConversationAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_link', 'sentiment_display', 'satisfaction_level', 'confidence_score', 'analyzed_at']
    list_filter = ['sentiment', 'satisfaction_level', 'resolution_status', 'analyzed_at', 'langextract_model_used']
    search_fields = ['conversation__user__username', 'customer_intent', 'issues_raised']
    readonly_fields = ['analyzed_at', 'processing_time', 'confidence_score']
    list_per_page = 25
    date_hierarchy = 'analyzed_at'
    ordering = ['-analyzed_at']
    
    fieldsets = (
        (_('Analysis Results'), {
            'fields': ('conversation', 'sentiment', 'satisfaction_level', 'customer_intent')
        }),
        (_('Issues & Resolution'), {
            'fields': ('issues_raised', 'urgency_indicators', 'resolution_status', 'key_insights')
        }),
        (_('LangExtract Data'), {
            'fields': ('source_spans', 'confidence_score', 'langextract_model_used', 'processing_time'),
            'classes': ('collapse',)
        }),
        (_('Timestamp'), {
            'fields': ('analyzed_at',),
            'classes': ('collapse',)
        })
    )
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">Conv #{}</a>', url, obj.conversation.id)
    conversation_link.short_description = _('Conversation')
    conversation_link.admin_order_field = 'conversation__id'
    
    def sentiment_display(self, obj):
        colors = {
            'positive': 'green',
            'negative': 'red', 
            'neutral': 'orange'
        }
        icons = {
            'positive': '😊',
            'negative': '😞',
            'neutral': '😐'
        }
        color = colors.get(obj.sentiment, 'black')
        icon = icons.get(obj.sentiment, '')
        return format_html('<span style="color: {};">{} {}</span>', color, icon, obj.sentiment.title())
    sentiment_display.short_description = _('Sentiment')
    sentiment_display.admin_order_field = 'sentiment'


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
            return format_html('<span style="color: green;">👍 Positive</span>')
        else:
            return format_html('<span style="color: red;">👎 Negative</span>')
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


@admin.register(DocumentUsage)
class DocumentUsageAdmin(admin.ModelAdmin):
    list_display = ['id', 'document_link', 'conversation_link', 'effectiveness_score', 'search_query', 'referenced_at']
    list_filter = ['referenced_at', 'effectiveness_score']
    search_fields = ['document__title', 'search_query', 'conversation__user__username']
    readonly_fields = ['referenced_at']
    list_per_page = 50
    date_hierarchy = 'referenced_at'
    ordering = ['-referenced_at']
    
    def document_link(self, obj):
        url = reverse('admin:documents_companydocument_change', args=[obj.document.id])
        return format_html('<a href="{}">{}</a>', url, obj.document.title[:30])
    document_link.short_description = _('Document')
    
    def conversation_link(self, obj):
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html('<a href="{}">Conv #{}</a>', url, obj.conversation.id)
    conversation_link.short_description = _('Conversation')
