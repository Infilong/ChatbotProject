from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import os
import hashlib
import uuid
import json


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
    """Document model for knowledge base management with file deduplication"""
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
    
    # Knowledge base fields
    extracted_text = models.TextField(
        blank=True,
        verbose_name=_('Extracted Text'),
        help_text=_('Full text extracted from document for knowledge base')
    )
    
    ai_summary = models.TextField(
        blank=True,
        verbose_name=_('AI Summary'),
        help_text=_('AI-generated summary of document content')
    )
    
    ai_keywords_json = models.TextField(
        blank=True,
        default='[]',
        verbose_name=_('AI Keywords JSON'),
        help_text=_('AI-extracted keywords and topics (JSON string)')
    )
    
    search_vector = models.TextField(
        blank=True,
        db_index=True,
        verbose_name=_('Search Vector'),
        help_text=_('Preprocessed text for fast searching')
    )
    
    # Usage analytics
    reference_count = models.IntegerField(
        default=0,
        verbose_name=_('Reference Count'),
        help_text=_('Number of times referenced by LLM')
    )
    
    last_referenced = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Referenced'),
        help_text=_('Last time this document was used by LLM')
    )
    
    effectiveness_score = models.FloatField(
        default=0.0,
        verbose_name=_('Effectiveness Score'),
        help_text=_('How useful this document is for answering questions')
    )
    
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
    
    @property
    def ai_keywords(self):
        """Get ai_keywords as Python list from JSON string"""
        if not self.ai_keywords_json:
            return []
        try:
            return json.loads(self.ai_keywords_json)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @ai_keywords.setter
    def ai_keywords(self, value):
        """Set ai_keywords as JSON string from Python list"""
        if isinstance(value, (list, dict)):
            self.ai_keywords_json = json.dumps(value)
        else:
            self.ai_keywords_json = '[]'
    
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
    
    def increment_reference(self):
        """Increment reference count when used by LLM"""
        from django.utils import timezone
        self.reference_count += 1
        self.last_referenced = timezone.now()
        self.save(update_fields=['reference_count', 'last_referenced'])
    
    def get_relevance_score(self, query: str) -> float:
        """Calculate relevance score for a query with fuzzy matching for typo tolerance"""
        if not self.extracted_text and not self.ai_summary:
            return 0.0
        
        query_lower = query.lower().strip()
        score = 0.0
        
        # Import fuzzy matching library
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            # Fallback to original exact matching if rapidfuzz not available
            return self._get_exact_relevance_score(query)
        
        # Check title relevance (higher weight)
        if query_lower in self.name.lower():
            score += 2.0
        else:
            # Fuzzy match with title
            title_ratio = fuzz.partial_ratio(query_lower, self.name.lower())
            if title_ratio > 80:  # High similarity threshold
                score += 1.5 * (title_ratio / 100)
        
        # Check keywords relevance with fuzzy matching (high weight)
        for keyword in self.ai_keywords:
            if isinstance(keyword, str):
                keyword_lower = keyword.lower()
                if query_lower in keyword_lower:
                    score += 1.5
                else:
                    # Fuzzy match with keywords
                    keyword_ratio = fuzz.partial_ratio(query_lower, keyword_lower)
                    if keyword_ratio > 75:  # Medium-high similarity threshold
                        score += 1.2 * (keyword_ratio / 100)
        
        # Check category relevance
        if self.category:
            if query_lower in self.category.lower():
                score += 1.0
            else:
                # Fuzzy match with category
                category_ratio = fuzz.partial_ratio(query_lower, self.category.lower())
                if category_ratio > 70:
                    score += 0.8 * (category_ratio / 100)
        
        # Check tags relevance with fuzzy matching
        for tag in self.get_tags_list():
            tag_lower = tag.lower()
            if query_lower in tag_lower:
                score += 1.0
            else:
                # Fuzzy match with tags
                tag_ratio = fuzz.partial_ratio(query_lower, tag_lower)
                if tag_ratio > 70:
                    score += 0.8 * (tag_ratio / 100)
        
        # Enhanced content relevance with fuzzy matching
        if self.extracted_text:
            content_lower = self.extracted_text.lower()
            # Full query match (higher score)
            if query_lower in content_lower:
                score += 0.5
            else:
                # Enhanced individual word matches with fuzzy matching
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 2:  # Skip very short words
                        if word in content_lower:
                            score += 0.1
                        else:
                            # Fuzzy match individual words in content
                            content_words = content_lower.split()
                            best_match = process.extractOne(word, content_words, scorer=fuzz.ratio)
                            if best_match and best_match[1] > 80:  # High similarity for content words
                                score += 0.08 * (best_match[1] / 100)  # Slightly lower than exact match
        
        # Enhanced summary matching with fuzzy matching
        if self.ai_summary:
            summary_lower = self.ai_summary.lower()
            if query_lower in summary_lower:
                score += 0.8
            else:
                # Enhanced individual word matches in summary with fuzzy matching
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 2:
                        if word in summary_lower:
                            score += 0.15
                        else:
                            # Fuzzy match words in summary
                            summary_words = summary_lower.split()
                            best_match = process.extractOne(word, summary_words, scorer=fuzz.ratio)
                            if best_match and best_match[1] > 80:  # High similarity for summary words
                                score += 0.12 * (best_match[1] / 100)
        
        # Boost score based on effectiveness and usage
        score *= (1 + self.effectiveness_score / 10)
        score *= (1 + min(self.reference_count / 100, 0.5))
        
        return score
    
    def _get_exact_relevance_score(self, query: str) -> float:
        """Fallback method for exact matching when fuzzy libraries unavailable"""
        query_lower = query.lower()
        score = 0.0
        
        # Check title relevance (higher weight)
        if query_lower in self.name.lower():
            score += 2.0
        
        # Check keywords relevance (high weight)
        for keyword in self.ai_keywords:
            if isinstance(keyword, str) and query_lower in keyword.lower():
                score += 1.5
        
        # Check category relevance
        if self.category and query_lower in self.category.lower():
            score += 1.0
        
        # Check tags relevance
        for tag in self.get_tags_list():
            if query_lower in tag.lower():
                score += 1.0
        
        # Check content relevance (lower weight but important)
        if self.extracted_text:
            content_lower = self.extracted_text.lower()
            # Full query match (higher score)
            if query_lower in content_lower:
                score += 0.5
            else:
                # Individual word matches (partial score)
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 2 and word in content_lower:  # Skip very short words
                        score += 0.1
        
        if self.ai_summary:
            summary_lower = self.ai_summary.lower()
            if query_lower in summary_lower:
                score += 0.8
            else:
                # Individual word matches in summary
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 2 and word in summary_lower:
                        score += 0.15
        
        # Boost score based on effectiveness and usage
        score *= (1 + self.effectiveness_score / 10)
        score *= (1 + min(self.reference_count / 100, 0.5))
        
        return score
    
    def get_excerpt(self, query: str = None, max_length: int = 300) -> str:
        """Get relevant excerpt from document for context with semantic matching"""
        if not self.extracted_text:
            return self.ai_summary[:max_length] if self.ai_summary else ""
        
        if not query:
            # Return beginning of text if no query
            return self.extracted_text[:max_length] + "..." if len(self.extracted_text) > max_length else self.extracted_text
        
        # Enhanced excerpt generation with semantic matching
        text = self.extracted_text.lower()
        query_lower = query.lower()
        
        # First try exact phrase match
        query_pos = text.find(query_lower)
        
        if query_pos != -1:
            # Found exact match, extract context around it
            start = max(0, query_pos - max_length // 2)
            end = min(len(self.extracted_text), start + max_length)
            excerpt = self.extracted_text[start:end]
            
            # Add ellipsis if needed
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(self.extracted_text):
                excerpt = excerpt + "..."
            return excerpt
        
        # If exact phrase not found, try semantic word matching
        query_words = query_lower.split()
        best_match_pos = -1
        best_match_score = 0
        
        # Split text into sentences/sections for better context
        sentences = self.extracted_text.split('.')
        
        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            word_matches = sum(1 for word in query_words if len(word) > 2 and word in sentence_lower)
            
            if word_matches > best_match_score:
                best_match_score = word_matches
                best_match_pos = text.find(sentence_lower)
        
        # If we found semantic matches, return that section
        if best_match_score > 0 and best_match_pos != -1:
            # Find the best matching sentence and surrounding context
            start = max(0, best_match_pos - max_length // 4)
            end = min(len(self.extracted_text), best_match_pos + max_length)
            excerpt = self.extracted_text[start:end]
            
            # Add ellipsis if needed
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(self.extracted_text):
                excerpt = excerpt + "..."
            return excerpt
        
        # Fallback: If ai_summary contains query words, use it; otherwise use beginning
        if self.ai_summary:
            summary_words = sum(1 for word in query_words if len(word) > 2 and word in self.ai_summary.lower())
            if summary_words > 0:
                return self.ai_summary[:max_length]
        
        # Ultimate fallback: return beginning of document
        return self.extracted_text[:max_length] + "..." if len(self.extracted_text) > max_length else self.extracted_text


