"""
REST API views for chat application
"""

import asyncio
import logging
from typing import Dict, Any

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt
from .serializers import (
    ConversationSerializer, MessageSerializer, MessageCreateSerializer,
    MessageFeedbackSerializer, UserSessionSerializer, APIConfigurationSerializer,
    AdminPromptSerializer, LLMChatRequestSerializer, LLMChatResponseSerializer,
    LLMTestRequestSerializer, LLMTestResponseSerializer
)
from .llm_services import LLMManager, LLMError

logger = logging.getLogger(__name__)


# Conversation Views
class ConversationListCreateView(generics.ListCreateAPIView):
    """List user's conversations or create new conversation"""
    
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-updated_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a conversation"""
    
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete - set is_active to False
        instance.is_active = False
        instance.save()


# Message Views
class MessageListCreateView(generics.ListCreateAPIView):
    """List messages in conversation or create new message"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs['conversation_id']
        return Message.objects.filter(
            conversation_id=conversation_id,
            conversation__user=self.request.user
        ).order_by('timestamp')
    
    def perform_create(self, serializer):
        conversation_id = self.kwargs['conversation_id']
        try:
            conversation = Conversation.objects.get(
                id=conversation_id,
                user=self.request.user
            )
            serializer.save(conversation=conversation)
        except Conversation.DoesNotExist:
            raise ValueError("Conversation not found")


class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a message"""
    
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Message.objects.filter(
            conversation__user=self.request.user
        )


class MessageFeedbackView(generics.UpdateAPIView):
    """Update message feedback"""
    
    serializer_class = MessageFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Message.objects.filter(
            conversation__user=self.request.user,
            sender_type='bot'  # Only bot messages can receive feedback
        )


# LLM API Views
class LLMChatView(APIView):
    """Generate LLM response for user message"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = LLMChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        user_message = data['message']
        conversation_id = data.get('conversation_id')
        provider = data.get('provider')
        language = data.get('language', 'en')
        max_tokens = data.get('max_tokens', 1000)
        temperature = data.get('temperature', 0.7)
        
        try:
            with transaction.atomic():
                # Get or create conversation
                if conversation_id:
                    conversation = Conversation.objects.get(
                        id=conversation_id,
                        user=request.user
                    )
                else:
                    conversation = Conversation.objects.create(
                        user=request.user
                    )
                
                # Save user message
                user_msg = Message.objects.create(
                    conversation=conversation,
                    content=user_message,
                    sender_type='user'
                )
                
                # Get conversation history for context
                history = list(
                    conversation.messages.all()
                    .exclude(id=user_msg.id)
                    .order_by('-timestamp')[:10]
                    .reverse()
                )
                
                # Generate LLM response
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    bot_response, metadata = loop.run_until_complete(
                        LLMManager.generate_chat_response(
                            user_message=user_message,
                            conversation_history=history,
                            provider=provider,
                            language=language
                        )
                    )
                    
                finally:
                    loop.close()
                
                # Save bot response
                bot_msg = Message.objects.create(
                    conversation=conversation,
                    content=bot_response,
                    sender_type='bot',
                    metadata=metadata,
                    llm_model_used=metadata.get('model'),
                    response_time=metadata.get('response_time')
                )
                
                response_data = LLMChatResponseSerializer({
                    'response': bot_response,
                    'conversation_id': conversation.id,
                    'message_id': bot_msg.id,
                    'metadata': metadata
                }).data
                
                return Response(response_data, status=status.HTTP_201_CREATED)
        
        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            return Response(
                {'error': f'LLM service error: {str(e)}'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error in LLM chat: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LLMTestView(APIView):
    """Test LLM API configuration"""
    
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = LLMTestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = serializer.validated_data['provider']
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                LLMManager.test_configuration(provider)
            )
            
        except Exception as e:
            result = {
                'status': 'error',
                'provider': provider,
                'error': str(e)
            }
        finally:
            loop.close()
        
        response_serializer = LLMTestResponseSerializer(result)
        return Response(response_serializer.data)


class APIConfigurationListView(generics.ListAPIView):
    """List LLM API configurations (admin only)"""
    
    serializer_class = APIConfigurationSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = APIConfiguration.objects.all().order_by('provider')


# Session Views
class UserSessionListView(generics.ListCreateAPIView):
    """List user sessions"""
    
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSession.objects.filter(
            user=self.request.user
        ).order_by('-started_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete user session"""
    
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        # End session if requested
        if 'ended_at' in self.request.data and not serializer.instance.ended_at:
            serializer.save(
                ended_at=timezone.now(),
                is_active=False
            )
        else:
            serializer.save()


# Admin Prompt Views
class AdminPromptListView(generics.ListAPIView):
    """List admin prompts"""
    
    serializer_class = AdminPromptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = AdminPrompt.objects.filter(is_active=True)
        
        # Filter by prompt type if specified
        prompt_type = self.request.query_params.get('type')
        if prompt_type:
            queryset = queryset.filter(prompt_type=prompt_type)
        
        # Filter by language if specified
        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)
        
        return queryset.order_by('prompt_type', 'language', '-is_default')


class AdminPromptDetailView(generics.RetrieveAPIView):
    """Retrieve admin prompt detail"""
    
    serializer_class = AdminPromptSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = AdminPrompt.objects.filter(is_active=True)


# Utility API Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def chat_status(request):
    """Get chat system status"""
    try:
        # Check active configurations
        active_configs = APIConfiguration.objects.filter(is_active=True)
        
        status_data = {
            'status': 'online',
            'user': request.user.username,
            'available_providers': [
                {
                    'provider': config.provider,
                    'model': config.model_name
                }
                for config in active_configs
            ],
            'total_conversations': Conversation.objects.filter(
                user=request.user
            ).count(),
            'server_time': timezone.now().isoformat()
        }
        
        return Response(status_data)
        
    except Exception as e:
        logger.error(f"Error getting chat status: {e}")
        return Response(
            {'status': 'error', 'message': 'Unable to get status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def end_conversation(request, conversation_id):
    """End a conversation"""
    try:
        conversation = Conversation.objects.get(
            id=conversation_id,
            user=request.user
        )
        
        conversation.is_active = False
        conversation.save()
        
        return Response({'status': 'conversation ended'})
        
    except Conversation.DoesNotExist:
        return Response(
            {'error': 'Conversation not found'},
            status=status.HTTP_404_NOT_FOUND
        )


# Admin Progress Tracking Views
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def langextract_progress(request):
    """
    Get progress updates for LangExtract analysis
    Uses session to store progress information
    """
    progress_data = request.session.get('langextract_progress', {
        'status': 'idle',
        'current_step': '',
        'processed': 0,
        'total': 0,
        'errors': [],
        'success_count': 0,
        'error_count': 0
    })
    
    return Response(progress_data)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def clear_langextract_progress(request):
    """Clear progress tracking data"""
    if 'langextract_progress' in request.session:
        del request.session['langextract_progress']
    
    return Response({'status': 'cleared'})
