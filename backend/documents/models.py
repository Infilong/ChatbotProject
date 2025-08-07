from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import os
import hashlib
import uuid


def calculate_file_hash(file):
    """Calculate SHA-256 hash of the file content"""
    hasher = hashlib.sha256()
    # Reset file pointer to beginning
    file.seek(0)
    # Read file in chunks to handle large files efficiently
    for chunk in iter(lambda: file.read(8192), b""):
        hasher.update(chunk)
    # Reset file pointer for subsequent operations
    file.seek(0)
    return hasher.hexdigest()


def validate_document_file(file):
    """Validate uploaded document file types, size, and check for duplicates"""
    # Allowed file extensions
    ALLOWED_EXTENSIONS = [
        '.pdf', '.txt', '.md', '.docx', '.doc', '.rtf', 
        '.json', '.csv', '.xlsx', '.xls', '.html', '.htm',
        '.ppt', '.pptx', '.zip', '.rar'
    ]
    
    # Maximum file size (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes
    
    # Get file extension
    ext = os.path.splitext(file.name)[1].lower()
    
    # Check file extension
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            _('Unsupported file type. Allowed types: %(extensions)s'),
            params={'extensions': ', '.join(ALLOWED_EXTENSIONS)}
        )
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(
            _('File size too large. Maximum size is 100MB. Your file is %(size).1f MB'),
            params={'size': file.size / (1024 * 1024)}
        )
    
    # Note: Duplicate check will be performed in the model's save method
    # to avoid circular import issues


class Document(models.Model):
    """Simple document management system for file operations"""
    
    # Unique identifier for secure URLs
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name=_('Document UUID')
    )
    
    # Basic Information
    name = models.CharField(
        max_length=255, 
        verbose_name=_('Document Name'),
        help_text=_('Display name for the document')
    )
    
    original_filename = models.CharField(
        max_length=255, 
        verbose_name=_('Original Filename'),
        editable=False
    )
    
    description = models.TextField(
        blank=True, 
        verbose_name=_('Description'),
        help_text=_('Brief description of the document')
    )
    
    # File upload
    file = models.FileField(
        upload_to='documents/%Y/%m/',
        validators=[validate_document_file],
        verbose_name=_('Document File'),
        help_text=_('Upload PDF, DOCX, TXT, MD, JSON, CSV, XLSX, RTF, HTML, PPT, ZIP (Max: 100MB)')
    )
    
    # File metadata (auto-filled)
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name=_('File Size'))
    file_type = models.CharField(max_length=10, blank=True, verbose_name=_('File Type'))
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        editable=False,
        db_index=True,  # Index for fast lookups without unique constraint
        verbose_name=_('File Hash'),
        help_text=_('SHA-256 hash for duplicate detection')
    )
    
    # Management
    category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Category'),
        help_text=_('Organize documents by category')
    )
    
    tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Tags'),
        help_text=_('Comma-separated tags for easy searching')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    
    # Audit fields
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Uploaded By')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_file_extension(self):
        """Return file extension in uppercase"""
        if self.file:
            return os.path.splitext(self.file.name)[1].upper().lstrip('.')
        return ""
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        if self.file_size:
            if self.file_size < 1024:
                return f"{self.file_size} B"
            elif self.file_size < 1024 * 1024:
                return f"{self.file_size / 1024:.1f} KB"
            else:
                return f"{self.file_size / (1024 * 1024):.1f} MB"
        return _("Unknown")
    
    def get_tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    def save(self, *args, **kwargs):
        # Set file metadata on save
        if self.file:
            # Calculate file hash if not already set or file has changed
            if not self.file_hash or self._file_has_changed():
                self.file_hash = calculate_file_hash(self.file)
            
            # Set other metadata
            if not self.file_size:
                self.file_size = self.file.size
            if not self.original_filename:
                self.original_filename = os.path.basename(self.file.name)
            if not self.file_type:
                self.file_type = self.get_file_extension()
            if not self.name:
                # Use original filename without extension as default name
                self.name = os.path.splitext(self.original_filename)[0].replace('_', ' ').title()
        
        super().save(*args, **kwargs)
    
    def _file_has_changed(self):
        """Check if the file has changed compared to database"""
        if not self.pk:
            return True
        try:
            original = Document.objects.get(pk=self.pk)
            return original.file != self.file
        except Document.DoesNotExist:
            return True


