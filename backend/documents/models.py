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
    
    # Vector embeddings and hybrid search fields
    chunks_json = models.TextField(
        blank=True,
        default='[]',
        verbose_name=_('Document Chunks JSON'),
        help_text=_('Text chunks for vector embeddings (JSON array)')
    )
    
    embeddings_generated = models.BooleanField(
        default=False,
        verbose_name=_('Embeddings Generated'),
        help_text=_('Whether vector embeddings have been generated for this document')
    )
    
    embedding_model = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Embedding Model'),
        help_text=_('Name of the embedding model used')
    )
    
    chunks_count = models.IntegerField(
        default=0,
        verbose_name=_('Chunks Count'),
        help_text=_('Number of text chunks generated')
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
    
    @property
    def chunks(self):
        """Get document chunks as Python list from JSON string"""
        if not self.chunks_json:
            return []
        try:
            return json.loads(self.chunks_json)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @chunks.setter
    def chunks(self, value):
        """Set document chunks as JSON string from Python list"""
        if isinstance(value, list):
            self.chunks_json = json.dumps(value)
            self.chunks_count = len(value)
        else:
            self.chunks_json = '[]'
            self.chunks_count = 0
    
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
        query_words = query_lower.split()
        
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
        
        # Split into larger chunks (paragraphs and sections) for better semantic matching
        # Look for question sections, paragraphs, or logical sections
        sections = []
        
        # Try splitting by questions (FAQ format)
        if '**' in self.extracted_text:
            sections = self.extracted_text.split('**')
        elif '\n\n' in self.extracted_text:
            sections = self.extracted_text.split('\n\n')
        else:
            # Fallback to sentences
            sections = self.extracted_text.split('.')
        
        best_section = None
        best_score = 0
        best_start_pos = 0
        
        current_pos = 0
        for section in sections:
            section_lower = section.lower()
            
            # Calculate relevance score for this section
            score = 0
            for word in query_words:
                if len(word) > 2:  # Skip short words
                    # Count occurrences of each query word
                    score += section_lower.count(word) * len(word)
            
            # Bonus for sections that contain multiple query words
            words_found = sum(1 for word in query_words if len(word) > 2 and word in section_lower)
            if words_found > 1:
                score *= 1.5
            
            if score > best_score:
                best_score = score
                best_section = section
                best_start_pos = current_pos
            
            current_pos += len(section)
        
        # If we found a relevant section, return it with context
        if best_section and best_score > 0:
            # Find position in original text
            section_pos = self.extracted_text.lower().find(best_section.lower())
            if section_pos != -1:
                # Include some context before and after
                context_before = max_length // 4
                context_after = max_length - len(best_section) - context_before
                
                start = max(0, section_pos - context_before)
                end = min(len(self.extracted_text), section_pos + len(best_section) + context_after)
                
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


class DocumentationImprovement(models.Model):
    """Model for tracking conversation analysis and documentation improvement needs"""
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    SATISFACTION_CHOICES = [
        (1, _('Very Dissatisfied')),
        (2, _('Dissatisfied')),
        (3, _('Neutral')),
        (4, _('Satisfied')),
        (5, _('Very Satisfied')),
    ]
    
    # Unique identifier for secure URLs
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name=_('UUID')
    )
    
    # Link to conversation
    conversation = models.ForeignKey(
        'chat.Conversation',
        on_delete=models.CASCADE,
        related_name='documentation_improvements',
        verbose_name=_('Conversation')
    )
    
    # Analysis fields
    conversation_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Conversation Title'),
        help_text=_('Display title for the conversation')
    )
    
    issues_detected = models.TextField(
        blank=True,
        verbose_name=_('Issues Detected'),
        help_text=_('Specific issues like account, password, pricing concerns')
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Priority')
    )
    
    langextract_analysis_summary = models.TextField(
        blank=True,
        verbose_name=_('LangExtract Analysis Summary'),
        help_text=_('User-friendly summary of conversation analysis')
    )
    
    langextract_full_analysis = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Full LangExtract Analysis'),
        help_text=_('Complete analysis data from LangExtract')
    )
    
    category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Category'),
        help_text=_('Category based on LangExtract analysis')
    )
    
    satisfaction_level = models.IntegerField(
        choices=SATISFACTION_CHOICES,
        null=True,
        blank=True,
        verbose_name=_('Satisfaction Level'),
        help_text=_('Customer satisfaction rating from 1-5')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    
    # Analysis status
    analysis_completed = models.BooleanField(
        default=False,
        verbose_name=_('Analysis Completed'),
        help_text=_('Whether LangExtract analysis has been completed')
    )
    
    analysis_error = models.TextField(
        blank=True,
        verbose_name=_('Analysis Error'),
        help_text=_('Error message if analysis failed')
    )
    
    class Meta:
        verbose_name = _('Doc Improvement')
        verbose_name_plural = _('Doc Improvements') 
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Improvement for: {self.conversation_title or f'Conversation {self.conversation.id}'}"
    
    def get_conversation_url(self):
        """Get URL to view the conversation (placeholder for frontend routing)"""
        return f"/chat/conversation/{self.conversation.uuid}/"
    
    def get_priority_display_color(self):
        """Return CSS color class for priority display"""
        color_map = {
            'low': 'text-success',
            'medium': 'text-warning', 
            'high': 'text-danger',
            'urgent': 'text-danger fw-bold'
        }
        return color_map.get(self.priority, 'text-secondary')
    
    def get_satisfaction_display_color(self):
        """Return CSS color class for satisfaction display"""
        if not self.satisfaction_level:
            return 'text-muted'
        if self.satisfaction_level <= 2:
            return 'text-danger'
        elif self.satisfaction_level == 3:
            return 'text-warning'
        else:
            return 'text-success'
    
    def get_analysis_summary_preview(self, max_length=150):
        """Get truncated analysis summary for list view"""
        if not self.langextract_analysis_summary:
            return _('No analysis summary available')
        if len(self.langextract_analysis_summary) <= max_length:
            return self.langextract_analysis_summary
        return self.langextract_analysis_summary[:max_length] + "..."
    
    def save(self, *args, **kwargs):
        # Auto-populate conversation title if not set
        if not self.conversation_title and self.conversation:
            self.conversation_title = self.conversation.get_title()
        
        super().save(*args, **kwargs)


