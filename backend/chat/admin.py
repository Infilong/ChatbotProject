from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import Conversation, Message, UserSession, TestModel


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'title_display', 'total_messages', 'satisfaction_score', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'updated_at', 'satisfaction_score']
    search_fields = ['user__username', 'user__email', 'title']
    readonly_fields = ['created_at', 'updated_at', 'total_messages']
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-updated_at']
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
    
    def title_display(self, obj):
        title = obj.get_title()
        return title[:50] + "..." if len(title) > 50 else title
    title_display.short_description = _('Title')


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
            return format_html('<span style="color: green;">👍 Positive</span>')
        elif obj.feedback == 'negative':
            return format_html('<span style="color: red;">👎 Negative</span>')
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


class TestModelAdmin(admin.ModelAdmin):
    """Simple admin for test model"""
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    fields = ['name', 'description', 'is_active']

# Use traditional registration instead of decorator
admin.site.register(TestModel, TestModelAdmin)
