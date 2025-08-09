from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django import forms
from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt


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
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
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
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_display.short_description = _('Updated At')
    updated_at_display.admin_order_field = 'updated_at'


# Customize admin site
admin.site.site_header = _('🤖 Chatbot Administration')
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

