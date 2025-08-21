from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, UserPreferences
from .session_models import UserSession, SessionActivity

# Import session admin
from . import session_admin


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = _('Profile')
    fields = ['role', 'phone_number', 'company', 'job_title', 'preferred_language', 'email_notifications']


class UserPreferencesInline(admin.StackedInline):
    model = UserPreferences
    can_delete = False
    verbose_name_plural = _('Preferences')
    fields = ['chat_theme', 'show_timestamps', 'enable_sound_notifications', 'preferred_response_style', 'enable_proactive_suggestions']


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, UserPreferencesInline)
    list_display = ['username', 'email', 'first_name', 'last_name', 'role_display', 'total_conversations', 'average_satisfaction', 'last_active', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'profile__role', 'profile__last_active']
    
    def role_display(self, obj):
        if hasattr(obj, 'profile'):
            role = obj.profile.role
            colors = {
                'admin': 'red',
                'support': 'orange', 
                'customer': 'blue'
            }
            color = colors.get(role, 'black')
            return format_html('<span style="color: {};">{}</span>', color, role.title())
        return _('No Profile')
    role_display.short_description = _('Role')
    role_display.admin_order_field = 'profile__role'
    
    def total_conversations(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.total_conversations
        return 0
    total_conversations.short_description = _('Conversations')
    total_conversations.admin_order_field = 'profile__total_conversations'
    
    def average_satisfaction(self, obj):
        if hasattr(obj, 'profile') and obj.profile.average_satisfaction:
            score = obj.profile.average_satisfaction
            if score >= 8:
                color = 'green'
            elif score >= 6:
                color = 'orange'
            else:
                color = 'red'
            return format_html('<span style="color: {};">{}</span>', color, f'{score:.1f}')
        return '-'
    average_satisfaction.short_description = _('Avg Satisfaction')
    average_satisfaction.admin_order_field = 'profile__average_satisfaction'
    
    def last_active(self, obj):
        if hasattr(obj, 'profile') and obj.profile.last_active:
            return obj.profile.last_active.strftime('%Y-%m-%d %H:%M')
        return _('Never')
    last_active.short_description = _('Last Active')
    last_active.admin_order_field = 'profile__last_active'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')


# Unregister the default User admin
admin.site.unregister(User)
# Register our custom User admin
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'role', 'company', 'total_conversations', 'total_messages_sent', 'average_satisfaction', 'last_active']
    list_filter = ['role', 'preferred_language', 'email_notifications', 'created_at', 'last_active']
    search_fields = ['user__username', 'user__email', 'company', 'job_title']
    readonly_fields = ['created_at', 'updated_at', 'total_conversations', 'total_messages_sent', 'average_satisfaction', 'last_active']
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-last_active']
    
    fieldsets = (
        (_('User Information'), {
            'fields': ('user', 'role')
        }),
        (_('Contact Details'), {
            'fields': ('phone_number', 'company', 'job_title')
        }),
        (_('Preferences'), {
            'fields': ('preferred_language', 'email_notifications')
        }),
        (_('Usage Statistics'), {
            'fields': ('total_conversations', 'total_messages_sent', 'average_satisfaction', 'last_active'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_link(self, obj):
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'chat_theme', 'preferred_response_style', 'enable_proactive_suggestions', 'allow_conversation_analysis', 'updated_at']
    list_filter = ['chat_theme', 'preferred_response_style', 'enable_proactive_suggestions', 'allow_conversation_analysis', 'updated_at']
    search_fields = ['user__username']
    readonly_fields = ['updated_at']
    list_per_page = 50
    ordering = ['-updated_at']
    
    fieldsets = (
        (_('User'), {
            'fields': ('user',)
        }),
        (_('Chat Preferences'), {
            'fields': ('chat_theme', 'show_timestamps', 'enable_sound_notifications')
        }),
        (_('AI Preferences'), {
            'fields': ('preferred_response_style', 'enable_proactive_suggestions')
        }),
        (_('Privacy Settings'), {
            'fields': ('allow_conversation_analysis', 'share_data_for_improvements')
        }),
        (_('Metadata'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        })
    )
    
    def user_link(self, obj):
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
