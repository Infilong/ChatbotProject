from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid
import json




class Conversation(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_('UUID'))
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
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_('UUID'))
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
    tokens_used = models.IntegerField(null=True, blank=True, verbose_name=_('Tokens Used'))
    
    # Message-level analysis (new field)
    message_analysis = models.JSONField(default=dict, blank=True, verbose_name=_('Message Analysis'))
    
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
            
            # Note: Automatic analysis is now handled by Django signals in chat/signals.py


class ConversationSummary(models.Model):
    """Automatic LLM-generated conversation analysis and insights"""
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name=_('UUID'))
    
    # LLM-generated content (main field)
    llm_analysis = models.TextField(default='', verbose_name=_('LLM Analysis'))
    
    # Analysis period (automatically determined)
    analysis_period = models.CharField(
        max_length=50,
        default='Unknown',
        verbose_name=_('Analysis Period'),
        help_text=_('Time period covered by this analysis (e.g., "Last 24 hours", "Today", "This week")')
    )
    
    # Automatic metadata
    messages_analyzed_count = models.IntegerField(default=0, verbose_name=_('Messages Analyzed'))
    critical_issues_found = models.IntegerField(default=0, verbose_name=_('Critical Issues Found'))
    
    # Auto-generation metadata
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Generated At'))
    trigger_reason = models.CharField(
        max_length=100,
        default='legacy_migration',
        verbose_name=_('Generation Trigger'),
        help_text=_('What triggered this automatic summary generation')
    )
    
    # LLM metadata
    llm_model_used = models.CharField(max_length=50, blank=True, verbose_name=_('LLM Model Used'))
    llm_response_time = models.FloatField(null=True, blank=True, verbose_name=_('LLM Response Time'))
    
    class Meta:
        verbose_name = _('Summary')
        verbose_name_plural = _('Summaries')
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Summary - {self.analysis_period} ({self.generated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def get_preview(self, length=200):
        """Get preview of LLM analysis"""
        if len(self.llm_analysis) <= length:
            return self.llm_analysis
        return self.llm_analysis[:length] + "..."


class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions', verbose_name=_('User'))
    session_id = models.CharField(max_length=100, unique=True, verbose_name=_('Session ID'))
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Started At'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    last_activity = models.DateTimeField(auto_now=True, verbose_name=_('Last Activity'))
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = _('Customer Session')
        verbose_name_plural = _('Customer Sessions')
        
    def __str__(self):
        return f"Customer Session {self.session_id} - {self.user.username}"
    
    def end_session(self):
        self.ended_at = timezone.now()
        self.is_active = False
        self.save()




class APIConfiguration(models.Model):
    """Model for storing LLM API configurations"""
    
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('gemini', 'Google Gemini'),
        ('claude', 'Anthropic Claude'),
    ]
    
    provider = models.CharField(
        max_length=20, 
        choices=PROVIDER_CHOICES, 
        unique=True, 
        verbose_name=_('Provider')
    )
    api_key = models.TextField(
        verbose_name=_('API Key'), 
        help_text=_('API key for the provider')
    )
    model_name = models.CharField(
        max_length=100, 
        verbose_name=_('Model Name')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('API Configuration')
        verbose_name_plural = _('API Configurations')
        ordering = ['provider']
    
    def __str__(self):
        return f"{self.get_provider_display()} - {'Active' if self.is_active else 'Inactive'}"




class AdminPrompt(models.Model):
    """Model for storing admin-defined system prompts for LLM"""
    
    PROMPT_TYPE_CHOICES = [
        ('system', _('System Prompt')),
        ('greeting', _('Greeting Prompt')),
        ('error', _('Error Handling')),
        ('clarification', _('Clarification Request')),
        ('escalation', _('Escalation Prompt')),
        ('closing', _('Conversation Closing')),
        ('instruction', _('Instruction Prompt')),
        ('custom', _('Custom Prompt')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Prompt Name'))
    prompt_type = models.CharField(
        max_length=20,
        choices=PROMPT_TYPE_CHOICES,
        verbose_name=_('Prompt Type')
    )
    prompt_text = models.TextField(
        verbose_name=_('Prompt Text'),
        help_text=_('The actual prompt text that will be sent to the LLM')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description of when and how this prompt is used')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    is_default = models.BooleanField(
        default=False,
        verbose_name=_('Is Default'),
        help_text=_('Use this as the default prompt for this type')
    )
    language = models.CharField(
        max_length=10,
        choices=[('en', _('English')), ('ja', _('Japanese'))],
        default='en',
        verbose_name=_('Language')
    )
    
    # Usage tracking
    usage_count = models.IntegerField(default=0, verbose_name=_('Usage Count'))
    last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Used'))
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Created By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Admin Prompt')
        verbose_name_plural = _('Admin Prompts')
        ordering = ['prompt_type', 'language', '-is_default', 'name']
    
    def __str__(self):
        default_marker = " (Default)" if self.is_default else ""
        return f"{self.name} [{self.get_prompt_type_display()}]{default_marker}"
    
    def get_preview(self, length=100):
        """Return a preview of the prompt text"""
        return self.prompt_text[:length] + "..." if len(self.prompt_text) > length else self.prompt_text
    
    def increment_usage(self):
        """Increment usage count and update last used timestamp"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
    
    def save(self, *args, **kwargs):
        # Ensure only one default per prompt_type and language
        if self.is_default:
            AdminPrompt.objects.filter(
                prompt_type=self.prompt_type,
                language=self.language,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
