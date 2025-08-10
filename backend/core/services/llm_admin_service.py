import json
from typing import Dict, Any, Optional
from django.http import JsonResponse
from asgiref.sync import async_to_sync
from chat.llm_services import LLMManager
from core.exceptions.chat_exceptions import (
    LLMProviderException, ConversationException, ValidationException
)
from chat.models import APIConfiguration, AdminPrompt
from documents.models import Document
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
    def process_chat_message(cls, request, message: str, provider: str, 
                           use_knowledge: bool, conversation_id: str) -> JsonResponse:
        """Process a chat message and return LLM response"""
        try:
            # Validate inputs
            if not message or not message.strip():
                raise ValidationException('message', 'Message cannot be empty')
            
            if not conversation_id:
                raise ConversationException('', 'Conversation ID is required')
            
            # Save user message to session
            ConversationService.save_message_to_session(
                request, conversation_id, 'user', message
            )
            
            # Get enhanced context for admin queries
            enhanced_context = AnalyticsService.get_customer_analytics_context(message)
            
            # Configure knowledge base usage
            knowledge_context = None
            if use_knowledge:
                # This would typically search documents
                # For now, we'll simulate document context
                knowledge_docs = Document.objects.filter(is_active=True)[:3]
                knowledge_context = {
                    'documents': [{
                        'name': doc.name,
                        'content_excerpt': doc.extracted_text[:200] if doc.extracted_text else '',
                        'category': doc.category
                    } for doc in knowledge_docs]
                }
            
            # For now, provide a test response until we fix the async context issue
            # TODO: Fix async context issue with LLM service
            response = cls._generate_test_response(message, provider, use_knowledge, knowledge_context)
            metadata = {
                'admin_test': True,
                'provider_used': provider,
                'tokens_used': len(response.split()) * 1.3,  # Approximate token count
                'knowledge_base_used': use_knowledge,
                'response_type': 'test_mode'
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
    def _generate_test_response(cls, message: str, provider: str, use_knowledge: bool, 
                              knowledge_context: Optional[Dict] = None) -> str:
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
            base_response += f"\n\n📚 I can access {len(docs)} documents from your knowledge base: "
            base_response += ", ".join([doc['name'] for doc in docs[:3]])
            if len(docs) > 3:
                base_response += f" and {len(docs) - 3} more."
        
        # Add admin-specific functionality hints
        base_response += "\n\n🔧 As your admin assistant, I can help you with:"
        base_response += "\n• Customer analytics and conversation metrics"
        base_response += "\n• System performance and usage statistics" 
        base_response += "\n• Knowledge base management and document search"
        base_response += "\n• Testing chatbot responses and configurations"
        
        # Add test mode notice
        base_response += "\n\n💡 This is a test response. To enable real LLM functionality, configure your API keys in the Django admin panel."
        
        return base_response
    
    @classmethod
    def get_conversation_history_response(cls, request, conversation_id: str) -> JsonResponse:
        """Get conversation history for a specific conversation"""
        try:
            if not conversation_id:
                raise ValidationException('conversation_id', 'Conversation ID is required')
            
            history = ConversationService.get_conversation_history(request, conversation_id)
            conversations = ConversationService.get_all_conversations(request)
            
            return JsonResponse({
                'success': True,
                'history': history,
                'conversations': conversations,
                'current_conversation_id': conversation_id
            })
            
        except ValidationException as e:
            return JsonResponse({
                'success': False,
                'error': e.message,
                'error_code': e.error_code
            }, status=400)
            
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
