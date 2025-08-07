from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import path, reverse
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.template.response import TemplateResponse
from django.utils import timezone
import json
import uuid
from .models import AIHelperChat, AIHelperMessage, AIHelperKnowledgeBase


class AIHelperAdminMixin:
    """Mixin to add AI Helper functionality to admin site"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ai_helper/chat/', self.admin_view(self.ai_helper_chat_view), name='ai_helper_chat'),
            path('ai_helper/api/send-message/', self.admin_view(self.ai_helper_send_message_api), name='ai_helper_send_message'),
            path('ai_helper/api/get-messages/<str:session_id>/', self.admin_view(self.ai_helper_get_messages_api), name='ai_helper_get_messages'),
        ]
        return custom_urls + urls

    def ai_helper_chat_view(self, request):
        """Main chat interface"""
        # Get or create chat session
        session_id = request.GET.get('session') or str(uuid.uuid4())
        
        try:
            chat = AIHelperChat.objects.get(session_id=session_id, user=request.user)
        except AIHelperChat.DoesNotExist:
            chat = AIHelperChat.objects.create(
                user=request.user,
                session_id=session_id,
                title=_('New AI Helper Session')
            )
        
        context = {
            'title': _('AI Helper'),
            'chat': chat,
            'session_id': session_id,
        }
        
        return TemplateResponse(request, 'admin/ai_helper/chat.html', context)

    @csrf_exempt
    def ai_helper_send_message_api(self, request):
        """API endpoint to send message to AI"""
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            message_content = data.get('message', '').strip()
            
            if not session_id or not message_content:
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            # Get or create chat session
            chat, created = AIHelperChat.objects.get_or_create(
                session_id=session_id,
                user=request.user,
                defaults={'title': message_content[:50] + '...'}
            )
            
            # Save user message
            user_message = AIHelperMessage.objects.create(
                chat=chat,
                message_type='user',
                content=message_content
            )
            
            # Generate AI response
            ai_response = self._generate_ai_response(message_content, request.user)
            
            # Save AI response
            ai_message = AIHelperMessage.objects.create(
                chat=chat,
                message_type='assistant',
                content=ai_response
            )
            
            # Update chat timestamp
            chat.updated_at = timezone.now()
            chat.save()
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'timestamp': ai_message.created_at.isoformat()
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def ai_helper_get_messages_api(self, request, session_id):
        """API endpoint to get chat messages"""
        try:
            chat = get_object_or_404(AIHelperChat, session_id=session_id, user=request.user)
            messages = chat.messages.all().order_by('created_at')
            
            message_data = [
                {
                    'type': msg.message_type,
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat()
                }
                for msg in messages
            ]
            
            return JsonResponse({
                'success': True,
                'messages': message_data
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    def _generate_ai_response(self, message, user):
        """Generate AI response based on user message"""
        message_lower = message.lower()
        
        # Import here to avoid circular imports
        from documents.models import Document
        from chat.models import Conversation, Message
        from authentication.models import UserProfile
        from analytics.models import AnalyticsSummary
        
        # System statistics
        if any(keyword in message_lower for keyword in ['stats', 'statistics', 'overview', 'summary', 'dashboard']):
            doc_count = Document.objects.filter(is_active=True).count()
            conversation_count = Conversation.objects.count()
            user_count = UserProfile.objects.count()
            
            return f"""📊 **System Overview**

📄 **Documents**: {doc_count} active documents
💬 **Conversations**: {conversation_count} total conversations  
👥 **Users**: {user_count} registered users
🕐 **Last updated**: {timezone.now().strftime('%Y-%m-%d %H:%M')}

What specific area would you like to explore?"""

        # Document-related queries
        elif any(keyword in message_lower for keyword in ['document', 'file', 'upload', 'pdf', 'doc']):
            doc_count = Document.objects.count()
            categories = Document.objects.values_list('category', flat=True).distinct().exclude(category='')
            file_types = Document.objects.values_list('file_type', flat=True).distinct().exclude(file_type='')
            
            return f"""📁 **Document Management Information**

📄 **Total Documents**: {doc_count}
📂 **Categories**: {', '.join(categories) if categories else 'None set'}
📋 **File Types**: {', '.join(file_types) if file_types else 'None'}

