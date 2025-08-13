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
    async def search_relevant_documents_async(
        cls, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.1
    ) -> List[Document]:
        """
        Async version with LLM-powered query preprocessing
        """
        if not query.strip():
            return []
        
        try:
            # Use LLM-powered preprocessing for better understanding
            processed_query = await cls._preprocess_query_with_llm(query)
            
            # Get active documents with content
            from asgiref.sync import sync_to_async
            get_docs = sync_to_async(list)
            active_docs = await get_docs(Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text=''))
            
            if not active_docs:
                logger.info("No active documents with extracted text found")
                return []
            
            # Score documents by relevance using both original and processed query
            scored_docs = []
            for doc in active_docs:
                # Try original query first
                score = doc.get_relevance_score(query)
                
                # Always try processed query if it's different
                if processed_query != query.lower().strip():
                    processed_score = doc.get_relevance_score(processed_query)
                    # Use the higher score but mark it as LLM-processed
                    if processed_score > score:
                        score = processed_score * 0.98  # Slight penalty for processed match
                        logger.info(f"LLM preprocessing improved query '{query}' → '{processed_query}' (score: {score:.2f})")
                
                if score >= min_score:
                    scored_docs.append((doc, score))
            
            # Sort by relevance score (descending)
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Log search results for debugging
            if scored_docs:
                logger.info(f"Query '{query}' found {len(scored_docs)} relevant documents")
                for doc, score in scored_docs[:3]:  # Log top 3
                    logger.info(f"  - {doc.name}: {score:.2f}")
            else:
                logger.info(f"Query '{query}' found no relevant documents above threshold {min_score}")
            
            # Return just the documents (not the scores)
            return [doc for doc, score in scored_docs[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    @classmethod
    def search_relevant_documents(
        cls, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.1
    ) -> List[Document]:
        """
        Search for documents relevant to a query with typo tolerance and query preprocessing
        
        Returns:
            List of documents sorted by relevance
        """
        if not query.strip():
            return []
        
        try:
            # Try LLM-powered preprocessing first, fallback to simple preprocessing
            try:
                import asyncio
                processed_query = await cls._preprocess_query_with_llm(query)
            except Exception as e:
                logger.warning(f"LLM preprocessing failed, using fallback: {e}")
                processed_query = cls._preprocess_query(query)
            
            # Get active documents with content
            active_docs = Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text='')
            
            if not active_docs.exists():
                logger.info("No active documents with extracted text found")
                return []
            
            # Score documents by relevance using both original and processed query
            scored_docs = []
            for doc in active_docs:
                # Try original query first
                score = doc.get_relevance_score(query)
                
                # Always try processed query if it's different, not just for low scores
                if processed_query != query.lower().strip():
                    processed_score = doc.get_relevance_score(processed_query)
                    # Use the higher score but mark it as fuzzy matched
                    if processed_score > score:
                        score = processed_score * 0.95  # Slight penalty for fuzzy match
                        logger.info(f"Query '{query}' matched better as '{processed_query}' (score: {score:.2f})")
                
                if score >= min_score:
                    scored_docs.append((doc, score))
            
            # Sort by relevance score (descending)
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # Log search results for debugging
            if scored_docs:
                logger.info(f"Query '{query}' found {len(scored_docs)} relevant documents")
                for doc, score in scored_docs[:3]:  # Log top 3
                    logger.info(f"  - {doc.name}: {score:.2f}")
            else:
                logger.info(f"Query '{query}' found no relevant documents above threshold {min_score}")
            
            # Return just the documents (not the scores)
            return [doc for doc, score in scored_docs[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    @classmethod
    async def _preprocess_query_with_llm(cls, query: str) -> str:
        """
        Use LLM to intelligently preprocess query for typo correction and semantic understanding
        """
        if not query or len(query.strip()) < 3:
            return query
        
        try:
            # Import LLM manager
            from chat.llm_services import LLMManager
            
            # Create a preprocessing prompt for the LLM
            preprocessing_prompt = """You are a query preprocessing assistant for a data analytics company FAQ system. 

Your task: Fix typos and extract key search terms from user queries.

Rules:
1. Fix obvious typos and spelling mistakes
2. Extract the main intent and keywords 
3. Keep business/technical terms accurate
4. Return ONLY the corrected keywords, no explanations
5. If query is about technology/tools, include "technology tools platforms"
6. If query is about data, include "data sources formats"
7. If query is about business/clients, include "business clients companies"
8. If query is about pricing/cost, include "pricing cost quote"
9. If query is about consultation, include "consultation meeting"

Examples:
- "cousultation related info" → "consultation meeting information"
- "businesse and startaps" → "business companies startups enterprises clients"
- "technologies you use" → "technology tools platforms software"
- "data sorces" → "data sources formats databases"
- "pricng info" → "pricing cost quote information"

User query: "{query}"

Corrected keywords:"""

            # Get LLM response for query preprocessing
            messages = [{'role': 'user', 'content': preprocessing_prompt.format(query=query)}]
            
            # Use a lightweight LLM call for preprocessing
            corrected_query, _ = await LLMManager.generate_chat_response(
                user_message=preprocessing_prompt.format(query=query),
                conversation_history=None,
                use_knowledge_base=False,  # Don't use knowledge base for preprocessing
                language='en'
            )
            
            # Clean up the response (remove any extra text)
            corrected_query = corrected_query.strip()
            
            # Remove common LLM response prefixes/suffixes
            prefixes_to_remove = ['corrected keywords:', 'keywords:', 'corrected:', 'result:', 'output:']
            for prefix in prefixes_to_remove:
                if corrected_query.lower().startswith(prefix):
                    corrected_query = corrected_query[len(prefix):].strip()
            
            # Limit length to avoid overly long queries
            if len(corrected_query) > 200:
                corrected_query = corrected_query[:200].strip()
            
            logger.info(f"LLM query preprocessing: '{query}' → '{corrected_query}'")
            
            return corrected_query if corrected_query else query
            
        except Exception as e:
            logger.warning(f"LLM query preprocessing failed: {e}")
            # Fallback to original query
            return query
    
    @classmethod  
    def _preprocess_query(cls, query: str) -> str:
        """
        Fallback preprocessing method (for sync contexts or when LLM fails)
        """
        if not query:
            return query
        
        query_lower = query.lower().strip()
        
        # Simple typo corrections as fallback
        simple_corrections = {
            'cousultation': 'consultation',
            'startaps': 'startups',
            'businesse': 'business',
            'busines': 'business',
            'technologie': 'technology',
            'tecnology': 'technology',
            'suport': 'support',
            'pricng': 'pricing',
        }
        
        corrected_query = query_lower
        for typo, correction in simple_corrections.items():
            if typo in corrected_query:
                corrected_query = corrected_query.replace(typo, correction)
                logger.info(f"Fallback typo correction: '{typo}' → '{correction}'")
        
        return corrected_query
    
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
        
        # Preprocess query for excerpt generation too
        processed_query = cls._preprocess_query(query)
        
        context_parts = []
        referenced_docs = []
        current_length = 0
        
        for doc in relevant_docs:
            # Get relevant excerpt from document using processed query for better matching
            excerpt = doc.get_excerpt(processed_query, max_length=600)
            
            # If processed query doesn't yield good results, try original query
            if not excerpt or len(excerpt) < 50:
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