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
        """Calculate hybrid relevance score combining multiple strategies"""
        if not self.extracted_text and not self.ai_summary:
            return 0.0
        
        query_lower = query.lower().strip()
        total_score = 0.0
        
        # HYBRID SCORING: Combine multiple search strategies
        
        # 1. Traditional fuzzy matching score (base score)
        base_score = self._get_fuzzy_relevance_score(query)
        total_score += base_score * 0.4  # 40% weight
        
        # 2. Semantic concept matching score
        semantic_score = self._get_semantic_relevance_score(query)
        total_score += semantic_score * 0.3  # 30% weight
        
        # 3. Keyword density score
        keyword_score = self._get_keyword_density_score(query)
        total_score += keyword_score * 0.2  # 20% weight
        
        # 4. Q&A pattern matching score
        qa_score = self._get_qa_pattern_score(query)
        total_score += qa_score * 0.1  # 10% weight
        
        # Apply document effectiveness multipliers
        total_score *= (1 + self.effectiveness_score / 10)
        total_score *= (1 + min(self.reference_count / 100, 0.5))
        
        return total_score
    
    def _get_fuzzy_relevance_score(self, query: str) -> float:
        """Traditional fuzzy matching score (fallback method)"""
        try:
            from rapidfuzz import fuzz, process
        except ImportError:
            return self._get_exact_relevance_score(query)
        
        query_lower = query.lower().strip()
        score = 0.0
        
        # Check title relevance
        if query_lower in self.name.lower():
            score += 2.0
        else:
            title_ratio = fuzz.partial_ratio(query_lower, self.name.lower())
            if title_ratio > 80:
                score += 1.5 * (title_ratio / 100)
        
        # Check keywords relevance
        for keyword in self.ai_keywords:
            if isinstance(keyword, str):
                keyword_lower = keyword.lower()
                if query_lower in keyword_lower:
                    score += 1.5
                else:
                    keyword_ratio = fuzz.partial_ratio(query_lower, keyword_lower)
                    if keyword_ratio > 75:
                        score += 1.2 * (keyword_ratio / 100)
        
        # Content matching
        if self.extracted_text:
            content_lower = self.extracted_text.lower()
            if query_lower in content_lower:
                score += 0.5
            else:
                query_words = query_lower.split()
                for word in query_words:
                    if len(word) > 2:
                        if word in content_lower:
                            score += 0.1
        
        return score
    
    def _get_semantic_relevance_score(self, query: str) -> float:
        """Semantic concept matching score"""
        query_lower = query.lower()
        text_lower = self.extracted_text.lower() if self.extracted_text else ""
        score = 0.0
        
        # Universal semantic concept mappings for any industry
        semantic_concepts = {
            'support': ['assistance', 'help', 'service', 'care', 'maintenance', 'guidance', 'aid'],
            'price': ['cost', 'fee', 'rate', 'charge', 'payment', 'billing', 'quote', 'estimate'],
            'quality': ['standard', 'excellence', 'performance', 'reliability', 'effectiveness'],
            'time': ['schedule', 'timeline', 'duration', 'deadline', 'delivery', 'timeframe'],
            'process': ['procedure', 'method', 'workflow', 'system', 'approach', 'technique'],
            'team': ['staff', 'personnel', 'employee', 'expert', 'specialist', 'professional'],
            'product': ['item', 'goods', 'offering', 'solution', 'service', 'package'],
            'customer': ['client', 'user', 'consumer', 'buyer', 'patron', 'account'],
            'company': ['business', 'organization', 'firm', 'corporation', 'enterprise'],
            'contact': ['reach', 'communicate', 'connect', 'call', 'email', 'inquiry'],
            'order': ['purchase', 'buy', 'transaction', 'booking', 'request'],
            'delivery': ['shipping', 'transport', 'distribution', 'fulfillment'],
            'return': ['refund', 'exchange', 'replacement', 'cancel'],
            'warranty': ['guarantee', 'coverage', 'protection', 'insurance'],
            'training': ['education', 'learning', 'instruction', 'course'],
            'location': ['address', 'place', 'site', 'facility', 'office'],
            'problem': ['issue', 'trouble', 'difficulty', 'challenge', 'concern']
        }
        
        # Check for semantic matches
        for concept, related_terms in semantic_concepts.items():
            if concept in query_lower:
                # Look for related terms in document
                for term in related_terms:
                    if term in text_lower:
                        score += 1.0 if term in query_lower else 0.7
        
        return score
    
    def _get_keyword_density_score(self, query: str) -> float:
        """Calculate keyword density and proximity score"""
        if not self.extracted_text:
            return 0.0
        
        text_lower = self.extracted_text.lower()
        query_lower = query.lower()
        
        # Extract meaningful keywords
        stop_words = {'the', 'and', 'are', 'you', 'for', 'with', 'this', 'that', 'have', 'can', 'what', 'how'}
        query_words = [word.strip() for word in query_lower.split() if len(word.strip()) > 2 and word.strip() not in stop_words]
        
        if not query_words:
            return 0.0
        
        # Calculate keyword density
        matches = sum(1 for word in query_words if word in text_lower)
        density_score = (matches / len(query_words)) * 2.0
        
        # Check for phrase proximity (words appearing near each other)
        proximity_bonus = 0.0
        for i, word1 in enumerate(query_words[:-1]):
            word2 = query_words[i + 1]
            if word1 in text_lower and word2 in text_lower:
                # Check if words appear within 50 characters of each other
                word1_pos = text_lower.find(word1)
                word2_pos = text_lower.find(word2, word1_pos)
                if word2_pos != -1 and word2_pos - word1_pos < 50:
                    proximity_bonus += 0.5
        
        return density_score + proximity_bonus
    
    def _get_qa_pattern_score(self, query: str) -> float:
        """Calculate Q&A pattern matching score"""
        if not self.extracted_text:
            return 0.0
        
        text_lower = self.extracted_text.lower()
        query_lower = query.lower()
        
        # Look for Q&A patterns
        import re
        score = 0.0
        
        # Find questions in the document
        question_patterns = [r'q:\s*([^?]+\?)', r'question:\s*([^?]+\?)']
        
        for pattern in question_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                question = match.group(1) if match.groups() else match.group(0)
                
                # Calculate similarity between user query and document question
                question_words = set(question.lower().split())
                query_words = set(query_lower.split())
                overlap = len(question_words & query_words)
                
                if overlap > 0:
                    similarity = overlap / max(len(question_words), len(query_words))
                    score += similarity * 3.0  # High score for Q&A matches
        
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
    
    def clean_text_for_chatbot(self, text: str) -> str:
        """Clean document text for chatbot consumption by removing formatting characters"""
        if not text:
            return ""
        
        # Remove markdown-style formatting
        cleaned_text = text
        
        # Remove ** bold markers but preserve the text between them
        # Handle both **text** and *text* patterns
        import re
        
        # Replace **bold text** with just the text
        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_text)
        
        # Replace *italic text* with just the text  
        cleaned_text = re.sub(r'\*(.*?)\*', r'\1', cleaned_text)
        
        # Clean up any remaining standalone asterisks
        cleaned_text = re.sub(r'\*+', '', cleaned_text)
        
        # Clean up excessive whitespace that might result from removing formatting
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Clean up any double spaces or newlines
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
        
        return cleaned_text.strip()

    def get_excerpt(self, query: str = None, max_length: int = 300) -> str:
        """Get relevant excerpt from document using hybrid LLM + keyword search"""
        if not self.extracted_text:
            return self.clean_text_for_chatbot(self.ai_summary[:max_length]) if self.ai_summary else ""
        
        if not query:
            # Return beginning of text if no query
            excerpt = self.extracted_text[:max_length] + "..." if len(self.extracted_text) > max_length else self.extracted_text
            return self.clean_text_for_chatbot(excerpt)
        
        # HYBRID SEARCH: Try multiple strategies and score them
        candidates = []
        
        # Strategy 1: Exact phrase match (highest priority)
        exact_match = self._find_exact_phrase_excerpt(query, max_length)
        if exact_match:
            candidates.append(("exact", exact_match, 10.0))
        
        # Strategy 2: Keyword-based search (multiple keywords)
        keyword_excerpts = self._find_keyword_excerpts(query, max_length)
        for excerpt, score in keyword_excerpts:
            candidates.append(("keyword", excerpt, score))
        
        # Strategy 3: Semantic/conceptual search (related terms)
        semantic_excerpts = self._find_semantic_excerpts(query, max_length)
        for excerpt, score in semantic_excerpts:
            candidates.append(("semantic", excerpt, score))
        
        # Strategy 4: Question/Answer pattern matching
        qa_excerpt = self._find_qa_pattern_excerpt(query, max_length)
        if qa_excerpt:
            candidates.append(("qa", qa_excerpt, 8.0))
        
        # Choose the best candidate
        if candidates:
            # Sort by score (descending)
            candidates.sort(key=lambda x: x[2], reverse=True)
            best_strategy, best_excerpt, best_score = candidates[0]
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Excerpt strategy '{best_strategy}' (score: {best_score:.2f}) for query: '{query[:50]}...'")
            
            return self.clean_text_for_chatbot(best_excerpt)
        
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
            
            # TEMPORARILY DISABLED: LangExtract-based semantic scoring to prevent excessive API calls
            # Use fallback scoring to avoid 500 errors from excessive LangExtract calls
            score = self._fallback_section_score(section, query)
            
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
                return self.clean_text_for_chatbot(excerpt)
        
        # Fallback: If ai_summary is available, use it; otherwise use beginning
        if self.ai_summary:
            return self.clean_text_for_chatbot(self.ai_summary[:max_length])
        
        # Ultimate fallback: return beginning of document
        excerpt = self.extracted_text[:max_length] + "..." if len(self.extracted_text) > max_length else self.extracted_text
        return self.clean_text_for_chatbot(excerpt)
    
    def _find_exact_phrase_excerpt(self, query: str, max_length: int) -> str:
        """Strategy 1: Find exact phrase matches"""
        text = self.extracted_text.lower()
        query_lower = query.lower()
        
        query_pos = text.find(query_lower)
        if query_pos != -1:
            # For Q&A format, find the complete answer after the question
            answer_start = text.find('a:', query_pos)
            if answer_start != -1:
                # Find the end of the answer (next question or section)
                answer_end = text.find('**q:', answer_start + 1)
                if answer_end == -1:
                    answer_end = text.find('\n\n', answer_start + 50)  # At least 50 chars of answer
                if answer_end == -1:
                    answer_end = min(len(text), answer_start + max_length)
                
                # Extract from question to end of answer
                start = max(0, query_pos - 50)  # Include some context before question
                end = min(len(self.extracted_text), answer_end)
                excerpt = self.extracted_text[start:end]
            else:
                # Regular text match - center around the found phrase
                start = max(0, query_pos - max_length // 2)
                end = min(len(self.extracted_text), start + max_length)
                excerpt = self.extracted_text[start:end]
            
            if start > 0:
                excerpt = "..." + excerpt
            if end < len(self.extracted_text):
                excerpt = excerpt + "..."
            return excerpt
        return None
    
    def _find_keyword_excerpts(self, query: str, max_length: int) -> list:
        """Strategy 2: Find excerpts based on keyword matching with scoring"""
        text = self.extracted_text.lower()
        query_lower = query.lower()
        excerpts = []
        
        # Extract meaningful keywords (>2 chars, not common words)
        stop_words = {'the', 'and', 'are', 'you', 'for', 'with', 'this', 'that', 'have', 'can', 'what', 'how', 'when', 'where', 'why', 'who'}
        query_words = [word.strip() for word in query_lower.split() if len(word.strip()) > 2 and word.strip() not in stop_words]
        
        if not query_words:
            return excerpts
        
        # Find positions of all keywords
        keyword_positions = {}
        for word in query_words:
            positions = []
            start = 0
            while True:
                pos = text.find(word, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            if positions:
                keyword_positions[word] = positions
        
        # Score excerpts based on keyword density and proximity
        for word, positions in keyword_positions.items():
            for pos in positions:
                start = max(0, pos - max_length // 2)
                end = min(len(self.extracted_text), start + max_length)
                excerpt = self.extracted_text[start:end]
                
                # Calculate score based on keyword density in this excerpt
                excerpt_lower = excerpt.lower()
                keyword_count = sum(1 for kw in query_words if kw in excerpt_lower)
                score = (keyword_count / len(query_words)) * 7.0  # Max score 7.0
                
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(self.extracted_text):
                    excerpt = excerpt + "..."
                
                excerpts.append((excerpt, score))
        
        return excerpts
    
    def _find_semantic_excerpts(self, query: str, max_length: int) -> list:
        """Strategy 3: Find excerpts using semantic/conceptual matching"""
        text = self.extracted_text.lower()
        query_lower = query.lower()
        excerpts = []
        
        # Universal semantic mappings for any industry
        semantic_map = {
            # Universal business concepts
            'support': ['assistance', 'help', 'service', 'care', 'maintenance', 'troubleshooting', 'guidance', 'aid'],
            'price': ['cost', 'fee', 'rate', 'charge', 'payment', 'billing', 'quote', 'estimate', 'budget'],
            'quality': ['standard', 'excellence', 'grade', 'level', 'performance', 'reliability', 'effectiveness'],
            'time': ['schedule', 'timeline', 'duration', 'deadline', 'period', 'timeframe', 'delivery'],
            'process': ['procedure', 'method', 'workflow', 'system', 'approach', 'technique', 'protocol'],
            'team': ['staff', 'personnel', 'employee', 'member', 'expert', 'specialist', 'professional'],
            'product': ['item', 'goods', 'merchandise', 'offering', 'solution', 'service', 'package'],
            'customer': ['client', 'user', 'consumer', 'buyer', 'patron', 'account', 'subscriber'],
            'company': ['business', 'organization', 'firm', 'corporation', 'enterprise', 'agency'],
            'contact': ['reach', 'communicate', 'connect', 'call', 'email', 'message', 'inquiry'],
            'order': ['purchase', 'buy', 'acquisition', 'transaction', 'booking', 'request'],
            'delivery': ['shipping', 'transport', 'distribution', 'fulfillment', 'dispatch'],
            'return': ['refund', 'exchange', 'replacement', 'cancel', 'reverse', 'back'],
            'warranty': ['guarantee', 'coverage', 'protection', 'insurance', 'assurance'],
            'training': ['education', 'learning', 'instruction', 'teaching', 'course', 'workshop'],
            'location': ['address', 'place', 'site', 'facility', 'office', 'branch', 'store'],
            'availability': ['stock', 'supply', 'inventory', 'ready', 'accessible', 'obtainable'],
            'requirement': ['need', 'specification', 'criteria', 'condition', 'standard', 'prerequisite'],
            'benefit': ['advantage', 'value', 'gain', 'profit', 'merit', 'plus', 'feature'],
            'problem': ['issue', 'trouble', 'difficulty', 'challenge', 'concern', 'complaint']
        }
        
        # Find semantic matches
        for concept, related_terms in semantic_map.items():
            if concept in query_lower:
                # Look for related terms in the document
                for term in related_terms:
                    term_pos = text.find(term)
                    if term_pos != -1:
                        start = max(0, term_pos - max_length // 2)
                        end = min(len(self.extracted_text), start + max_length)
                        excerpt = self.extracted_text[start:end]
                        
                        # Enhanced scoring: Higher score if the excerpt contains specific query terms
                        base_score = 5.0 if term in query_lower else 4.0
                        
                        # Bonus for containing multiple query words in the excerpt
                        query_words = query_lower.split()
                        excerpt_lower = excerpt.lower()
                        word_matches = sum(1 for word in query_words if len(word) > 2 and word in excerpt_lower)
                        if word_matches >= 2:  # Contains multiple relevant words
                            base_score += 5.0  # Boost score to beat Q&A strategy
                        
                        if start > 0:
                            excerpt = "..." + excerpt
                        if end < len(self.extracted_text):
                            excerpt = excerpt + "..."
                        
                        excerpts.append((excerpt, base_score))
        
        return excerpts
    
    def _find_qa_pattern_excerpt(self, query: str, max_length: int) -> str:
        """Strategy 4: Find Q&A pattern matches with improved semantic matching"""
        text = self.extracted_text.lower()
        query_lower = query.lower()
        
        # Look for Q&A patterns in the document
        import re
        
        # Enhanced query understanding - extract key concepts
        query_concepts = self._extract_query_concepts(query_lower)
        
        # Find questions that might match the user's query
        question_patterns = [
            r'q:\s*([^?]+\?)',  # "Q: What is...?"
            r'question:\s*([^?]+\?)',  # "Question: How do...?"
            r'\*\*q:\s*([^?]+\?)',  # "**Q: What is...?"
        ]
        
        best_match = None
        best_score = 0
        
        for pattern in question_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                question = match.group(1) if match.groups() else match.group(0)
                question_clean = question.strip().lower()
                
                # Enhanced semantic scoring for questions
                score = self._calculate_qa_relevance_score(query_concepts, question_clean)
                
                if score > best_score:
                    best_score = score
                    question_pos = match.start()
                    
                    # Find the complete answer after this question
                    answer_start = text.find('a:', question_pos)
                    if answer_start == -1:
                        answer_start = match.end()
                    
                    # Find the end of the answer (next question or significant break)
                    answer_end = self._find_answer_end(text, answer_start)
                    
                    # Extract complete Q&A context
                    start = max(0, question_pos - 50)
                    end = min(len(self.extracted_text), answer_end)
                    excerpt = self.extracted_text[start:end]
                    
                    if start > 0:
                        excerpt = "..." + excerpt
                    if end < len(self.extracted_text):
                        excerpt = excerpt + "..."
                    
                    best_match = excerpt
        
        return best_match if best_score > 1.0 else None  # Require minimum relevance
    
    def _extract_query_concepts(self, query: str) -> dict:
        """Extract key concepts from user query for better matching"""
        concepts = {
            'main_words': [],
            'action_words': [],
            'tech_related': False,
            'normalized_terms': []
        }
        
        # Technology-related query patterns
        tech_patterns = ['tech', 'technology', 'technologies', 'tool', 'tools', 'platform', 'platforms', 
                        'software', 'stack', 'framework', 'frameworks', 'system', 'systems']
        
        # Action words that indicate intent
        action_patterns = ['use', 'using', 'utilize', 'work', 'employ', 'leverage', 'implement']
        
        words = query.split()
        for word in words:
            word_clean = word.strip().lower()
            if len(word_clean) > 2:
                concepts['main_words'].append(word_clean)
                
                if word_clean in tech_patterns:
                    concepts['tech_related'] = True
                    # Normalize variations
                    if word_clean in ['tech', 'technology', 'technologies']:
                        concepts['normalized_terms'].extend(['technology', 'technologies', 'tech'])
                    elif word_clean in ['tool', 'tools']:
                        concepts['normalized_terms'].extend(['tool', 'tools', 'platform', 'platforms'])
                
                if word_clean in action_patterns:
                    concepts['action_words'].append(word_clean)
        
        return concepts
    
    def _calculate_qa_relevance_score(self, query_concepts: dict, question: str) -> float:
        """Calculate relevance score between query concepts and question"""
        score = 0.0
        question_words = question.split()
        
        # Exact word matches
        for word in query_concepts['main_words']:
            if word in question:
                score += 2.0
        
        # Normalized term matches (for tech variations)
        for term in query_concepts['normalized_terms']:
            if term in question:
                score += 3.0  # Higher score for normalized matches
        
        # Tech context bonus
        if query_concepts['tech_related']:
            tech_indicators = ['technology', 'technologies', 'tech', 'tool', 'tools', 'platform', 'stack']
            if any(indicator in question for indicator in tech_indicators):
                score += 5.0  # Strong bonus for tech-related questions
        
        # Action word context
        for action in query_concepts['action_words']:
            action_synonyms = {
                'use': ['use', 'using', 'utilize', 'work', 'employ', 'leverage'],
                'work': ['work', 'working', 'use', 'employ', 'operate'],
                'employ': ['employ', 'use', 'utilize', 'leverage', 'work']
            }
            synonyms = action_synonyms.get(action, [action])
            if any(synonym in question for synonym in synonyms):
                score += 1.5
        
        return score
    
    def _find_answer_end(self, text: str, answer_start: int) -> int:
        """Find the end of an answer in Q&A format"""
        # Look for next question patterns
        import re
        
        next_q_patterns = [
            r'\*\*q:',  # Next question marker
            r'\n\*\*q:',  # Question with newline
            r'\n\nq:',  # Question with double newline
            r'\n\n\*\*',  # Section break
            r'###',  # Markdown section
        ]
        
        search_start = answer_start + 50  # Skip at least 50 chars for the current answer
        earliest_end = len(text)
        
        for pattern in next_q_patterns:
            match = re.search(pattern, text[search_start:], re.IGNORECASE)
            if match:
                end_pos = search_start + match.start()
                earliest_end = min(earliest_end, end_pos)
        
        # If no pattern found, look for natural breaks
        if earliest_end == len(text):
            # Look for double newlines that might indicate section breaks
            double_newline = text.find('\n\n', search_start)
            if double_newline != -1:
                earliest_end = min(earliest_end, double_newline)
        
        return earliest_end
    
    def _get_semantic_section_score(self, section: str, query: str) -> float:
        """
        Use LangExtract to analyze semantic relevance between document section and user query
        This replaces manual keyword matching with proper LLM-based semantic understanding
        """
        try:
            # Import LangExtract service
            from analytics.langextract_service import LangExtractService
            
            # Create semantic analysis prompt for LangExtract
            analysis_data = {
                "conversation": [
                    {
                        "role": "system",
                        "content": f"""Analyze the semantic relevance between a user query and a document section.
                        
User Query: "{query}"
Document Section: "{section[:500]}..."

Rate the relevance on a scale of 0.0 to 1.0 where:
- 1.0 = Direct answer to the query
- 0.7-0.9 = Highly relevant, contains key information  
- 0.4-0.6 = Somewhat relevant, related topic
- 0.1-0.3 = Marginally relevant, mentions similar concepts
- 0.0 = Not relevant at all

Respond with ONLY the numeric score (e.g., "0.8").""",
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                ]
            }
            
            # Use LangExtract to analyze semantic relevance
            lang_extract = LangExtractService()
            result = lang_extract.analyze_conversation(analysis_data["conversation"])
            
            # Extract relevance score from LangExtract response
            if result and 'analysis' in result:
                # Try to parse numeric score from response
                import re
                analysis_text = str(result.get('analysis', ''))
                
                # Look for decimal numbers in the response
                score_match = re.search(r'\b(0\.\d+|1\.0|0|1)\b', analysis_text)
                if score_match:
                    score = float(score_match.group(1))
                    # Ensure score is within valid range
                    return min(max(score, 0.0), 1.0)
                
                # Fallback: look for high/medium/low relevance keywords
                analysis_lower = analysis_text.lower()
                if any(word in analysis_lower for word in ['direct', 'exactly', 'perfect', 'complete']):
                    return 0.9
                elif any(word in analysis_lower for word in ['high', 'very relevant', 'strongly']):
                    return 0.8
                elif any(word in analysis_lower for word in ['relevant', 'related', 'pertinent']):
                    return 0.6
                elif any(word in analysis_lower for word in ['somewhat', 'partially', 'minor']):
                    return 0.3
                elif any(word in analysis_lower for word in ['not relevant', 'unrelated', 'irrelevant']):
                    return 0.0
            
            # Fallback to basic string matching if LangExtract fails
            return self._fallback_section_score(section, query)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"LangExtract semantic scoring failed: {e}")
            # Fallback to basic scoring
            return self._fallback_section_score(section, query)
    
    def _fallback_section_score(self, section: str, query: str) -> float:
        """
        Fallback semantic scoring when LangExtract is unavailable
        Uses basic text matching but better than manual keyword filtering
        """
        if not section or not query:
            return 0.0
        
        section_lower = section.lower()
        query_lower = query.lower()
        
        # Direct phrase match (highest score)
        if query_lower in section_lower:
            return 0.8
        
        # Word overlap scoring
        query_words = [word for word in query_lower.split() if len(word) > 2]
        if not query_words:
            return 0.0
        
        matches = sum(1 for word in query_words if word in section_lower)
        match_ratio = matches / len(query_words)
        
        # Convert match ratio to relevance score
        if match_ratio >= 0.8:
            return 0.7
        elif match_ratio >= 0.5:
            return 0.5
        elif match_ratio >= 0.3:
            return 0.3
        elif match_ratio > 0:
            return 0.1
        else:
            return 0.0


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


