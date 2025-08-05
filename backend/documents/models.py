from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    color = models.CharField(max_length=7, default='#0288D1', verbose_name=_('Color'))  # Hex color for UI
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        verbose_name = _('Document Category')
        verbose_name_plural = _('Document Categories')
        ordering = ['name']
        
    def __str__(self):
        return self.name


class CompanyDocument(models.Model):
    title = models.CharField(max_length=200, verbose_name=_('Title'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    category = models.ForeignKey(DocumentCategory, on_delete=models.CASCADE, related_name='documents', verbose_name=_('Category'))
    
    # File handling
    file = models.FileField(
        upload_to='company_documents/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'md'])],
        verbose_name=_('File')
    )
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name=_('File Size'))  # Size in bytes
    
    # Extracted content for AI search
    content_text = models.TextField(blank=True, verbose_name=_('Content Text'))  # Extracted text content
    content_summary = models.TextField(blank=True, verbose_name=_('Content Summary'))  # AI-generated summary
    keywords = models.JSONField(default=list, verbose_name=_('Keywords'))  # Extracted keywords for search
    
    # Document management
    version = models.CharField(max_length=20, default='1.0', verbose_name=_('Version'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents', verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    # Analytics fields
    usage_count = models.IntegerField(default=0, verbose_name=_('Usage Count'))
    effectiveness_score = models.FloatField(default=0.0, verbose_name=_('Effectiveness Score'))  # Based on user feedback
    last_referenced = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Referenced'))
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Company Document')
        verbose_name_plural = _('Company Documents')
        
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    def save(self, *args, **kwargs):
        # Set file size if file exists
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class DocumentVersion(models.Model):
    document = models.ForeignKey(CompanyDocument, on_delete=models.CASCADE, related_name='versions', verbose_name=_('Document'))
    version_number = models.CharField(max_length=20, verbose_name=_('Version Number'))
    file = models.FileField(upload_to='document_versions/', verbose_name=_('File'))
    content_text = models.TextField(blank=True, verbose_name=_('Content Text'))
    
    # Change tracking
    change_notes = models.TextField(blank=True, verbose_name=_('Change Notes'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Created By'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['document', 'version_number']
        verbose_name = _('Document Version')
        verbose_name_plural = _('Document Versions')
        
    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class KnowledgeGap(models.Model):
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('identified', _('Identified')),
        ('in_progress', _('In Progress')),
        ('resolved', _('Resolved')),
        ('dismissed', _('Dismissed')),
    ]
    
    # Gap identification
    query = models.CharField(max_length=500, verbose_name=_('Query'))  # What users were asking about
    frequency = models.IntegerField(default=1, verbose_name=_('Frequency'))  # How often this gap appears
    first_identified = models.DateTimeField(auto_now_add=True, verbose_name=_('First Identified'))
    last_encountered = models.DateTimeField(auto_now=True, verbose_name=_('Last Encountered'))
    
    # Classification
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Category'))
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Priority'))
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='identified', verbose_name=_('Status'))
    
    # Resolution tracking
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Assigned To'))
    resolution_notes = models.TextField(blank=True, verbose_name=_('Resolution Notes'))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Resolved At'))
    
    # Related conversations
    conversations = models.ManyToManyField('chat.Conversation', blank=True, related_name='knowledge_gaps')
    
    class Meta:
        ordering = ['-frequency', '-last_encountered']
        verbose_name = _('Knowledge Gap')
        verbose_name_plural = _('Knowledge Gaps')
        
    def __str__(self):
        return f"Gap: {self.query[:50]}... (freq: {self.frequency})"


class DocumentFeedback(models.Model):
    FEEDBACK_CHOICES = [
        ('helpful', _('Helpful')),
        ('not_helpful', _('Not Helpful')),
        ('outdated', _('Outdated')),
        ('unclear', _('Unclear')),
    ]
    
    document = models.ForeignKey(CompanyDocument, on_delete=models.CASCADE, related_name='feedback', verbose_name=_('Document'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('User'))
    feedback_type = models.CharField(max_length=15, choices=FEEDBACK_CHOICES, verbose_name=_('Feedback Type'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    rating = models.IntegerField(verbose_name=_('Rating'))  # 1-5 scale
    
    # Context
    conversation = models.ForeignKey('chat.Conversation', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Conversation'))
    search_query = models.CharField(max_length=200, blank=True, verbose_name=_('Search Query'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['document', 'user', 'conversation']
        verbose_name = _('Document Feedback')
        verbose_name_plural = _('Document Feedback')
        
    def __str__(self):
        return f"{self.feedback_type} feedback for {self.document.title}"
