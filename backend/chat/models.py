from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations', verbose_name=_('User'))
    title = models.CharField(max_length=200, blank=True, verbose_name=_('Title'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    
    # Analytics fields
    total_messages = models.IntegerField(default=0, verbose_name=_('Total Messages'))
    satisfaction_score = models.FloatField(null=True, blank=True, verbose_name=_('Satisfaction Score'))
    langextract_analysis = models.JSONField(default=dict, blank=True, verbose_name=_('LangExtract Analysis'))
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Conversation')
        verbose_name_plural = _('Conversations')
        
    def __str__(self):
        return f"Conversation {self.id} - {self.user.username}"
    
    def get_title(self):
        """Generate title from first message if not set"""
        if self.title:
            return self.title
        first_message = self.messages.filter(sender_type='user').first()
        if first_message:
            return first_message.content[:50] + "..." if len(first_message.content) > 50 else first_message.content
        return f"Conversation {self.id}"


class Message(models.Model):
    SENDER_CHOICES = [
        ('user', _('User')),
        ('bot', _('Bot')),
        ('admin', _('Admin')),
    ]
    
    FEEDBACK_CHOICES = [
        ('positive', _('Positive')),
        ('negative', _('Negative')),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', verbose_name=_('Conversation'))
    content = models.TextField(verbose_name=_('Content'))
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES, verbose_name=_('Sender Type'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))
    
    # Optional fields
    feedback = models.CharField(max_length=10, choices=FEEDBACK_CHOICES, null=True, blank=True, verbose_name=_('Feedback'))
    file_attachment = models.FileField(upload_to='message_attachments/', null=True, blank=True, verbose_name=_('File Attachment'))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))
    
    # Bot response metadata
    response_time = models.FloatField(null=True, blank=True, verbose_name=_('Response Time'))
    llm_model_used = models.CharField(max_length=50, null=True, blank=True, verbose_name=_('LLM Model Used'))
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        
    def __str__(self):
        return f"{self.sender_type}: {self.content[:50]}..."
    
    def save(self, *args, **kwargs):
        # Update conversation's total_messages count
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.conversation.total_messages += 1
            self.conversation.save(update_fields=['total_messages', 'updated_at'])


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions', verbose_name=_('User'))
    session_id = models.CharField(max_length=100, unique=True, verbose_name=_('Session ID'))
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Started At'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    
    # Session analytics
    total_conversations = models.IntegerField(default=0, verbose_name=_('Total Conversations'))
    total_messages_sent = models.IntegerField(default=0, verbose_name=_('Total Messages Sent'))
    average_response_time = models.FloatField(null=True, blank=True, verbose_name=_('Average Response Time'))
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = _('User Session')
        verbose_name_plural = _('User Sessions')
        
    def __str__(self):
        return f"Session {self.session_id} - {self.user.username}"
    
    def end_session(self):
        self.ended_at = timezone.now()
        self.is_active = False
        self.save()


class TestModel(models.Model):
    """Simple test model to verify admin functionality"""
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        verbose_name = _('Test Model')
        verbose_name_plural = _('Test Models')
    
    def __str__(self):
        return self.name
