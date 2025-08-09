"""
Admin views for LLM chat interface and testing
"""

import json
import asyncio
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from asgiref.sync import sync_to_async
from django.db.models import Count, Avg, Q, Max
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta

from .llm_services import LLMManager
from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt
from documents.models import Document


def get_customer_analytics_context(query):
    """Get customer and analytics data based on query content"""
    context_data = {}
    query_lower = query.lower()
    
    # Customer satisfaction analysis
    if any(term in query_lower for term in ['satisfaction', 'feedback', 'rating', 'happy', 'satisfied']):
        satisfaction_stats = Conversation.objects.filter(
            satisfaction_score__isnull=False
        ).aggregate(
            avg_satisfaction=Avg('satisfaction_score'),
            total_rated=Count('id'),
            high_satisfaction=Count('id', filter=Q(satisfaction_score__gte=4.0)),
            low_satisfaction=Count('id', filter=Q(satisfaction_score__lt=3.0))
        )
        
        context_data['satisfaction'] = {
            'average_score': round(satisfaction_stats['avg_satisfaction'] or 0, 2),
            'total_conversations_rated': satisfaction_stats['total_rated'],
            'high_satisfaction_count': satisfaction_stats['high_satisfaction'],
            'low_satisfaction_count': satisfaction_stats['low_satisfaction'],
            'satisfaction_rate': round(
                (satisfaction_stats['high_satisfaction'] / max(satisfaction_stats['total_rated'], 1)) * 100, 1
            )
        }
    
    # Message and conversation statistics
    if any(term in query_lower for term in ['conversations', 'messages', 'activity', 'usage', 'stats']):
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        
        conversation_stats = {
            'total_conversations': Conversation.objects.count(),
            'active_conversations': Conversation.objects.filter(is_active=True).count(),
            'conversations_last_30_days': Conversation.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            'conversations_last_7_days': Conversation.objects.filter(
                created_at__gte=last_7_days
            ).count(),
            'total_messages': Message.objects.count(),
            'bot_messages': Message.objects.filter(sender_type='bot').count(),
            'user_messages': Message.objects.filter(sender_type='user').count(),
        }
        
        context_data['conversations'] = conversation_stats
    
    # User activity analysis
    if any(term in query_lower for term in ['users', 'customers', 'active', 'engagement']):
        user_stats = User.objects.aggregate(
            total_users=Count('id'),
            users_with_conversations=Count('id', filter=Q(conversations__isnull=False)),
            active_users_last_7_days=Count(
                'id', 
                filter=Q(conversations__updated_at__gte=timezone.now() - timedelta(days=7)),
                distinct=True
            )
        )
        
        # Top active users
        top_users = User.objects.annotate(
            conversation_count=Count('conversations'),
            message_count=Count('conversations__messages', filter=Q(conversations__messages__sender_type='user')),
            last_activity=Max('conversations__updated_at')
        ).filter(conversation_count__gt=0).order_by('-conversation_count')[:5]
        
        context_data['users'] = {
            'total_users': user_stats['total_users'],
            'users_with_conversations': user_stats['users_with_conversations'],
            'active_users_last_7_days': user_stats['active_users_last_7_days'],
            'top_active_users': [
                {
                    'username': user.username,
                    'conversations': user.conversation_count,
                    'messages': user.message_count,
                    'last_activity': user.last_activity.strftime('%Y-%m-%d %H:%M') if user.last_activity else 'Never'
                } for user in top_users
            ]
        }
    
    # Response time and performance analysis
    if any(term in query_lower for term in ['response', 'time', 'performance', 'speed', 'fast', 'slow']):
        response_stats = Message.objects.filter(
            sender_type='bot',
            response_time__isnull=False
        ).aggregate(
            avg_response_time=Avg('response_time'),
            total_bot_messages=Count('id')
        )
        
        context_data['performance'] = {
            'average_response_time': round(response_stats['avg_response_time'] or 0, 3),
            'total_bot_responses': response_stats['total_bot_messages']
        }
    
    # Feedback analysis
    if any(term in query_lower for term in ['feedback', 'positive', 'negative', 'thumbs']):
        feedback_stats = Message.objects.filter(
            feedback__isnull=False
        ).values('feedback').annotate(count=Count('id'))
        
        feedback_data = {item['feedback']: item['count'] for item in feedback_stats}
        
        context_data['feedback'] = {
            'positive_feedback': feedback_data.get('positive', 0),
            'negative_feedback': feedback_data.get('negative', 0),
            'total_feedback': sum(feedback_data.values()),
            'positive_rate': round(
                (feedback_data.get('positive', 0) / max(sum(feedback_data.values()), 1)) * 100, 1
            )
        }
    
    # LLM model usage analysis  
    if any(term in query_lower for term in ['models', 'llm', 'ai', 'provider', 'openai', 'gemini', 'claude']):
        model_stats = Message.objects.filter(
            sender_type='bot',
            llm_model_used__isnull=False
        ).values('llm_model_used').annotate(
            count=Count('id')
        ).order_by('-count')
        
        context_data['models'] = {
            'model_usage': [
                {
                    'model': item['llm_model_used'],
                    'usage_count': item['count']
                } for item in model_stats
            ]
        }
    
    return context_data


