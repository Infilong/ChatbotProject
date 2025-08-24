"""Refactored admin views using service layer architecture"""

import json
from typing import Dict, Any
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from core.services.analytics_service import AnalyticsService
from core.services.conversation_service import ConversationService
from core.services.llm_admin_service import LLMAdminService
from documents.models import Document
from chat.models import Conversation


@staff_member_required
def admin_llm_chat(request):
    """LLM Chat Interface for Django Admin"""
    context = LLMAdminService.get_admin_context(request)
    return render(request, 'admin/chat/llm_chat.html', context)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(staff_member_required, name='dispatch')
class AdminChatAPI(View):
    """API endpoint for admin chat functionality"""
    
    def post(self, request):
        """Handle chat messages"""
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            provider = data.get('provider', 'auto')  # Use 'auto' to let backend choose active provider
            use_knowledge = data.get('use_knowledge_base', data.get('use_knowledge', False))
            conversation_id = data.get('conversation_id')
            
            if not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message cannot be empty'
                }, status=400)
            
            # Create new conversation if none provided
            if not conversation_id:
                conversation_id = ConversationService.create_new_conversation(request)
            
            # Use async_to_sync to properly handle the async call in Django view context
            from asgiref.sync import async_to_sync
            return async_to_sync(LLMAdminService.process_chat_message)(
                request, message, provider, use_knowledge, conversation_id
            )
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            
            # Log the full traceback for debugging
            error_traceback = traceback.format_exc()
            logger.error(f"Admin chat API error: {e}")
            logger.error(f"Full traceback: {error_traceback}")
            
            return JsonResponse({
                'success': False,
                'error': f'Server error: {str(e)}',
                'traceback': error_traceback
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')  
@method_decorator(staff_member_required, name='dispatch')
class AdminChatHistory(View):
    """API endpoint for chat history management"""
    
    def get(self, request):
        """Get conversation history"""
        conversation_id = request.GET.get('conversation_id')
        
        # If no conversation_id provided, return list of all conversations
        if not conversation_id:
            try:
                conversations = ConversationService.get_all_conversations(request)
                return JsonResponse({
                    'success': True,
                    'conversations': conversations,
                    'history': [],
                    'current_conversation_id': None
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error getting conversations: {str(e)}'
                }, status=500)
        
        return LLMAdminService.get_conversation_history_response(request, conversation_id)
    
    def post(self, request):
        """Handle conversation management actions"""
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            return LLMAdminService.handle_conversation_action(request, action, data)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
    
    def delete(self, request):
        """Delete specific conversation"""
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            
            if not conversation_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Conversation ID is required'
                }, status=400)
            
            success = ConversationService.delete_conversation(request, conversation_id)
            
            return JsonResponse({
                'success': success,
                'error': None if success else 'Failed to delete conversation'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Failed to delete conversation: {str(e)}'
            }, status=500)


@staff_member_required
def knowledge_base_test(request):
    """Knowledge Base Testing Interface"""
    context = {
        'total_documents': AnalyticsService.get_document_analytics()['total_documents'],
        'analytics': AnalyticsService.get_conversation_metrics()
    }
    return render(request, 'admin/documents/knowledge_test.html', context)


@method_decorator(staff_member_required, name='dispatch')
class DocumentStatsAPI(View):
    """API endpoint for admin dashboard statistics"""
    
    def get(self, request):
        """Get dashboard statistics"""
        try:
            # Get basic counts
            total_documents = Document.objects.filter(is_active=True).count()
            total_conversations = Conversation.objects.count()
            processed_documents = Document.objects.filter(
                is_active=True, 
                extracted_text__isnull=False
            ).exclude(extracted_text='').count()
            
            stats = {
                'total_documents': total_documents,
                'total_references': total_conversations,
                'processed_documents': processed_documents,
                'processing_rate': (processed_documents / total_documents * 100) if total_documents > 0 else 0
            }
            
            return JsonResponse({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)