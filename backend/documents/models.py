from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#0288D1')  # Hex color for UI
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Document Categories"
        ordering = ['name']
        
    def __str__(self):
        return self.name


class CompanyDocument(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.CASCADE, related_name='documents')
    
    # File handling
    file = models.FileField(
        upload_to='company_documents/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'md'])]
    )
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    
    # Extracted content for AI search
    content_text = models.TextField(blank=True)  # Extracted text content
    content_summary = models.TextField(blank=True)  # AI-generated summary
    keywords = models.JSONField(default=list)  # Extracted keywords for search
    
    # Document management
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Analytics fields
    usage_count = models.IntegerField(default=0)
    effectiveness_score = models.FloatField(default=0.0)  # Based on user feedback
    last_referenced = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} (v{self.version})"
    
    def save(self, *args, **kwargs):
        # Set file size if file exists
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class DocumentVersion(models.Model):
    document = models.ForeignKey(CompanyDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=20)
    file = models.FileField(upload_to='document_versions/')
    content_text = models.TextField(blank=True)
    
    # Change tracking
    change_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['document', 'version_number']
        
    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class KnowledgeGap(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUS_CHOICES = [
        ('identified', 'Identified'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    
    # Gap identification
    query = models.CharField(max_length=500)  # What users were asking about
    frequency = models.IntegerField(default=1)  # How often this gap appears
    first_identified = models.DateTimeField(auto_now_add=True)
    last_encountered = models.DateTimeField(auto_now=True)
    
    # Classification
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='identified')
    
    # Resolution tracking
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Related conversations
    conversations = models.ManyToManyField('chat.Conversation', blank=True, related_name='knowledge_gaps')
    
    class Meta:
        ordering = ['-frequency', '-last_encountered']
        
    def __str__(self):
        return f"Gap: {self.query[:50]}... (freq: {self.frequency})"


class DocumentFeedback(models.Model):
    FEEDBACK_CHOICES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
        ('outdated', 'Outdated'),
        ('unclear', 'Unclear'),
    ]
    
    document = models.ForeignKey(CompanyDocument, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=15, choices=FEEDBACK_CHOICES)
    comment = models.TextField(blank=True)
    rating = models.IntegerField()  # 1-5 scale
    
    # Context
    conversation = models.ForeignKey('chat.Conversation', on_delete=models.CASCADE, null=True, blank=True)
    search_query = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['document', 'user', 'conversation']
        
    def __str__(self):
        return f"{self.feedback_type} feedback for {self.document.title}"
