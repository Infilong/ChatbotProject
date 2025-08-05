from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Analytics fields
    total_messages = models.IntegerField(default=0)
    satisfaction_score = models.FloatField(null=True, blank=True)
    langextract_analysis = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        
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
        ('user', 'User'),
        ('bot', 'Bot'),
        ('admin', 'Admin'),
    ]
    
    FEEDBACK_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    sender_type = models.CharField(max_length=10, choices=SENDER_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional fields
    feedback = models.CharField(max_length=10, choices=FEEDBACK_CHOICES, null=True, blank=True)
    file_attachment = models.FileField(upload_to='message_attachments/', null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Bot response metadata
    response_time = models.FloatField(null=True, blank=True)
    llm_model_used = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Session analytics
    total_conversations = models.IntegerField(default=0)
    total_messages_sent = models.IntegerField(default=0)
    average_response_time = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        
    def __str__(self):
        return f"Session {self.session_id} - {self.user.username}"
    
    def end_session(self):
        self.ended_at = timezone.now()
        self.is_active = False
        self.save()
