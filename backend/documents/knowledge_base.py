"""
Knowledge base service for document retrieval and LLM integration
Modern RAG implementation with hybrid search (BM25 + Vector Embeddings)
"""

import logging
from typing import List, Dict, Tuple, Optional
from django.db.models import Q
from django.utils import timezone

from .models import Document
from .hybrid_search import hybrid_search_service, SearchResult

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
        Async version with modern hybrid search (BM25 + Vector Embeddings)
        """
        if not query.strip():
            return []
        
        try:
            # Use hybrid search service
            from asgiref.sync import sync_to_async
            
            # Run hybrid search in thread pool to avoid blocking
            search_func = sync_to_async(hybrid_search_service.hybrid_search)
            search_results = await search_func(query, top_k=limit, min_score=min_score)
            
            if search_results:
                logger.info(f"Hybrid search for '{query}' found {len(search_results)} results:")
                for i, result in enumerate(search_results[:3]):
                    logger.info(f"  {i+1}. {result.document.name} (hybrid: {result.hybrid_score:.3f}, "
                              f"bm25: {result.bm25_score:.3f}, vector: {result.vector_score:.3f})")
                
                # Return documents from search results
                return [result.document for result in search_results]
            else:
                logger.info(f"Hybrid search for '{query}' found no relevant documents")
                return []
            
        except Exception as e:
            logger.error(f"Error in async hybrid search: {e}")
            # Fallback to traditional search
            return await cls._fallback_search_async(query, limit, min_score)
    
    @classmethod
    async def _fallback_search_async(cls, query: str, limit: int, min_score: float) -> List[Document]:
        """Fallback search method if hybrid search fails"""
        try:
            from asgiref.sync import sync_to_async
            get_docs = sync_to_async(list)
            active_docs = await get_docs(Document.objects.filter(
                is_active=True,
                extracted_text__isnull=False
            ).exclude(extracted_text=''))
            
            if not active_docs:
                return []
            
            scored_docs = []
            for doc in active_docs:
                score = doc.get_relevance_score(query)
                if score >= min_score:
                    scored_docs.append((doc, score))
            
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            logger.info(f"Fallback search for '{query}' found {len(scored_docs)} documents")
            
            return [doc for doc, score in scored_docs[:limit]]
            
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []
    
    @classmethod
    def search_relevant_documents(
        cls, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.05  # Lower threshold for broader matching
    ) -> List[Document]:
        """
        Search for documents relevant to a query - basic matching only
        LLM handles all query understanding and semantic processing
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
            
            # Simple relevance scoring - let LLM handle semantic understanding
            scored_docs = []
            for doc in active_docs:
                score = doc.get_relevance_score(query)
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
        
        # Simple typo corrections and semantic expansions as fallback
        simple_corrections = {
            'cousultation': 'consultation',
            'startaps': 'startups',
            'businesse': 'business',
            'busines': 'business',
            'technologie': 'technology',
            'tecnology': 'technology',
            'suport': 'support',
            'pricng': 'pricing',
            'price': 'pricing cost quote',
            'cost': 'pricing cost quote',
            'quote': 'pricing cost quote',
            'models': 'pricing models packages services',
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
        Get knowledge context for LLM using hybrid search results
        
        Returns:
            Tuple of (formatted_context, list_of_referenced_documents)
        """
        try:
            # Use hybrid search for better relevance
            search_results = hybrid_search_service.hybrid_search(
                query, top_k=max_documents, min_score=0.1
            )
            
            if not search_results:
                logger.info(f"No hybrid search results for query: {query}")
                return "", []
            
            context_parts = []
            referenced_docs = []
            current_length = 0
            
            for result in search_results:
                doc = result.document
                chunk_text = result.chunk_text
                
                # Use the specific chunk that was found relevant
                if len(chunk_text) > 800:
                    # Truncate very long chunks but preserve important parts
                    chunk_text = chunk_text[:800] + "..."
                
                # Format document context with hybrid search metadata
                doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}  
Relevance: {result.hybrid_score:.2f} (BM25: {result.bm25_score:.2f}, Vector: {result.vector_score:.2f})
Content: {chunk_text}
---
"""
                
                # Check if adding this document would exceed length limit
                if current_length + len(doc_context) > max_context_length:
                    if not referenced_docs:  # Always include at least one document
                        # Truncate the content to fit
                        available_length = max_context_length - current_length
                        truncated_content = chunk_text[:available_length - 200] + "..."
                        doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}
Relevance: {result.hybrid_score:.2f}
Content: {truncated_content}
---
"""
                        context_parts.append(doc_context)
                        referenced_docs.append(doc)
                    break
                
                context_parts.append(doc_context)
                referenced_docs.append(doc)
                current_length += len(doc_context)
            
            formatted_context = ''.join(context_parts)
            
            logger.info(f"Generated knowledge context with {len(referenced_docs)} documents, "
                       f"total length: {len(formatted_context)} characters")
            
            return formatted_context, referenced_docs
            
        except Exception as e:
            logger.error(f"Error generating knowledge context: {e}")
            # Fallback to traditional method
            return cls._get_knowledge_context_fallback(query, max_documents, max_context_length)
    
    @classmethod
    def _get_knowledge_context_fallback(
        cls, 
        query: str, 
        max_documents: int,
        max_context_length: int
    ) -> Tuple[str, List[Document]]:
        """Fallback knowledge context generation"""
        try:
            relevant_docs = cls.search_relevant_documents(query, limit=max_documents)
            
            if not relevant_docs:
                return "", []
            
            context_parts = []
            referenced_docs = []
            current_length = 0
            
            for doc in relevant_docs:
                excerpt = doc.get_excerpt(query, max_length=600)
                if not excerpt:
                    continue
                
                doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}
Content: {excerpt}
---
"""
                
                if current_length + len(doc_context) > max_context_length:
                    if not referenced_docs:
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
            
            return ''.join(context_parts), referenced_docs
            
        except Exception as e:
            logger.error(f"Error in fallback context generation: {e}")
            return "", []
    
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