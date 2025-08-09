"""
Knowledge base service for document retrieval and LLM integration
"""

import logging
from typing import List, Dict, Tuple, Optional
from django.db.models import Q
from django.utils import timezone

from .models import Document

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Service for managing and querying the document knowledge base"""
    
    @classmethod
    def search_relevant_documents(
        cls, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.1
    ) -> List[Document]:
        """
        Search for documents relevant to a query
        
        Returns:
            List of documents sorted by relevance
        """
        if not query.strip():
            return []
        
        try:
            # Get active documents with content
            active_docs = Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text='')
            
            if not active_docs.exists():
                logger.info("No active documents with extracted text found")
                return []
            
            # Score documents by relevance
            scored_docs = []
            for doc in active_docs:
                score = doc.get_relevance_score(query)
                if score >= min_score:
                    scored_docs.append((doc, score))
            
            # Sort by relevance score (descending)
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Return just the documents (not the scores)
            return [doc for doc, score in scored_docs[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    @classmethod
    def get_knowledge_context(
        cls, 
        query: str, 
        max_documents: int = 3,
        max_context_length: int = 2000
    ) -> Tuple[str, List[Document]]:
        """
        Get knowledge context for LLM from relevant documents
        
        Returns:
            Tuple of (formatted_context, list_of_referenced_documents)
        """
        relevant_docs = cls.search_relevant_documents(query, limit=max_documents)
        
        if not relevant_docs:
            return "", []
        
        context_parts = []
        referenced_docs = []
        current_length = 0
        
        for doc, score in relevant_docs:
            # Get relevant excerpt from document
            excerpt = doc.get_excerpt(query, max_length=600)
            
            if not excerpt:
                continue
            
            # Format document context
            doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}
Content: {excerpt}
---
"""
            
            # Check if adding this document would exceed length limit
            if current_length + len(doc_context) > max_context_length:
                if not referenced_docs:  # Always include at least one document
                    # Truncate the excerpt to fit
                    available_length = max_context_length - current_length
                    truncated_excerpt = excerpt[:available_length - 100] + "..."
                    doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}
Content: {truncated_excerpt}
---
"""
                    context_parts.append(doc_context)
                    referenced_docs.append(doc)
                break
            
            context_parts.append(doc_context)
            referenced_docs.append(doc)
            current_length += len(doc_context)
        
        formatted_context = ''.join(context_parts)
        
        return formatted_context, referenced_docs
    
    @classmethod
    def record_document_usage(cls, documents: List[Document], feedback_positive: bool = True):
        """
        Record that documents were used to answer a question
        Updates analytics and effectiveness scores
        """
        if not documents:
            return
        
        try:
            for doc in documents:
                # Increment reference count
                doc.increment_reference()
                
                # Update effectiveness score based on feedback
                if feedback_positive:
                    # Positive feedback increases effectiveness
                    doc.effectiveness_score = min(doc.effectiveness_score + 0.1, 10.0)
                else:
                    # Negative feedback decreases effectiveness
                    doc.effectiveness_score = max(doc.effectiveness_score - 0.05, 0.0)
                
                doc.save(update_fields=['effectiveness_score'])
                
                logger.info(f"Updated usage for document: {doc.name} (score: {doc.effectiveness_score:.2f})")
        
        except Exception as e:
            logger.error(f"Error recording document usage: {e}")
    
    @classmethod
    def get_knowledge_summary(cls) -> Dict[str, any]:
        """Get summary statistics about the knowledge base"""
        try:
            total_docs = Document.objects.filter(is_active=True).count()
            processed_docs = Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text='').count()
            
            # Get most referenced documents
            top_referenced = Document.objects.filter(
                is_active=True,
                reference_count__gt=0
            ).order_by('-reference_count')[:5]
            
            # Get categories
            categories = Document.objects.filter(
                is_active=True
            ).values_list('category', flat=True).distinct()
            categories = [cat for cat in categories if cat]
            
            # Get total references
            total_references = sum(
                doc.reference_count for doc in Document.objects.filter(is_active=True)
            )
            
            return {
                'total_documents': total_docs,
                'processed_documents': processed_docs,
                'processing_rate': (processed_docs / total_docs * 100) if total_docs > 0 else 0,
                'categories': list(categories),
                'total_references': total_references,
                'top_documents': [
                    {
                        'name': doc.name,
                        'references': doc.reference_count,
                        'effectiveness': doc.effectiveness_score,
                        'last_used': doc.last_referenced.isoformat() if doc.last_referenced else None
                    }
                    for doc in top_referenced
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge summary: {e}")
            return {
                'total_documents': 0,
                'processed_documents': 0,
                'processing_rate': 0,
                'categories': [],
                'total_references': 0,
                'top_documents': []
            }
    
    @classmethod
    def get_documents_by_category(cls, category: str = None) -> List[Document]:
        """Get documents filtered by category"""
        queryset = Document.objects.filter(
            is_active=True,
            extracted_text__isnull=False
        ).exclude(extracted_text='')
        
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        return list(queryset.order_by('-effectiveness_score', '-reference_count'))
    
    @classmethod
    def get_underutilized_documents(cls, reference_threshold: int = 2) -> List[Document]:
        """Get documents that are rarely used but might be valuable"""
        return list(
            Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False,
                reference_count__lt=reference_threshold
            ).exclude(extracted_text='').order_by('reference_count', '-created_at')
        )
    
    @classmethod
    def find_knowledge_gaps(cls, recent_queries: List[str]) -> List[str]:
        """
        Identify potential knowledge gaps based on queries that didn't find good matches
        """
        gaps = []
        
        for query in recent_queries:
            relevant_docs = cls.search_relevant_documents(query, limit=1, min_score=0.5)
            
            if not relevant_docs:
                # No good matches found - potential knowledge gap
                gaps.append(query)
        
        return gaps