"""
User Session Models for tracking active user sessions
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid


class UserSession(models.Model):
    """Track active user sessions with start/end times"""
    
    # Unique session identifier
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # User relationship
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    
    # Session timing
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Started At'))
    last_active = models.DateTimeField(auto_now=True, verbose_name=_('Last Active'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))
    
    # Session metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP Address'))
    user_agent = models.TextField(blank=True, verbose_name=_('User Agent'))
    device_type = models.CharField(max_length=20, blank=True, verbose_name=_('Device Type'))  # mobile, desktop, tablet
    
    # Activity tracking
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    total_requests = models.IntegerField(default=0, verbose_name=_('Total Requests'))
    last_activity_type = models.CharField(max_length=50, blank=True, verbose_name=_('Last Activity'))  # chat, view, api_call
    
    class Meta:
        ordering = ['-last_active']
        verbose_name = _('Admin Session')
        verbose_name_plural = _('Admin Sessions')
        indexes = [
            models.Index(fields=['user', '-last_active']),
            models.Index(fields=['is_active', '-last_active']),
        ]
    
    def __str__(self):
        duration = self.get_session_duration()
        status = "Active" if self.is_active else "Ended"
        return f"{self.user.username} - {status} ({duration})"
    
    def get_session_duration(self):
        """Calculate session duration"""
        end_time = self.ended_at or timezone.now()
        duration = end_time - self.started_at
        
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{total_seconds}s"
    
    def is_session_expired(self, timeout_minutes=30):
        """Check if session is expired (inactive for X minutes)"""
        if not self.is_active:
            return True
        
        timeout_delta = timezone.timedelta(minutes=timeout_minutes)
        return timezone.now() - self.last_active > timeout_delta
    
    def end_session(self):
        """Mark session as ended"""
        self.is_active = False
        self.ended_at = timezone.now()
        self.save(update_fields=['is_active', 'ended_at'])
    
    def update_activity(self, activity_type='general', increment_requests=True):
        """Update session activity"""
        self.last_active = timezone.now()
        self.last_activity_type = activity_type
        
        if increment_requests:
            self.total_requests += 1
        
        self.save(update_fields=['last_active', 'last_activity_type', 'total_requests'])
    
    @classmethod
    def get_active_sessions(cls):
        """Get all currently active sessions"""
        return cls.objects.filter(is_active=True)
    
    @classmethod
    def get_user_active_session(cls, user):
        """Get user's current active session"""
        return cls.objects.filter(user=user, is_active=True).first()
    
    @classmethod
    def cleanup_expired_sessions(cls, timeout_minutes=30):
        """Clean up expired sessions"""
        timeout_delta = timezone.timedelta(minutes=timeout_minutes)
        cutoff_time = timezone.now() - timeout_delta
        
        expired_sessions = cls.objects.filter(
            is_active=True,
            last_active__lt=cutoff_time
        )
        
        count = expired_sessions.count()
        expired_sessions.update(is_active=False, ended_at=timezone.now())
        
        return count


class SessionActivity(models.Model):
    """Track detailed session activities"""
    
    ACTIVITY_TYPES = [
        ('login', _('Login')),
        ('chat', _('Chat Message')),
        ('view', _('Page View')),
        ('api', _('API Call')),
        ('upload', _('File Upload')),
        ('download', _('File Download')),
        ('admin', _('Admin Action')),
        ('logout', _('Logout')),
    ]
    
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, verbose_name=_('Activity Type'))
    description = models.CharField(max_length=200, blank=True, verbose_name=_('Description'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))
    
    # Optional metadata
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Session Activity')
        verbose_name_plural = _('Session Activities')
        indexes = [
            models.Index(fields=['session', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.session.user.username} - {self.get_activity_type_display()} ({self.timestamp})"