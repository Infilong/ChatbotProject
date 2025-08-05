from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('support', 'Support Agent'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    
    # Profile information
    phone_number = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    
    # Preferences
    preferred_language = models.CharField(max_length=10, default='en')
    email_notifications = models.BooleanField(default=True)
    
    # Usage statistics
    total_conversations = models.IntegerField(default=0)
    total_messages_sent = models.IntegerField(default=0)
    average_satisfaction = models.FloatField(default=0.0)
    last_active = models.DateTimeField(null=True, blank=True)
    
    # Account details
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        
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
    chat_theme = models.CharField(max_length=20, default='ocean_blue')
    show_timestamps = models.BooleanField(default=True)
    enable_sound_notifications = models.BooleanField(default=True)
    
    # AI preferences
    preferred_response_style = models.CharField(max_length=20, default='balanced')  # casual, formal, balanced
    enable_proactive_suggestions = models.BooleanField(default=True)
    
    # Privacy settings
    allow_conversation_analysis = models.BooleanField(default=True)
    share_data_for_improvements = models.BooleanField(default=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Preferences'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
