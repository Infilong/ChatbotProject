from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class AIHelperChat(models.Model):
    """Chat session with AI Helper"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    session_id = models.CharField(max_length=100, unique=True, verbose_name=_('Session ID'))
    title = models.CharField(max_length=200, blank=True, verbose_name=_('Chat Title'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    
    class Meta:
        verbose_name = _('AI Helper Chat')
        verbose_name_plural = _('AI Helper Chats')
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title or f"Chat {self.session_id}"


class AIHelperMessage(models.Model):
    """Individual message in AI Helper chat"""
    
    MESSAGE_TYPE_CHOICES = [
        ('user', _('User')),
        ('assistant', _('AI Assistant')),
        ('system', _('System')),
    ]
    
    chat = models.ForeignKey(
        AIHelperChat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Chat')
    )
    
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        verbose_name=_('Message Type')
    )
    
    content = models.TextField(verbose_name=_('Content'))
    
    # Context data for AI responses
    context_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Context Data'),
        help_text=_('Additional context data used for AI response')
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        verbose_name = _('AI Helper Message')
        verbose_name_plural = _('AI Helper Messages')
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_message_type_display()}: {self.content[:50]}..."


class AIHelperKnowledgeBase(models.Model):
    """Knowledge base for AI Helper responses about the system"""
    
    CATEGORY_CHOICES = [
        ('documents', _('Document Management')),
        ('users', _('User Management')),
        ('chat', _('Chat System')),
        ('analytics', _('Analytics')),
        ('system', _('System Information')),
        ('api', _('API Information')),
        ('general', _('General Help')),
    ]
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name=_('Category')
    )
    
    topic = models.CharField(max_length=200, verbose_name=_('Topic'))
    question_patterns = models.TextField(
        verbose_name=_('Question Patterns'),
        help_text=_('Common questions or keywords that trigger this response')
    )
    
    response_template = models.TextField(
        verbose_name=_('Response Template'),
        help_text=_('Template response for this topic')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('AI Helper Knowledge')
        verbose_name_plural = _('AI Helper Knowledge Base')
        ordering = ['category', 'topic']
    
    def __str__(self):
        return f"{self.get_category_display()}: {self.topic}"