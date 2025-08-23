import json
import asyncio
from typing import Dict, Any, Optional, List
from django.http import JsonResponse
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta
from asgiref.sync import async_to_sync
from chat.llm_services import LLMManager
from core.exceptions.chat_exceptions import (
    LLMProviderException, ConversationException, ValidationException
)
from chat.models import APIConfiguration, AdminPrompt, Conversation, Message, ConversationSummary
from documents.models import Document
from documents.hybrid_search import hybrid_search_service
from .conversation_service import ConversationService
from .analytics_service import AnalyticsService


class LLMAdminService:
    """Service for LLM admin chat functionality"""
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available LLM providers"""
        return [
            {'value': 'openai', 'label': 'OpenAI GPT'},
            {'value': 'gemini', 'label': 'Gemini'},
            {'value': 'claude', 'label': 'Claude'}
        ]
    
    @classmethod
    def get_admin_context(cls, request) -> Dict[str, Any]:
        """Get context data for admin LLM chat interface"""
        # Get conversation statistics
        conversation_count = ConversationService.get_conversation_count(request)
        
        # Get document statistics
        total_docs = Document.objects.filter(is_active=True).count()
        processed_docs = Document.objects.filter(
            is_active=True, 
            extracted_text__isnull=False
        ).exclude(extracted_text='').count()
        
        # Get API configuration status
        api_configs = APIConfiguration.objects.filter(is_active=True).count()
        
        return {
            'title': 'LLM Chat Interface',
            'available_providers': [provider['value'] for provider in cls.get_available_providers()],
            'providers': cls.get_available_providers(),
            'total_conversations': conversation_count,
            'total_documents': total_docs,
            'processed_documents': processed_docs,
            'api_configurations': api_configs,
            'user': request.user
        }
    
    @classmethod
    async def process_chat_message(cls, request, message: str, provider: str, 
                           use_knowledge: bool, conversation_id: str) -> JsonResponse:
        """Process a chat message and return LLM response"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Processing chat message: message='{message}', provider={provider}, use_knowledge={use_knowledge}")
        
        try:
            # Validate inputs
            logger.info("Step 1: Validating inputs")
            if not message or not message.strip():
                raise ValidationException('message', 'Message cannot be empty')
            
            logger.info("Step 2: Input validation passed")
            
            if not conversation_id:
                raise ConversationException('', 'Conversation ID is required')
            
            logger.info("Step 3: Saving message to session")
            # Save user message to session
            ConversationService.save_message_to_session(
                request, conversation_id, 'user', message
            )
            logger.info("Step 4: Message saved to session successfully")
            
            logger.info("Step 5: Getting all data context (async-safe)")
            # Get all data context in sync thread to avoid async context issues
            from asgiref.sync import sync_to_async
            
            def get_all_data_context():
                # Get enhanced context for admin queries with conversation data  
                enhanced_context = cls._get_admin_data_context_sync(message)
                
                # Get conversation and message data based on admin query
                conversation_data = cls._query_conversation_data(message)
                message_data = cls._query_message_data(message)
                summary_data = cls._query_summary_data(message)
                
                # Always include basic feedback stats for any admin query
                if 'feedback_analysis' not in message_data:
                    feedback_stats = Message.objects.filter(
                        feedback__isnull=False
                    ).aggregate(
                        total_feedback=Count('id'),
                        positive_feedback=Count('id', filter=Q(feedback='positive')),
                        negative_feedback=Count('id', filter=Q(feedback='negative'))
                    )
                    
                    if feedback_stats['total_feedback'] > 0:
                        message_data['feedback_analysis'] = {
                            'total_feedback_messages': feedback_stats['total_feedback'],
                            'positive_count': feedback_stats['positive_feedback'],
                            'negative_count': feedback_stats['negative_feedback'],
                            'positive_rate': round(
                                (feedback_stats['positive_feedback'] / max(feedback_stats['total_feedback'], 1)) * 100, 1
                            ),
                            'negative_rate': round(
                                (feedback_stats['negative_feedback'] / max(feedback_stats['total_feedback'], 1)) * 100, 1
                            )
                        }
                
                return enhanced_context, conversation_data, message_data, summary_data
            
            enhanced_context, conversation_data, message_data, summary_data = await sync_to_async(get_all_data_context)()
            logger.info("Step 6: All data context retrieved successfully")
            
            # Combine all context data
            enhanced_context.update({
                'conversations': conversation_data,
                'messages': message_data, 
                'summaries': summary_data
            })
            
            # Configure knowledge base usage with advanced RAG system
            knowledge_context = None
            if use_knowledge:
                logger.info("Step 7: Knowledge Base enabled - searching documents")
                # Use advanced RAG system for document search
                knowledge_context = await cls._search_with_advanced_rag(message)
                logger.info(f"Step 8: Knowledge search completed - found {knowledge_context.get('total_results', 0)} documents")
            
            # Build enhanced message with context for LLM
            enhanced_message = cls._build_enhanced_message(message, enhanced_context, knowledge_context)
            logger.info(f"Step 9: Enhanced message length: {len(enhanced_message)} characters")
            if knowledge_context:
                logger.info(f"Knowledge Base content included: {'KNOWLEDGE BASE SEARCH RESULTS' in enhanced_message}")
            
            # Try real LLM service, fallback to test response if it fails
            try:
                # Use asyncio.run to create a new event loop in a thread-safe way
                import asyncio
                import threading
                from concurrent.futures import ThreadPoolExecutor
                
                def run_async_llm():
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # Use automatic provider selection if 'auto' is specified
                        actual_provider = None if provider == 'auto' else provider
                        
                        return loop.run_until_complete(
                            LLMManager.generate_chat_response(
                                user_message=enhanced_message,
                                provider=actual_provider,
                                use_knowledge_base=use_knowledge,
                                conversation_id=conversation_id
                            )
                        )
                    finally:
                        loop.close()
                
                # Run in thread pool to avoid Django async context issues
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_async_llm)
                    response, metadata = future.result(timeout=30)  # 30 second timeout
                    
                # Mark as real LLM response
                metadata['admin_test'] = False
                metadata['real_llm_used'] = True
                
            except Exception as llm_error:
                # Fallback to test response if LLM fails
                response = cls._generate_test_response(message, provider, use_knowledge, knowledge_context, enhanced_context)
                metadata = {
                    'admin_test': True,
                    'provider_used': provider,
                    'tokens_used': len(response.split()) * 1.3,
                    'knowledge_base_used': use_knowledge,
                    'response_type': 'test_mode_fallback',
                    'llm_error': str(llm_error),
                    'data_context_included': True
                }
            
            # Save bot response to session
            ConversationService.save_message_to_session(
                request, conversation_id, 'assistant', response, metadata
            )
            
            return JsonResponse({
                'success': True,
                'response': response,
                'metadata': metadata,
                'conversation_id': conversation_id
            })
            
        except ValidationException as e:
            error_response = f"Validation error: {e.message}"
            return JsonResponse({
                'success': False,
                'error': error_response,
                'error_code': e.error_code,
                'conversation_id': conversation_id
            }, status=400)
            
        except LLMProviderException as e:
            error_response = f"LLM Provider error: {e.message}"
            
            # Save error response to session
            ConversationService.save_message_to_session(
                request, conversation_id, 'assistant', error_response, 
                {'error': True, 'error_type': 'LLMProviderException', 'provider': e.provider}
            )
            
            return JsonResponse({
                'success': False,
                'error': error_response,
                'error_code': e.error_code,
                'conversation_id': conversation_id
            }, status=500)
            
        except ConversationException as e:
            return JsonResponse({
                'success': False,
                'error': e.message,
                'error_code': e.error_code,
                'conversation_id': conversation_id
            }, status=400)
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Unexpected error in chat processing: {e}")
            logger.error(f"Full traceback: {error_traceback}")
            
            error_response = f"Unexpected error: {str(e)}"
            
            # Save error response to session
            ConversationService.save_message_to_session(
                request, conversation_id, 'assistant', error_response, 
                {'error': True, 'error_type': type(e).__name__}
            )
            
            return JsonResponse({
                'success': False,
                'error': error_response,
                'conversation_id': conversation_id
            }, status=500)
    
    @staticmethod
    def _build_admin_system_prompt(analytics_context: Dict[str, Any], 
                                 knowledge_context: Optional[Dict] = None) -> str:
        """Build system prompt for admin chat with enhanced context"""
        base_prompt = (
            "You are an AI assistant for a chatbot administration system. "
            "You help administrators understand customer insights, manage conversations, "
            "and analyze chatbot performance. Provide helpful, professional responses "
            "with specific data when available."
        )
        
        # Add analytics context if available
        if analytics_context:
            context_parts = []
            
            if 'satisfaction' in analytics_context:
                sat = analytics_context['satisfaction']
                context_parts.append(
                    f"Customer Satisfaction: {sat['average_score']}/5.0 average, "
                    f"{sat['satisfaction_rate']}% high satisfaction rate from "
                    f"{sat['total_conversations_rated']} rated conversations."
                )
            
            if 'volume' in analytics_context:
                vol = analytics_context['volume']
                context_parts.append(
                    f"Conversation Volume: {vol['weekly_conversations']} conversations this week, "
                    f"average {vol['avg_messages_per_conversation']} messages per conversation."
                )
            
            if 'response_time' in analytics_context:
                resp = analytics_context['response_time']
                context_parts.append(
                    f"Response Performance: {resp['average_response_seconds']}s average response time, "
                    f"rated as {resp['response_quality']}."
                )
            
            if context_parts:
                base_prompt += "\n\nCurrent System Data:\n" + "\n".join(context_parts)
        
        # Add knowledge base context if available
        if knowledge_context and knowledge_context.get('documents'):
            docs = knowledge_context['documents']
            base_prompt += (
                f"\n\nAvailable Documentation ({len(docs)} documents): "
                + ", ".join([doc['name'] for doc in docs])
            )
        
        return base_prompt
    
    @classmethod
    def _get_admin_data_context_sync(cls, query: str) -> Dict[str, Any]:
        """Get comprehensive admin data context based on query"""
        # Start with basic analytics context
        context = AnalyticsService.get_customer_analytics_context(query)
        
        # Always include basic system status for admin awareness
        context['system_status'] = {
            'total_conversations': Conversation.objects.count(),
            'active_conversations': Conversation.objects.filter(is_active=True).count(),
            'total_messages': Message.objects.count(),
            'recent_summaries': ConversationSummary.objects.count(),
            'total_users': Conversation.objects.values('user').distinct().count()
        }
        
        # Add analysis source information
        analysis_sources = Message.objects.filter(
            message_analysis__isnull=False
        ).exclude(message_analysis={})
        
        if analysis_sources.exists():
            # Get analysis source statistics
            context['analysis_sources'] = {
                'messages_with_analysis': analysis_sources.count(),
                'langextract_analyzed': Message.objects.filter(
                    message_analysis__analysis_source__icontains='LangExtract'
                ).count(),
                'gemini_analyzed': Message.objects.filter(
                    message_analysis__llm_model__icontains='gemini'
                ).count(),
                'total_analyzed_messages': analysis_sources.count()
            }
            
            # Get sample analysis sources
            sample_sources = list(analysis_sources.values_list(
                'message_analysis__analysis_source', flat=True
            ).distinct()[:5])
            context['analysis_sources']['sample_sources'] = sample_sources
        
        return context
    
    @classmethod
    def _query_conversation_data(cls, query: str) -> Dict[str, Any]:
        """Query conversation data based on admin question"""
        query_lower = query.lower()
        data = {}
        
        # Recent conversations
        if any(term in query_lower for term in ['recent', 'latest', 'new', 'today']):
            today = timezone.now().date()
            recent_convs = Conversation.objects.filter(
                created_at__date=today
            ).select_related('user').order_by('-created_at')[:10]
            
            data['recent_conversations'] = [{
                'id': conv.id,
                'title': conv.get_title(),
                'user': conv.user.username,
                'message_count': conv.total_messages,
                'satisfaction': conv.satisfaction_score,
                'created_at': conv.created_at.strftime('%H:%M'),
                'has_analysis': bool(conv.langextract_analysis)
            } for conv in recent_convs]
        
        # Problem conversations
        if any(term in query_lower for term in ['problem', 'issue', 'complaint', 'negative']):
            problem_convs = Conversation.objects.filter(
                Q(satisfaction_score__lt=3.0) | 
                Q(langextract_analysis__issues_raised__isnull=False)
            ).select_related('user').order_by('-created_at')[:10]
            
            data['problem_conversations'] = [{
                'id': conv.id,
                'title': conv.get_title(),
                'user': conv.user.username,
                'satisfaction': conv.satisfaction_score,
                'issues': len(conv.langextract_analysis.get('issues_raised', [])) if conv.langextract_analysis else 0,
                'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M')
            } for conv in problem_convs]
        
        # High satisfaction conversations
        if any(term in query_lower for term in ['good', 'positive', 'satisfied', 'happy']):
            good_convs = Conversation.objects.filter(
                satisfaction_score__gte=4.0
            ).select_related('user').order_by('-created_at')[:10]
            
            data['positive_conversations'] = [{
                'id': conv.id,
                'title': conv.get_title(),
                'user': conv.user.username,
                'satisfaction': conv.satisfaction_score,
                'created_at': conv.created_at.strftime('%Y-%m-%d %H:%M')
            } for conv in good_convs]
        
        return data
    
    @classmethod
    def _query_message_data(cls, query: str) -> Dict[str, Any]:
        """Query message data based on admin question"""
        query_lower = query.lower()
        data = {}
        
        # Recent messages
        if any(term in query_lower for term in ['messages', 'recent', 'latest']):
            recent_messages = Message.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).select_related('conversation', 'conversation__user').order_by('-timestamp')[:20]
            
            data['recent_messages'] = [{
                'content_preview': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                'sender': msg.sender_type,
                'conversation_id': msg.conversation.id,
                'user': msg.conversation.user.username,
                'feedback': msg.feedback,
                'timestamp': msg.timestamp.strftime('%H:%M'),
                'has_analysis': bool(msg.message_analysis)
            } for msg in recent_messages]
        
        # Feedback analysis - expanded triggers
        if any(term in query_lower for term in [
            'feedback', 'rating', 'thumbs', 'positive', 'negative', 'rate', 
            'messages positive', 'messages negative', 'message feedback'
        ]):
            feedback_stats = Message.objects.filter(
                feedback__isnull=False
            ).aggregate(
                total_feedback=Count('id'),
                positive_feedback=Count('id', filter=Q(feedback='positive')),
                negative_feedback=Count('id', filter=Q(feedback='negative'))
            )
            
            data['feedback_analysis'] = {
                'total_feedback_messages': feedback_stats['total_feedback'],
                'positive_count': feedback_stats['positive_feedback'],
                'negative_count': feedback_stats['negative_feedback'],
                'positive_rate': round(
                    (feedback_stats['positive_feedback'] / max(feedback_stats['total_feedback'], 1)) * 100, 1
                ),
                'negative_rate': round(
                    (feedback_stats['negative_feedback'] / max(feedback_stats['total_feedback'], 1)) * 100, 1
                )
            }
        
        return data
    
    @classmethod
    def _query_summary_data(cls, query: str) -> Dict[str, Any]:
        """Query conversation summary data based on admin question"""
        query_lower = query.lower()
        data = {}
        
        # Recent summaries
        if any(term in query_lower for term in ['summary', 'summaries', 'analysis', 'insights']):
            recent_summaries = ConversationSummary.objects.order_by('-generated_at')[:10]
            
            data['recent_summaries'] = [{
                'analysis_period': summary.analysis_period,
                'messages_analyzed': summary.messages_analyzed_count,
                'critical_issues': summary.critical_issues_found,
                'preview': summary.get_preview(150),
                'generated_at': summary.generated_at.strftime('%Y-%m-%d %H:%M'),
                'llm_model': summary.llm_model_used
            } for summary in recent_summaries]
        
        return data
    
    @classmethod
    async def _search_with_advanced_rag(cls, query: str) -> Dict[str, Any]:
        """Search knowledge base using hybrid search service (BM25 + Vector embeddings)"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Use sync_to_async for better Django integration
            from asgiref.sync import sync_to_async
            
            # Ensure indexes are built (hybrid search service handles this automatically)
            search_results = await sync_to_async(hybrid_search_service.hybrid_search)(
                query=query,
                top_k=5,
                bm25_weight=0.4,  # Keyword matching
                vector_weight=0.6,  # Semantic similarity  
                min_score=0.05
            )
            
            if not search_results:
                return {
                    'documents': [],
                    'total_results': 0,
                    'search_method': 'hybrid_search',
                    'error': 'No relevant documents found',
                    'query': query
                }
            
            # Format results for LLM consumption
            documents = []
            for result in search_results:
                # Track document usage (async-safe)
                try:
                    from asgiref.sync import sync_to_async
                    await sync_to_async(result.document.increment_reference)()
                except Exception as e:
                    logger.warning(f"Failed to increment reference count: {e}")
                
                documents.append({
                    'name': result.document.name,
                    'category': result.document.category or 'General',
                    'content': result.chunk_text,
                    'bm25_score': round(result.bm25_score, 3),
                    'vector_score': round(result.vector_score, 3),
                    'hybrid_score': round(result.hybrid_score, 3),
                    'chunk_index': result.chunk_index,
                    'summary': result.document.ai_summary[:200] if result.document.ai_summary else '',
                    'reference_count': result.document.reference_count
                })
            
            # Get search analytics
            analytics = await sync_to_async(hybrid_search_service.get_search_analytics)()
            
            return {
                'documents': documents,
                'total_results': len(documents),
                'search_method': 'hybrid_search',
                'hybrid_search_used': True,
                'vector_search_available': analytics.get('vector_index_size', 0) > 0,
                'bm25_search_available': analytics.get('bm25_index_size', 0) > 0,
                'total_chunks_indexed': analytics.get('total_chunks', 0),
                'documents_indexed': analytics.get('documents_indexed', 0),
                'embedding_model': analytics.get('embedding_model', 'unknown'),
                'query': query
            }
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            
            # Fallback to basic document search if hybrid search fails
            return {
                'documents': [],
                'total_results': 0,
                'search_method': 'hybrid_search_failed',
                'error': str(e),
                'query': query
            }
    
    @classmethod
    def _build_enhanced_message(cls, original_message: str, data_context: Dict[str, Any], knowledge_context: Dict[str, Any] = None) -> str:
        """Build enhanced message with relevant database context for LLM"""
        enhanced_msg = f"You are an admin assistant for a Django-based chatbot system. "
        enhanced_msg += f"You have access to the following database models and can provide insights about:\n\n"
        
        enhanced_msg += f"AVAILABLE DATA SOURCES:\n"
        enhanced_msg += f"1. Conversations: User conversations with satisfaction scores, LangExtract analysis\n"
        enhanced_msg += f"2. Messages: Individual messages with feedback, timestamps, analysis data\n"
        enhanced_msg += f"3. ConversationSummary: LLM-generated analysis summaries and insights\n"
        enhanced_msg += f"4. Documents: Knowledge base documents with usage statistics\n"
        enhanced_msg += f"5. UserSessions: User activity and session data\n"
        enhanced_msg += f"6. Message Analysis: LangExtract analysis including sentiment, issues, importance\n\n"
        
        enhanced_msg += f"ANALYSIS CAPABILITIES:\n"
        enhanced_msg += f"- Message analysis source detection (LangExtract, manual, etc.)\n"
        enhanced_msg += f"- Sentiment analysis and satisfaction tracking\n"
        enhanced_msg += f"- Issue categorization and importance levels\n"
        enhanced_msg += f"- Customer feedback (thumbs up/down) analysis\n"
        enhanced_msg += f"- Conversation volume and performance metrics\n"
        enhanced_msg += f"- User behavior and engagement patterns\n\n"
        
        enhanced_msg += f"Question: {original_message}\n\n"
        
        # Add system status if available
        if 'system_status' in data_context:
            status = data_context['system_status']
            enhanced_msg += "SYSTEM STATUS:\n"
            enhanced_msg += f"- Total Conversations: {status['total_conversations']}\n"
            enhanced_msg += f"- Active Conversations: {status['active_conversations']}\n"
            enhanced_msg += f"- Total Messages: {status['total_messages']}\n"
            enhanced_msg += f"- Total Users: {status['total_users']}\n"
            enhanced_msg += f"- Analysis Summaries Available: {status['recent_summaries']}\n\n"
        
        # Add satisfaction context if available
        if 'satisfaction' in data_context:
            sat = data_context['satisfaction']
            enhanced_msg += "CUSTOMER SATISFACTION DATA:\n"
            enhanced_msg += f"- Average Satisfaction Score: {sat['average_score']}/5.0\n"
            enhanced_msg += f"- High Satisfaction Rate: {sat['satisfaction_rate']}%\n"
            enhanced_msg += f"- Total Rated Conversations: {sat['total_conversations_rated']}\n"
            enhanced_msg += f"- High Satisfaction Count: {sat.get('high_satisfaction_count', 0)}\n"
            enhanced_msg += f"- Low Satisfaction Count: {sat.get('low_satisfaction_count', 0)}\n\n"
        
        # Add conversation data if available
        if 'conversations' in data_context and data_context['conversations']:
            conv_data = data_context['conversations']
            enhanced_msg += "CONVERSATION DATA:\n"
            
            if 'recent_conversations' in conv_data:
                enhanced_msg += f"Recent Conversations ({len(conv_data['recent_conversations'])}): "
                for conv in conv_data['recent_conversations'][:3]:
                    enhanced_msg += f"{conv['title'][:30]}...(Score: {conv.get('satisfaction', 'N/A')}), "
                enhanced_msg += "\n"
            
            if 'problem_conversations' in conv_data:
                enhanced_msg += f"Problem Conversations ({len(conv_data['problem_conversations'])}): "
                for conv in conv_data['problem_conversations'][:3]:
                    enhanced_msg += f"{conv['title'][:30]}...(Score: {conv['satisfaction']}), "
                enhanced_msg += "\n"
        
        # Add feedback analysis if available
        if 'messages' in data_context and 'feedback_analysis' in data_context['messages']:
            fb = data_context['messages']['feedback_analysis']
            enhanced_msg += "MESSAGE FEEDBACK DATA:\n"
            enhanced_msg += f"- Total Feedback Messages: {fb['total_feedback_messages']}\n"
            enhanced_msg += f"- Positive Feedback: {fb['positive_count']} ({fb['positive_rate']}%)\n"
            enhanced_msg += f"- Negative Feedback: {fb['negative_count']} ({fb.get('negative_rate', 0)}%)\n\n"
        
        # Add volume data if available
        if 'volume' in data_context:
            vol = data_context['volume']
            enhanced_msg += "CONVERSATION VOLUME DATA:\n"
            enhanced_msg += f"- Weekly Conversations: {vol['weekly_conversations']}\n"
            enhanced_msg += f"- Average Messages per Conversation: {vol['avg_messages_per_conversation']}\n\n"
        
        # Add analysis source data if available
        if 'analysis_sources' in data_context:
            sources = data_context['analysis_sources']
            enhanced_msg += "MESSAGE ANALYSIS SOURCES:\n"
            enhanced_msg += f"- Total Messages with Analysis: {sources['messages_with_analysis']}\n"
            enhanced_msg += f"- LangExtract Analyzed: {sources['langextract_analyzed']}\n"
            enhanced_msg += f"- Gemini Model Analyzed: {sources['gemini_analyzed']}\n"
            if sources.get('sample_sources'):
                enhanced_msg += f"- Analysis Sources: {', '.join(sources['sample_sources'])}\n"
            enhanced_msg += "\n"
        
        # Add knowledge base context if available
        if knowledge_context and knowledge_context.get('documents'):
            enhanced_msg += "KNOWLEDGE BASE SEARCH RESULTS:\n"
            
            search_method = knowledge_context.get('search_method', 'unknown')
            total_results = knowledge_context.get('total_results', 0)
            enhanced_msg += f"- Search Method: {search_method.upper()}\n"
            enhanced_msg += f"- Results Found: {total_results}\n"
            
            if knowledge_context.get('hybrid_search_used'):
                enhanced_msg += f"- Vector Search: {'Available' if knowledge_context.get('vector_search_available') else 'Not Available'}\n"
                enhanced_msg += f"- BM25 Search: {'Available' if knowledge_context.get('bm25_search_available') else 'Not Available'}\n"
            
            enhanced_msg += "\nRELEVANT DOCUMENT CONTENT:\n"
            
            for i, doc in enumerate(knowledge_context['documents'], 1):
                enhanced_msg += f"\nDocument {i}: {doc['name']}\n"
                enhanced_msg += f"Category: {doc['category']}\n"
                
                if knowledge_context.get('hybrid_search_used'):
                    enhanced_msg += f"Relevance Scores - BM25: {doc['bm25_score']}, Vector: {doc['vector_score']}, Hybrid: {doc['hybrid_score']}\n"
                
                enhanced_msg += f"Content:\n{doc['content']}\n"
                
                if doc.get('summary'):
                    enhanced_msg += f"Summary: {doc['summary']}\n"
                
                enhanced_msg += "---\n"
            
            enhanced_msg += "\nUSE THE ABOVE KNOWLEDGE BASE CONTENT to answer the user's question. "
            enhanced_msg += "Reference specific information from the documents when relevant. "
            enhanced_msg += "If the knowledge base contains the answer, provide it directly from the document content.\n\n"
        
        enhanced_msg += "Based on the system architecture and available data above, provide a specific answer. "
        
        if knowledge_context and knowledge_context.get('documents'):
            enhanced_msg += "PRIORITIZE information from the Knowledge Base documents when answering the question. "
        else:
            enhanced_msg += "If you need to access specific data that wasn't provided, explain what data you would query "
            enhanced_msg += "from which database models (Conversations, Messages, ConversationSummary, etc.) to answer the question."
        
        return enhanced_msg
    
    @classmethod
    def _build_enhanced_admin_prompt(cls, data_context: Dict[str, Any], 
                                   knowledge_context: Optional[Dict] = None) -> str:
        """Build comprehensive admin system prompt with data context"""
        base_prompt = (
            "You are an AI assistant for a chatbot administration system. "
            "You help administrators analyze customer conversations, understand system performance, "
            "and extract insights from accumulated data. You have access to real conversation data, "
            "message analysis, and system metrics. Provide specific, data-driven responses "
            "with concrete examples and actionable insights."
        )
        
        # Add system status context
        if 'system_status' in data_context:
            status = data_context['system_status']
            base_prompt += f"\n\nSYSTEM STATUS:\n"
            base_prompt += f"- Total Conversations: {status['total_conversations']}\n"
            base_prompt += f"- Active Conversations: {status['active_conversations']}\n"
            base_prompt += f"- Total Messages: {status['total_messages']}\n"
            base_prompt += f"- Unique Users: {status['total_users']}\n"
            base_prompt += f"- Available Summaries: {status['recent_summaries']}"
        
        # Add conversation data context
        if 'conversations' in data_context and data_context['conversations']:
            conv_data = data_context['conversations']
            base_prompt += "\n\nCONVERSATION DATA:\n"
            
            if 'recent_conversations' in conv_data:
                base_prompt += f"Recent Conversations ({len(conv_data['recent_conversations'])}): "
                for conv in conv_data['recent_conversations'][:3]:
                    base_prompt += f"[{conv['title'][:30]}... - {conv['message_count']} messages], "
            
            if 'problem_conversations' in conv_data:
                base_prompt += f"\nProblem Conversations ({len(conv_data['problem_conversations'])}): "
                for conv in conv_data['problem_conversations'][:3]:
                    base_prompt += f"[{conv['title'][:30]}... - Score: {conv['satisfaction']}], "
        
        # Add message analysis context
        if 'messages' in data_context and data_context['messages']:
            msg_data = data_context['messages']
            base_prompt += "\n\nMESSAGE ANALYSIS:\n"
            
            if 'feedback_analysis' in msg_data:
                fb = msg_data['feedback_analysis']
                base_prompt += f"Feedback: {fb['total_feedback_messages']} total, "
                base_prompt += f"{fb['positive_rate']}% positive ({fb['positive_count']} positive, {fb['negative_count']} negative)\n"
            
            if 'recent_messages' in msg_data:
                base_prompt += f"Recent Messages: {len(msg_data['recent_messages'])} in last 24h\n"
        
        # Add summary insights context
        if 'summaries' in data_context and data_context['summaries']:
            summary_data = data_context['summaries']
            if 'recent_summaries' in summary_data:
                base_prompt += "\n\nRECENT ANALYSIS SUMMARIES:\n"
                for summary in summary_data['recent_summaries'][:3]:
                    base_prompt += f"- {summary['analysis_period']}: {summary['messages_analyzed']} messages analyzed, "
                    base_prompt += f"{summary['critical_issues']} critical issues found\n"
        
        # Add knowledge base context
        if knowledge_context and knowledge_context.get('documents'):
            docs = knowledge_context['documents']
            base_prompt += f"\n\nKNOWLEDGE BASE: {len(docs)} documents available\n"
        
        base_prompt += "\n\nWhen answering questions, reference specific data points and provide actionable insights based on the actual system data above."
        
        return base_prompt
    
    @classmethod
    def _generate_test_response(cls, message: str, provider: str, use_knowledge: bool, 
                              knowledge_context: Optional[Dict] = None, data_context: Optional[Dict] = None) -> str:
        """Generate a realistic test response for admin chat"""
        
        # Provider-specific response styles
        if provider.lower() == 'gemini':
            base_response = f"Hello! I'm Gemini, Google's AI assistant. I received your message: '{message}'"
        elif provider.lower() == 'claude':
            base_response = f"Hi there! I'm Claude, Anthropic's AI assistant. Regarding your message '{message}'"
        else:  # OpenAI/GPT
            base_response = f"Hello! I'm ChatGPT, OpenAI's AI assistant. I understand you said: '{message}'"
        
        # Add knowledge base context if enabled
        if use_knowledge and knowledge_context and knowledge_context.get('documents'):
            docs = knowledge_context['documents']
            base_response += f"\n\nKnowledge Base: I can access {len(docs)} documents: "
            base_response += ", ".join([doc['name'] for doc in docs[:3]])
            if len(docs) > 3:
                base_response += f" and {len(docs) - 3} more."
        
        # Add admin-specific functionality hints
        base_response += "\n\nAs your admin assistant, I can help you with:"
        base_response += "\n- Customer analytics and conversation metrics"
        base_response += "\n- System performance and usage statistics" 
        base_response += "\n- Knowledge base management and document search"
        base_response += "\n- Testing chatbot responses and configurations"
        
        # Add data-driven insights if available
        if data_context:
            if 'system_status' in data_context:
                status = data_context['system_status']
                base_response += f"\n\nCurrent System Status:"
                base_response += f"\n- Total Conversations: {status.get('total_conversations', 0)}"
                base_response += f"\n- Active Users: {status.get('total_users', 0)}"
                base_response += f"\n- Total Messages: {status.get('total_messages', 0)}"
            
            if 'conversations' in data_context:
                conv_data = data_context['conversations']
                if 'recent_conversations' in conv_data:
                    base_response += f"\n\nRecent Activity: {len(conv_data['recent_conversations'])} conversations today"
                if 'problem_conversations' in conv_data:
                    base_response += f"\nProblem Cases: {len(conv_data['problem_conversations'])} conversations need attention"
            
            if 'messages' in data_context and 'feedback_analysis' in data_context['messages']:
                fb = data_context['messages']['feedback_analysis']
                base_response += f"\n\nFeedback Summary: {fb.get('positive_rate', 0)}% positive from {fb.get('total_feedback_messages', 0)} rated messages"
        
        # Add test mode notice
        base_response += "\n\nThis is a test response with real data context. To enable full LLM functionality, configure your API keys in the Django admin panel."
        
        return base_response
    
    @classmethod
    def get_conversation_history_response(cls, request, conversation_id: str) -> JsonResponse:
        """Get conversation history for a specific conversation"""
        try:
            if not conversation_id:
                raise ValidationException('conversation_id', 'Conversation ID is required')
            
            history = ConversationService.get_conversation_history(request, conversation_id)
            conversations = ConversationService.get_all_conversations(request)
            
            # Transform history format: change 'role' to 'type' for frontend compatibility
            transformed_history = []
            for item in history:
                transformed_item = {
                    'type': item.get('role', 'user'),  # Convert 'role' to 'type'
                    'content': item.get('content', ''),
                    'timestamp': item.get('timestamp', ''),
                    'metadata': item.get('metadata', {})
                }
                transformed_history.append(transformed_item)
            
            return JsonResponse({
                'success': True,
                'history': transformed_history,
                'conversations': conversations,
                'current_conversation_id': conversation_id
            })
            
        except ValidationException as e:
            return JsonResponse({
                'success': False,
                'error': e.message,
                'error_code': e.error_code
            }, status=400)
            
        except ValueError as e:
            # Handle conversation not found errors from ConversationService
            return JsonResponse({
                'success': False,
                'error': str(e),
                'error_code': 'CONVERSATION_NOT_FOUND'
            }, status=404)
            
        except ConversationException as e:
            return JsonResponse({
                'success': False,
                'error': e.message,
                'error_code': e.error_code
            }, status=404)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to load conversation: {str(e)}'
            }, status=500)
    
    @classmethod
    def handle_conversation_action(cls, request, action: str, data: Dict[str, Any]) -> JsonResponse:
        """Handle conversation management actions (create, delete, clear)"""
        try:
            if action == 'create':
                conversation_id = ConversationService.create_new_conversation(request)
                conversations = ConversationService.get_all_conversations(request)
                
                # Find the newly created conversation
                new_conversation = next((c for c in conversations if c['id'] == conversation_id), None)
                
                return JsonResponse({
                    'success': True,
                    'conversation_id': conversation_id,
                    'conversation': new_conversation,
                    'conversations': conversations
                })
            
            elif action == 'clear_all':
                success = ConversationService.clear_all_conversations(request)
                if success:
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Failed to clear conversations'})
            
            elif action == 'delete':
                conversation_id = data.get('conversation_id')
                if not conversation_id:
                    return JsonResponse({'error': 'Conversation ID is required'}, status=400)
                
                success = ConversationService.delete_conversation(request, conversation_id)
                if success:
                    return JsonResponse({'success': True})
                else:
                    return JsonResponse({'success': False, 'error': 'Failed to delete conversation'})
            
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to process request: {str(e)}'
            }, status=500)
