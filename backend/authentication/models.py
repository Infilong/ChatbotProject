from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', _('Customer')),
        ('admin', _('Admin')),
        ('support', _('Support Agent')),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer', verbose_name=_('Role'))
    
    # Profile information
    phone_number = models.CharField(max_length=20, blank=True, verbose_name=_('Phone Number'))
    company = models.CharField(max_length=100, blank=True, verbose_name=_('Company'))
    job_title = models.CharField(max_length=100, blank=True, verbose_name=_('Job Title'))
    
    # Preferences
    preferred_language = models.CharField(max_length=10, default='en', verbose_name=_('Preferred Language'))
    email_notifications = models.BooleanField(default=True, verbose_name=_('Email Notifications'))
    
    # Usage statistics
    total_conversations = models.IntegerField(default=0, verbose_name=_('Total Conversations'))
    total_messages_sent = models.IntegerField(default=0, verbose_name=_('Total Messages Sent'))
    average_satisfaction = models.FloatField(default=0.0, verbose_name=_('Average Satisfaction'))
    last_active = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Active'))
    
    # Account details
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        
    def __str__(self):
        return f"{self.user.username} Profile ({self.role})"
    
    @property
    def is_admin(self):
        return self.role in ['admin', 'support']
    
    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    
    # Chat preferences
    chat_theme = models.CharField(max_length=20, default='ocean_blue', verbose_name=_('Chat Theme'))
    show_timestamps = models.BooleanField(default=True, verbose_name=_('Show Timestamps'))
    enable_sound_notifications = models.BooleanField(default=True, verbose_name=_('Enable Sound Notifications'))
    
    # AI preferences
    preferred_response_style = models.CharField(max_length=20, default='balanced', verbose_name=_('Preferred Response Style'))  # casual, formal, balanced
    enable_proactive_suggestions = models.BooleanField(default=True, verbose_name=_('Enable Proactive Suggestions'))
    
    # Privacy settings
    allow_conversation_analysis = models.BooleanField(default=True, verbose_name=_('Allow Conversation Analysis'))
    share_data_for_improvements = models.BooleanField(default=True, verbose_name=_('Share Data for Improvements'))
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('User Preferences')
        verbose_name_plural = _('User Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