def get_recent_conversations_context(limit=5):
    """Get recent conversation summaries for context"""
    recent_conversations = Conversation.objects.filter(
        is_active=True
    ).select_related('user').prefetch_related('messages').order_by('-updated_at')[:limit]
    
    conversations_summary = []
    for conv in recent_conversations:
        last_user_message = conv.messages.filter(sender_type='user').last()
        last_bot_message = conv.messages.filter(sender_type='bot').last()
        
        conversations_summary.append({
            'id': conv.id,
            'user': conv.user.username,
            'title': conv.get_title(),
            'total_messages': conv.total_messages,
            'satisfaction_score': conv.satisfaction_score,
            'last_user_message': last_user_message.content[:100] if last_user_message else None,
            'last_bot_message': last_bot_message.content[:100] if last_bot_message else None,
            'updated_at': conv.updated_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return conversations_summary


@staff_member_required
def admin_llm_chat(request):
    """Admin LLM chat interface"""
    from django.contrib.admin import site
    
    context = {
        'title': 'LLM Chat Interface',
        'available_providers': ['openai', 'gemini', 'claude'],
        'total_documents': Document.objects.filter(is_active=True).count(),
        'processed_documents': Document.objects.filter(is_active=True, extracted_text__isnull=False).exclude(extracted_text='').count(),
        # Add admin site context for navigation
        'has_permission': True,
        'site_title': site.site_title,
        'site_header': site.site_header,
        'site_url': '/',
        'app_list': site.get_app_list(request),
    }
    return render(request, 'admin/chat/llm_chat.html', context)



@method_decorator(staff_member_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class AdminLLMChatAPI(View):
    """API endpoint for admin LLM chat"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            provider = data.get('provider', 'openai')
            use_knowledge_base = data.get('use_knowledge_base', True)
            
            if not message:
                return JsonResponse({
                    'error': 'Message cannot be empty'
                }, status=400)
            
            # Try to use real LLM first, fall back to test response
            try:
                from asgiref.sync import sync_to_async
                import asyncio
                
                # Check if API configuration exists for the provider
                from chat.models import APIConfiguration
                api_config = APIConfiguration.objects.filter(
                    provider=provider,
                    is_active=True
                ).first()
                
                if api_config and api_config.api_key:
                    # Try direct API call to bypass Django async issues
                    try:
                        if provider == 'gemini':
                            response, metadata = self._call_gemini_directly(
                                api_config, message, use_knowledge_base
                            )
                        elif provider == 'openai':
                            response, metadata = self._call_openai_directly(
                                api_config, message, use_knowledge_base
                            )
                        else:
                            # Fallback: try the async approach
                            from asgiref.sync import async_to_sync
                            sync_llm_call = async_to_sync(LLMManager.generate_chat_response)
                            response, metadata = sync_llm_call(
                                user_message=message,
                                conversation_history=[],
                                provider=provider,
                                use_knowledge_base=use_knowledge_base
                            )
                        
                        # Add admin-specific metadata
                        metadata.update({
                            'admin_test': False,
                            'api_config_used': f"{provider} - {api_config.model_name}",
                            'real_llm_used': True
                        })
                        
                    except Exception as llm_error:
                        # LLM failed, provide demo response instead of error
                        response, metadata = self._generate_demo_response(
                            message, provider, use_knowledge_base, 
                            api_error=str(llm_error), has_api_config=True
                        )
                else:
                    # No API config, use realistic demo response
                    response, metadata = self._generate_demo_response(
                        message, provider, use_knowledge_base
                    )
                    
            except Exception as e:
                # Fallback to basic test response
                response = f"❌ System Error - Using Fallback Response\n\n" \
                          f"Error: {str(e)}\n" \
                          f"📝 Your message: '{message}'\n" \
                          f"🤖 Provider: {provider.upper()}"
                
                metadata = {
                    'provider_used': provider,
                    'tokens_used': 0,
                    'knowledge_context_used': False,
                    'referenced_documents': [],
                    'admin_test': True,
                    'system_error': str(e)
                }
            
            return JsonResponse({
                'response': response,
                'metadata': {
                    'provider_used': metadata.get('provider_used', provider),
                    'tokens_used': metadata.get('tokens_used', 0),
                    'knowledge_context_used': metadata.get('knowledge_context_used', False),
                    'referenced_documents': [
                        {
                            'name': doc.name,
                            'category': doc.category,
                            'effectiveness_score': doc.effectiveness_score
                        } for doc in metadata.get('referenced_documents', [])
                    ]
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to generate response: {str(e)}'
            }, status=500)
    
    def _call_gemini_directly(self, api_config, message, use_knowledge_base):
        """Direct Gemini API call to bypass async issues"""
        import requests
        
        # Add knowledge base context if enabled
        used_docs = []
        analytics_context = ""
        if use_knowledge_base:
            try:
                from documents.knowledge_base import KnowledgeBase
                context, used_docs = KnowledgeBase.get_knowledge_context(message)
                if context:
                    analytics_context = f"Knowledge Base Context:\n{context}\n\n"
            except:
                used_docs = []
        
        # Add customer analytics context
        try:
            analytics_data = get_customer_analytics_context(message)
            if analytics_data:
                analytics_context += "Customer Analytics Data:\n"
                for key, data in analytics_data.items():
                    analytics_context += f"{key.title()}: {data}\n"
                analytics_context += "\n"
                
            # Add recent conversations context for better customer understanding  
            if any(term in message.lower() for term in ['conversation', 'customer', 'user', 'recent']):
                recent_convs = get_recent_conversations_context(3)
                if recent_convs:
                    analytics_context += "Recent Customer Conversations:\n"
                    for conv in recent_convs:
                        analytics_context += f"- User: {conv['user']}, Messages: {conv['total_messages']}, "
                        analytics_context += f"Satisfaction: {conv['satisfaction_score'] or 'Not rated'}\n"
                    analytics_context += "\n"
        except Exception as e:
            analytics_context += f"Analytics data unavailable: {str(e)}\n"
        
        # Combine all context
        if analytics_context:
            full_message = f"{analytics_context}User Question: {message}"
        else:
            full_message = message
        
        # Gemini API call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_config.model_name}:generateContent?key={api_config.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": full_message
                }]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result['candidates'][0]['content']['parts'][0]['text']
        
        # Track document usage
        for doc in used_docs:
            doc.increment_reference()
        
        metadata = {
            'provider_used': 'gemini',
            'tokens_used': result.get('usageMetadata', {}).get('totalTokenCount', 0),
            'knowledge_context_used': use_knowledge_base and bool(used_docs),
            'referenced_documents': [{'name': doc.name, 'category': doc.category} for doc in used_docs],
            'direct_api_call': True,
            'analytics_context_used': bool(analytics_context),
            'context_length': len(analytics_context)
        }
        
        return ai_response, metadata
    
    def _call_openai_directly(self, api_config, message, use_knowledge_base):
        """Direct OpenAI API call to bypass async issues"""
        import requests
        
        # Add knowledge base context if enabled
        used_docs = []
        analytics_context = ""
        if use_knowledge_base:
            try:
                from documents.knowledge_base import KnowledgeBase
                context, used_docs = KnowledgeBase.get_knowledge_context(message)
                if context:
                    analytics_context = f"Knowledge Base Context:\n{context}\n\n"
            except:
                used_docs = []
        
        # Add customer analytics context
        try:
            analytics_data = get_customer_analytics_context(message)
            if analytics_data:
                analytics_context += "Customer Analytics Data:\n"
                for key, data in analytics_data.items():
                    analytics_context += f"{key.title()}: {data}\n"
                analytics_context += "\n"
                
            # Add recent conversations context
            if any(term in message.lower() for term in ['conversation', 'customer', 'user', 'recent']):
                recent_convs = get_recent_conversations_context(3)
                if recent_convs:
                    analytics_context += "Recent Customer Conversations:\n"
                    for conv in recent_convs:
                        analytics_context += f"- User: {conv['user']}, Messages: {conv['total_messages']}, "
                        analytics_context += f"Satisfaction: {conv['satisfaction_score'] or 'Not rated'}\n"
                    analytics_context += "\n"
        except Exception as e:
            analytics_context += f"Analytics data unavailable: {str(e)}\n"
        
        # Combine all context
        if analytics_context:
            full_message = f"{analytics_context}User Question: {message}"
        else:
            full_message = message
        
        # OpenAI API call
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": api_config.model_name or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": full_message}],
            "max_tokens": 800
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result['choices'][0]['message']['content']
        
        # Track document usage
        for doc in used_docs:
            doc.increment_reference()
        
        metadata = {
            'provider_used': 'openai',
            'tokens_used': result.get('usage', {}).get('total_tokens', 0),
            'knowledge_context_used': use_knowledge_base and bool(used_docs),
            'referenced_documents': [{'name': doc.name, 'category': doc.category} for doc in used_docs],
            'direct_api_call': True,
            'analytics_context_used': bool(analytics_context),
            'context_length': len(analytics_context)
        }
        
        return ai_response, metadata
    
    def _generate_conversation_title(self, first_user_message, provider='openai'):
        """Generate a concise conversation title using AI"""
        try:
            # Get API configuration
            from chat.models import APIConfiguration
            api_config = APIConfiguration.objects.filter(
                provider=provider,
                is_active=True
            ).first()
            
            if not api_config or not api_config.api_key:
                # Fallback to intelligent title generation using keywords
                return self._generate_smart_title_fallback(first_user_message)
            
            title_prompt = f"""Generate a concise, descriptive title (max 6 words) for a conversation that starts with this user message: "{first_user_message}"

The title should be:
- 6 words or less
- Descriptive of the topic
- Professional and clear
- No quotes or special characters

Examples:
- "Customer satisfaction report analysis"
- "Database query assistance needed"
- "Knowledge base search help"

Title:"""
            
            if provider == 'gemini':
                return self._call_gemini_for_title(api_config, title_prompt)
            elif provider == 'openai':
                return self._call_openai_for_title(api_config, title_prompt)
            else:
                return first_user_message[:40] + ("..." if len(first_user_message) > 40 else "")
                
        except Exception as e:
            # Fallback to intelligent title generation
            return self._generate_smart_title_fallback(first_user_message)
    
    def _generate_smart_title_fallback(self, message):
        """Generate intelligent titles without API using keyword analysis"""
        import re
        
        message_lower = message.lower().strip()
        
        # Define keyword patterns and corresponding titles
        keyword_patterns = [
            # Analytics and statistics
            (r'\b(satisfaction|rating|feedback|score|review)\b', 'Customer Satisfaction Analysis'),
            (r'\b(analytics|statistics|stats|data|report|metric)\b', 'Analytics and Statistics'),
            (r'\b(conversation|chat|message|user|customer)\b.*\b(count|number|how many)\b', 'Conversation Statistics'),
            (r'\b(active|activity|usage|engagement)\b', 'User Activity Analysis'),
            
            # Database queries
            (r'\b(database|db|query|sql|table|record)\b', 'Database Query Help'),
            (r'\b(data|information|info|details|show me)\b', 'Data Information Request'),
            
            # Knowledge base
            (r'\b(knowledge|document|file|search|find)\b', 'Knowledge Base Search'),
            (r'\b(help|assist|support|guide)\b', 'General Assistance'),
            
            # Technical issues
            (r'\b(error|problem|issue|bug|fix|troubleshoot)\b', 'Technical Issue Resolution'),
            (r'\b(how to|how do|tutorial|explain|configure)\b', 'How-To Question'),
            
            # Performance and metrics
            (r'\b(performance|speed|response time|latency)\b', 'Performance Analysis'),
            (r'\b(model|llm|ai|bot|chatbot)\b', 'AI Model Discussion'),
            
            # Admin tasks
            (r'\b(admin|manage|configure|settings|setup)\b', 'Admin Configuration'),
            (r'\b(test|testing|demo|example)\b', 'Testing and Demo'),
        ]
        
        # Check patterns in order of specificity
        for pattern, title in keyword_patterns:
            if re.search(pattern, message_lower):
                return title
        
        # If no patterns match, create title from first few meaningful words
        words = re.findall(r'\b\w+\b', message)
        if len(words) == 0:
            return "General Question"
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'when', 'where', 'why', 'how', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        meaningful_words = [word.title() for word in words if word.lower() not in stop_words][:4]
        
        if len(meaningful_words) >= 2:
            title = ' '.join(meaningful_words)
            return title if len(title) <= 50 else title[:47] + '...'
        else:
            # Last resort: use first part of message
            return message[:40] + ('...' if len(message) > 40 else '')
    
    def _call_gemini_for_title(self, api_config, prompt):
        """Call Gemini API for title generation"""
        import requests
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_config.model_name}:generateContent?key={api_config.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        title = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Clean up the title
        title = title.replace('"', '').replace("'", "").strip()
        if title.startswith('Title:'):
            title = title[6:].strip()
        
        return title[:50]  # Ensure max length
    
    def _call_openai_for_title(self, api_config, prompt):
        """Call OpenAI API for title generation"""
        import requests
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": api_config.model_name or "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 20,
            "temperature": 0.3
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        title = result['choices'][0]['message']['content'].strip()
        
        # Clean up the title
        title = title.replace('"', '').replace("'", "").strip()
        if title.startswith('Title:'):
            title = title[6:].strip()
        
        return title[:50]  # Ensure max length

    def _generate_demo_response(self, message, provider, use_knowledge_base, api_error=None, has_api_config=False):
        """Generate realistic demo responses for testing admin interface"""
        import random
        
        # Get knowledge base context if enabled
        knowledge_context = ""
        used_docs = []
        if use_knowledge_base:
            try:
                from documents.knowledge_base import KnowledgeBase
                context, used_docs = KnowledgeBase.get_knowledge_context(message)
                if context:
                    knowledge_context = context[:200] + "..." if len(context) > 200 else context
                # Track document usage in demo mode
                for doc in used_docs:
                    doc.increment_reference()
            except:
                used_docs = []
        
        # Generate realistic responses based on provider
        if provider == 'gemini':
            responses = [
                "Hello! I'm Gemini, Google's AI assistant. I'm here to help you with any questions or tasks you might have. How can I assist you today?",
                "Hi there! As Google's Gemini AI, I can help with a wide variety of topics including answering questions, creative writing, analysis, and more. What would you like to explore?",
                "Greetings! I'm Gemini, and I'm ready to assist you. Whether you need information, help with problem-solving, or creative collaboration, I'm here to help!",
                "Hello! I'm Google's Gemini AI assistant. I can help with research, writing, analysis, coding, and much more. What can I help you with?",
            ]
        elif provider == 'openai':
            responses = [
                "Hello! I'm ChatGPT, an AI assistant created by OpenAI. I'm here to help answer questions, assist with tasks, and have meaningful conversations. How can I help you today?",
                "Hi there! I'm ChatGPT from OpenAI. I can help with a wide range of tasks including answering questions, writing, analysis, and problem-solving. What would you like to work on?",
                "Hello! I'm an AI assistant built by OpenAI. I'm designed to be helpful, harmless, and honest. How can I assist you today?",
                "Hi! I'm ChatGPT, OpenAI's language model. I'm here to help with questions, creative projects, analysis, and more. What can I help you with?",
            ]
        else:
            responses = [
                f"Hello! I'm Claude, Anthropic's AI assistant. I'm here to help with any questions or tasks you have. How can I assist you today?",
                f"Hi there! As Claude, I can help with analysis, writing, research, and creative projects. What would you like to work on together?",
            ]
        
        # Add analytics context to demo response
        analytics_info = ""
        try:
            analytics_data = get_customer_analytics_context(message)
            if analytics_data:
                analytics_info += "\n\nBased on your customer analytics data, I can provide insights about:\n"
                if 'satisfaction' in analytics_data:
                    sat_data = analytics_data['satisfaction']
                    analytics_info += f"- Customer Satisfaction: {sat_data['average_score']}/5.0 average score\n"
                    analytics_info += f"- {sat_data['satisfaction_rate']}% high satisfaction rate\n"
                
                if 'conversations' in analytics_data:
                    conv_data = analytics_data['conversations']
                    analytics_info += f"- {conv_data['total_conversations']} total conversations\n"
                    analytics_info += f"- {conv_data['conversations_last_7_days']} conversations in last 7 days\n"
                
                if 'users' in analytics_data:
                    user_data = analytics_data['users']
                    analytics_info += f"- {user_data['total_users']} total users\n"
                    analytics_info += f"- {user_data['active_users_last_7_days']} active users this week\n"
                
                if 'feedback' in analytics_data:
                    feedback_data = analytics_data['feedback']
                    analytics_info += f"- {feedback_data['positive_rate']}% positive feedback rate\n"
        except:
            pass
        
        # Handle knowledge base integration in response
        if knowledge_context and used_docs:
            base_response = random.choice(responses)
            kb_integration = f"\n\nBased on your documents, I can see information about customer service policies. " \
                           f"The processed document shows details about response times, refund policies, and contact information. " \
                           f"Would you like me to help you with something specific from your knowledge base?"
            demo_response = base_response + kb_integration + analytics_info
        else:
            demo_response = random.choice(responses) + analytics_info
        
        # Add demo notice
        if has_api_config:
            status_note = f"DEMO MODE: API configured but using simulated response\n" \
                         f"API Error: {api_error[:100]}...\n\n"
        else:
            status_note = f"DEMO MODE: Simulated {provider.upper()} response for testing\n" \
                         f"Add real API key to enable live responses\n\n"
        
        response = status_note + demo_response
        
        # Generate realistic metadata
        metadata = {
            'provider_used': provider,
            'tokens_used': random.randint(25, 85),
            'knowledge_context_used': use_knowledge_base and bool(used_docs),
            'referenced_documents': [{'name': doc.name, 'category': doc.category} for doc in used_docs],
            'demo_mode': True,
            'api_config_found': has_api_config,
            'simulated_response': True,
            'knowledge_docs_found': len(used_docs),
            'analytics_context_used': bool(analytics_info),
            'analytics_insights_provided': len([key for key in ['satisfaction', 'conversations', 'users', 'feedback'] 
                                               if key in str(analytics_info)])
        }
        
        return response, metadata



@method_decorator(staff_member_required, name='dispatch')
class AdminChatHistoryAPI(View):
    """API endpoint for managing admin chat conversations"""
    
    def get(self, request):
        """Get all conversations or specific conversation history"""
        try:
            conversation_id = request.GET.get('conversation_id')
            
            if conversation_id:
                # Get specific conversation
                session_key = f"admin_conversation_{request.user.id}_{conversation_id}"
                history = request.session.get(session_key, [])
                
                return JsonResponse({
                    'conversation_id': conversation_id,
                    'history': history
                })
            else:
                # Get all conversations list
                conversations_key = f"admin_conversations_{request.user.id}"
                conversations = request.session.get(conversations_key, [])
                
                return JsonResponse({
                    'conversations': conversations
                })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to load conversations: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """Save message to conversation or create new conversation"""
        try:
            data = json.loads(request.body)
            action = data.get('action', 'save_message')
            
            if action == 'new_conversation':
                # Create new conversation
                conversations_key = f"admin_conversations_{request.user.id}"
                conversations = request.session.get(conversations_key, [])
                
                # Generate new conversation ID
                conversation_id = f"conv_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{len(conversations) + 1}"
                
                # Create conversation metadata
                new_conversation = {
                    'id': conversation_id,
                    'title': 'New Conversation',
                    'created_at': timezone.now().isoformat(),
                    'updated_at': timezone.now().isoformat(),
                    'message_count': 0
                }
                
                conversations.insert(0, new_conversation)  # Add to beginning
                request.session[conversations_key] = conversations
                request.session.modified = True
                
                return JsonResponse({
                    'conversation_id': conversation_id,
                    'conversation': new_conversation
                })
            
            elif action == 'save_message':
                # Save message to existing conversation
                conversation_id = data.get('conversation_id')
                message = data.get('message', '')
                response = data.get('response', '')
                metadata = data.get('metadata', {})
                
                if not conversation_id or not message:
                    return JsonResponse({
                        'error': 'Conversation ID and message are required'
                    }, status=400)
                
                # Save to conversation history
                session_key = f"admin_conversation_{request.user.id}_{conversation_id}"
                history = request.session.get(session_key, [])
                
                timestamp = timezone.now().strftime('%H:%M:%S')
                
                # Add user message
                history.append({
                    'type': 'user',
                    'content': message,
                    'timestamp': timestamp
                })
                
                # Add bot response
                if response:
                    history.append({
                        'type': 'bot',
                        'content': response,
                        'timestamp': timestamp,
                        'metadata': metadata
                    })
                
                # Update conversation metadata
                conversations_key = f"admin_conversations_{request.user.id}"
                conversations = request.session.get(conversations_key, [])
                
                for conv in conversations:
                    if conv['id'] == conversation_id:
                        conv['updated_at'] = timezone.now().isoformat()
                        conv['message_count'] = len(history)
                        # Generate AI title with first message if it's still "New Conversation"
                        if conv['title'] == 'New Conversation' and len(history) >= 1:
                            first_user_message = next((h for h in history if h['type'] == 'user'), None)
                            if first_user_message:
                                # Generate AI title using the same API instance
                                try:
                                    from chat.admin_views import AdminLLMChatAPI
                                    api_instance = AdminLLMChatAPI()
                                    ai_title = api_instance._generate_conversation_title(
                                        first_user_message['content'], 
                                        provider='openai'  # Default to OpenAI for title generation
                                    )
                                    conv['title'] = ai_title
                                except Exception as e:
                                    # Fallback to simple truncation
                                    conv['title'] = first_user_message['content'][:40] + ('...' if len(first_user_message['content']) > 40 else '')
                        break
                
                request.session[session_key] = history
                request.session[conversations_key] = conversations
                request.session.modified = True
                
                return JsonResponse({'success': True})
            
            else:
                return JsonResponse({
                    'error': 'Invalid action'
                }, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to process request: {str(e)}'
            }, status=500)
    
    def delete(self, request):
        """Delete specific conversation"""
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            
            if not conversation_id:
                return JsonResponse({
                    'error': 'Conversation ID is required'
                }, status=400)
            
            # Delete conversation history
            session_key = f"admin_conversation_{request.user.id}_{conversation_id}"
            if session_key in request.session:
                del request.session[session_key]
            
            # Remove from conversations list
            conversations_key = f"admin_conversations_{request.user.id}"
            conversations = request.session.get(conversations_key, [])
            conversations = [c for c in conversations if c['id'] != conversation_id]
            request.session[conversations_key] = conversations
            request.session.modified = True
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to delete conversation: {str(e)}'
            }, status=500)

