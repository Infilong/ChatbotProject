"""
Django Admin for User Sessions
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import SimpleListFilter
from .session_models import UserSession, SessionActivity


class DeviceTypeFilter(SimpleListFilter):
    title = _('Device Type')
    parameter_name = 'device_type'

    def lookups(self, request, model_admin):
        device_types = UserSession.objects.values_list('device_type', flat=True).distinct()
        return [(dt, dt) for dt in device_types if dt]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(device_type=self.value())
        return queryset


class LastActivityFilter(SimpleListFilter):
    title = _('Last Activity')
    parameter_name = 'last_activity'

    def lookups(self, request, model_admin):
        return [
            ('today', _('Today')),
            ('yesterday', _('Yesterday')),
            ('week', _('This Week')),
            ('month', _('This Month')),
        ]

    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        if self.value() == 'today':
            return queryset.filter(last_active__date=timezone.now().date())
        elif self.value() == 'yesterday':
            yesterday = timezone.now().date() - timedelta(days=1)
            return queryset.filter(last_active__date=yesterday)
        elif self.value() == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            return queryset.filter(last_active__gte=week_ago)
        elif self.value() == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            return queryset.filter(last_active__gte=month_ago)
        return queryset


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'session_status', 'started_at_display', 'duration_display', 'last_active_display', 'total_requests_display', 'device_type_display', 'ip_address']
    list_filter = ['is_active', 'started_at', LastActivityFilter, DeviceTypeFilter]
    search_fields = ['user__username', 'user__email', 'ip_address', 'session_id']
    readonly_fields = ['session_id', 'started_at', 'last_active', 'total_requests']
    list_per_page = 25
    date_hierarchy = 'started_at'
    ordering = ['-last_active']
    
    fieldsets = (
        (_('Session Information'), {
            'fields': ('session_id', 'user', 'is_active')
        }),
        (_('Timing'), {
            'fields': ('started_at', 'last_active', 'ended_at')
        }),
        (_('Device & Location'), {
            'fields': ('ip_address', 'device_type', 'user_agent')
        }),
        (_('Activity'), {
            'fields': ('total_requests', 'last_activity_type'),
            'classes': ('collapse',)
        })
    )
    
    def user_link(self, obj):
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = _('User')
    user_link.admin_order_field = 'user__username'
    
    def session_status(self, obj):
        if obj.is_active:
            # Check if session might be expired
            if obj.is_session_expired():
                color = 'orange'
                status = _('Expired')
            else:
                color = 'green'
                status = _('Active')
        else:
            color = 'red'
            status = _('Ended')
        
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, status)
    session_status.short_description = _('Status')
    
    def started_at_display(self, obj):
        return obj.started_at.strftime('%Y-%m-%d %H:%M:%S')
    started_at_display.short_description = _('Started At')
    started_at_display.admin_order_field = 'started_at'
    
    def last_active_display(self, obj):
        return obj.last_active.strftime('%Y-%m-%d %H:%M:%S')
    last_active_display.short_description = _('Last Active')
    last_active_display.admin_order_field = 'last_active'
    
    def duration_display(self, obj):
        return obj.get_session_duration()
    duration_display.short_description = _('Duration')
    
    def total_requests_display(self, obj):
        return obj.total_requests
    total_requests_display.short_description = _('Total Requests')
    total_requests_display.admin_order_field = 'total_requests'
    
    def device_type_display(self, obj):
        return obj.device_type
    device_type_display.short_description = _('Device Type')
    device_type_display.admin_order_field = 'device_type'
    
    actions = ['mark_sessions_ended', 'cleanup_expired_sessions']
    
    def mark_sessions_ended(self, request, queryset):
        """Mark selected active sessions as ended"""
        active_sessions = queryset.filter(is_active=True)
        count = active_sessions.count()
        
        for session in active_sessions:
            session.end_session()
        
        self.message_user(request, _('Successfully ended {} sessions.').format(count))
    mark_sessions_ended.short_description = _('Mark selected sessions as ended')
    
    def cleanup_expired_sessions(self, request, queryset):
        """Clean up expired sessions"""
        count = UserSession.cleanup_expired_sessions(timeout_minutes=30)
        self.message_user(request, _('Cleaned up {} expired sessions.').format(count))
    cleanup_expired_sessions.short_description = _('Clean up expired sessions (30min timeout)')


@admin.register(SessionActivity)
class SessionActivityAdmin(admin.ModelAdmin):
    list_display = ['user_display', 'session_link', 'activity_type', 'description', 'timestamp']
    list_filter = ['activity_type', 'timestamp', 'session__is_active']
    search_fields = ['session__user__username', 'description', 'session__session_id']
    readonly_fields = ['session', 'timestamp', 'metadata']
    list_per_page = 50
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    fieldsets = (
        (_('Activity Information'), {
            'fields': ('session', 'activity_type', 'description')
        }),
        (_('Timing'), {
            'fields': ('timestamp',)
        }),
        (_('Additional Data'), {
            'fields': ('metadata',),
            'classes': ('collapse',)
        })
    )
    
    def user_display(self, obj):
        return obj.session.user.username
    user_display.short_description = _('User')
    user_display.admin_order_field = 'session__user__username'
    
    def session_link(self, obj):
        return format_html('<a href="/admin/authentication/usersession/{}/change/">{}</a>', 
                         obj.session.id, str(obj.session.session_id)[:8] + '...')
    session_link.short_description = _('Session')
    session_link.admin_order_field = 'session__session_id'