**Available Operations**:
• Upload new documents (PDF, DOCX, TXT, etc.)
• Organize by categories and tags
• Download and preview files
• Bulk management operations

Need help with a specific document operation?"""

        # User management queries
        elif any(keyword in message_lower for keyword in ['user', 'account', 'profile', 'permission']):
            return """👥 **User Management Information**

**User Features**:
• Profile management with preferences
• Role-based access control
• Session tracking
• Activity monitoring

**Admin Capabilities**:
• Create/edit user accounts
• Manage permissions
• View user activity
• Monitor sessions

What specific user management task can I help with?"""

        # Chat system queries
        elif any(keyword in message_lower for keyword in ['chat', 'conversation', 'message', 'llm']):
            return """💬 **Chat System Information**

**Features**:
• Real-time messaging
• Multiple LLM providers (OpenAI, Gemini, Claude)
• File attachments support
• Feedback system
• Session management

**Admin Controls**:
• Configure AI prompts
• Manage API settings
• Monitor conversations
• View analytics

Which aspect of the chat system interests you?"""

        # How to queries
        elif any(keyword in message_lower for keyword in ['how to', 'how do i', 'help', 'guide']):
            return """🎯 **How Can I Help?**

**I can assist with**:
📄 Document management operations
👥 User account administration  
💬 Chat system configuration
📊 Analytics and reporting
⚙️ System settings
🔧 Troubleshooting

**Just ask me about**:
• "How do I upload documents?"
• "Show me user statistics"  
• "How to configure chat settings?"
• "What's the system status?"

What would you like to learn about?"""

        # Default response
        else:
            return f"""🤖 **AI Helper**

Hello {user.username}! I'm your AI assistant for managing this system.

**I can help you with**:
• 📄 Document management
• 👥 User administration
• 💬 Chat system
• 📊 Analytics & reports
• ⚙️ System configuration

**Try asking me**:
• "Show me system statistics"
• "How do I manage documents?"
• "What's the user activity?"
• "Help with chat settings"

What would you like to know about?"""


# Register with main admin site
@admin.register(AIHelperChat)
class AIHelperChatAdmin(admin.ModelAdmin):
    list_display = ['title_display', 'user_display', 'message_count', 'created_at_display', 'updated_at_display']
    list_filter = ['created_at', 'updated_at', 'is_active']
    search_fields = ['title', 'user__username', 'session_id']
    readonly_fields = ['session_id', 'created_at', 'updated_at']
    
    def title_display(self, obj):
        return obj.title or f"Chat {obj.session_id[:8]}"
    title_display.short_description = _('Title')
    
    def user_display(self, obj):
        return obj.user.username
    user_display.short_description = _('User')
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = _('Messages')
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = _('Created')
    
    def updated_at_display(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_display.short_description = _('Last Updated')


@admin.register(AIHelperMessage)
class AIHelperMessageAdmin(admin.ModelAdmin):
    list_display = ['chat_display', 'message_type_display', 'content_preview', 'created_at_display']
    list_filter = ['message_type', 'created_at']
    search_fields = ['content', 'chat__title', 'chat__user__username']
    readonly_fields = ['created_at']
    
    def chat_display(self, obj):
        return str(obj.chat)
    chat_display.short_description = _('Chat')
    
    def message_type_display(self, obj):
        colors = {
            'user': '#007cba',
            'assistant': '#28a745',  
            'system': '#6c757d'
        }
        color = colors.get(obj.message_type, '#333')
        return format_html(
            '<span style="color: {};">●</span> {}',
            color, obj.get_message_type_display()
        )
    message_type_display.short_description = _('Type')
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = _('Content')
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = _('Created')


@admin.register(AIHelperKnowledgeBase)
class AIHelperKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['topic_display', 'category_display', 'is_active_display', 'updated_at_display']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['topic', 'question_patterns', 'response_template']
    
    def topic_display(self, obj):
        return obj.topic
    topic_display.short_description = _('Topic')
    
    def category_display(self, obj):
        return obj.get_category_display()
    category_display.short_description = _('Category')
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.short_description = _('Active')
    is_active_display.boolean = True
    
    def updated_at_display(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    updated_at_display.short_description = _('Updated')