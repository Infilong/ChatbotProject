"""
REST API views for chat application
Provides comprehensive API endpoints for frontend integration
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from asgiref.sync import sync_to_async, async_to_sync
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt
from .serializers import (
    ConversationSerializer, ConversationListSerializer, MessageSerializer,
    MessageCreateSerializer, MessageFeedbackSerializer, UserSessionSerializer,
    LLMChatRequestSerializer, LLMChatResponseSerializer, ConversationStatsSerializer,
    BulkMessageCreateSerializer, ConversationExportSerializer
)
from .llm_services import LLMManager, LLMError
from core.services.conversation_service import ConversationService
from analytics.langextract_service import LangExtractService

logger = logging.getLogger(__name__)



class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API endpoints"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationViewSet(ModelViewSet):
    """
    ViewSet for managing conversations
    Provides CRUD operations for conversations
    """
    
    serializer_class = ConversationSerializer
    permission_classes = [permissions.AllowAny]  # For development
    pagination_class = StandardResultsSetPagination
    
    def get_demo_user(self):
        """Get or create a demo user for anonymous access"""
        demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@datapro.solutions',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )
        return demo_user
    
    def get_queryset(self):
        """Filter conversations by current user"""
        user = self.request.user if self.request.user.is_authenticated else self.get_demo_user()
        return Conversation.objects.filter(user=user).order_by('-updated_at')
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def perform_create(self, serializer):
        """Set user when creating conversation"""
        user = self.request.user if self.request.user.is_authenticated else self.get_demo_user()
        serializer.save(user=user)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in a conversation"""
        conversation = self.get_object()
        messages = conversation.messages.all().order_by('timestamp')
        
        # Pagination
        paginator = StandardResultsSetPagination()
        result_page = paginator.paginate_queryset(messages, request)
        
        serializer = MessageSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in this conversation"""
        conversation = self.get_object()
        
        # Validate request data
        serializer = LLMChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        provider = serializer.validated_data.get('provider')
        language = serializer.validated_data.get('language', 'en')
        
        try:
            # Save user message
            ConversationService.save_message_to_session(
                request=request,
                conversation_id=str(conversation.uuid),
                role='user',
                content=user_message
            )
            
            # Get conversation history (last 10 messages)
            history = list(conversation.messages.all().order_by('-timestamp')[:10])
            history.reverse()  # Reverse to get chronological order
            
            # Generate LLM response using Django's async_to_sync
            bot_response, metadata = async_to_sync(LLMManager.generate_chat_response)(
                user_message=user_message,
                conversation_history=history,
                provider=provider,
                language=language
            )
            
            # Save bot message
            bot_message = ConversationService.save_message_to_session(
                request=request,
                conversation_id=str(conversation.uuid),
                role='bot',
                content=bot_response,
                metadata=metadata
            )
            
            # Return response
            response_serializer = LLMChatResponseSerializer({
                'response': bot_response,
                'conversation_id': conversation.uuid,
                'message_id': bot_message.uuid,
                'timestamp': bot_message.timestamp,
                'provider': metadata.get('provider', 'unknown'),
                'model': metadata.get('model', 'unknown'),
                'response_time': metadata.get('response_time', 0),
                'tokens_used': metadata.get('tokens_used'),
                'metadata': metadata
            })
            
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except LLMError as e:
            logger.error(f"LLM error in conversation {conversation.uuid}: {e}")
            return Response(
                {'error': 'Failed to generate response', 'details': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error in conversation {conversation.uuid}: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def analyze(self, request, pk=None):
        """Get LangExtract analysis for this conversation"""
        conversation = self.get_object()
        
        try:
            # Get conversation messages
            messages = list(conversation.messages.all().order_by('timestamp'))
            message_data = [
                {
                    'role': msg.sender_type,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]
            
            # Run LangExtract analysis
            lang_extract = LangExtractService()
            analysis = lang_extract.analyze_conversation(message_data)
            
            return Response({
                'conversation_id': conversation.uuid,
                'analysis': analysis,
                'message_count': len(messages),
                'analysis_timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Analysis error for conversation {conversation.uuid}: {e}")
            return Response(
                {'error': 'Analysis failed', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user's conversation statistics"""
        user_conversations = self.get_queryset()
        
        total_conversations = user_conversations.count()
        active_conversations = user_conversations.filter(is_active=True).count()
        total_messages = Message.objects.filter(
            conversation__in=user_conversations
        ).count()
        
        avg_messages = (
            total_messages / total_conversations 
            if total_conversations > 0 else 0
        )
        
        # Get recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_conversations = user_conversations.filter(updated_at__gte=week_ago)
        
        stats_data = {
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'total_messages': total_messages,
            'avg_messages_per_conversation': round(avg_messages, 2),
            'user_satisfaction_rating': 4.2,  # TODO: Calculate from feedback
            'popular_providers': ['openai', 'gemini'],  # TODO: Calculate from usage
            'recent_activity': list(recent_conversations.values(
                'uuid', 'title', 'updated_at'
            )[:10])
        }
        
        serializer = ConversationStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export conversations in various formats"""
        serializer = ConversationExportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        export_format = serializer.validated_data['format']
        include_metadata = serializer.validated_data['include_metadata']
        date_from = serializer.validated_data.get('date_from')
        date_to = serializer.validated_data.get('date_to')
        
        # Filter conversations
        conversations = self.get_queryset()
        if date_from:
            conversations = conversations.filter(created_at__gte=date_from)
        if date_to:
            conversations = conversations.filter(created_at__lte=date_to)
        
        try:
            # Generate export data
            export_data = []
            for conv in conversations:
                conv_data = {
                    'id': str(conv.uuid),
                    'title': conv.get_title(),
                    'created_at': conv.created_at.isoformat(),
                    'messages': []
                }
                
                for msg in conv.messages.all().order_by('timestamp'):
                    msg_data = {
                        'content': msg.content,
                        'sender': msg.sender_type,
                        'timestamp': msg.timestamp.isoformat()
                    }
                    if include_metadata:
                        msg_data.update({
                            'feedback': msg.feedback,
                            'llm_model': msg.llm_model_used,
                            'response_time': msg.response_time
                        })
                    conv_data['messages'].append(msg_data)
                
                export_data.append(conv_data)
            
            # Return appropriate format
            if export_format == 'json':
                response = JsonResponse({'conversations': export_data})
                response['Content-Disposition'] = 'attachment; filename="conversations.json"'
            elif export_format == 'csv':
                # TODO: Implement CSV export
                return Response({'error': 'CSV export not yet implemented'})
            else:  # txt
                # TODO: Implement TXT export
                return Response({'error': 'TXT export not yet implemented'})
            
            return response
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageViewSet(ModelViewSet):
    """
    ViewSet for managing messages
    Provides CRUD operations for messages with filtering
    """
    
    serializer_class = MessageSerializer
    permission_classes = [permissions.AllowAny]  # For development
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Filter messages by user's conversations"""
        # Get user (demo user for anonymous requests)
        if self.request.user.is_authenticated:
            user = self.request.user
        else:
            from django.contrib.auth.models import User
            user, created = User.objects.get_or_create(
                username='demo_user',
                defaults={
                    'email': 'demo@datapro.solutions',
                    'first_name': 'Demo',
                    'last_name': 'User',
                    'is_active': True,
                }
            )
        
        user_conversations = Conversation.objects.filter(user=user)
        queryset = Message.objects.filter(
            conversation__in=user_conversations
        ).order_by('-timestamp')
        
        # Filter by conversation if specified
        conversation_id = self.request.query_params.get('conversation')
        if conversation_id:
            queryset = queryset.filter(conversation__uuid=conversation_id)
        
        # Filter by sender type
        sender_type = self.request.query_params.get('sender_type')
        if sender_type in ['user', 'bot']:
            queryset = queryset.filter(sender_type=sender_type)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(timestamp__gte=date_from)
        if date_to:
            queryset = queryset.filter(timestamp__lte=date_to)
        
        return queryset
    
    def get_serializer_class(self):
        """Use different serializers for create vs other actions"""
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def perform_create(self, serializer):
        """Handle message creation"""
        # Get the conversation from the request data
        conversation_id = self.request.data.get('conversation')
        if not conversation_id:
            raise ValidationError("Conversation ID is required")
        
        # Get conversation and verify user access
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            raise ValidationError("Conversation not found")
        
        # Get current user (demo user for anonymous requests)
        if self.request.user.is_authenticated:
            current_user = self.request.user
        else:
            from django.contrib.auth.models import User
            current_user, created = User.objects.get_or_create(
                username='demo_user',
                defaults={
                    'email': 'demo@datapro.solutions',
                    'first_name': 'Demo',
                    'last_name': 'User',
                    'is_active': True,
                }
            )
        
        # Verify user owns the conversation
        if conversation.user != current_user:
            raise PermissionDenied("You don't have permission to add messages to this conversation")
        
        # Save the message
        serializer.save(conversation=conversation)
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, pk=None):
        """Submit feedback for a message"""
        message = self.get_object()
        
        # Check if message belongs to user's conversation (handle anonymous users)
        if request.user.is_authenticated:
            current_user = request.user
        else:
            from django.contrib.auth.models import User
            current_user, created = User.objects.get_or_create(
                username='demo_user',
                defaults={
                    'email': 'demo@datapro.solutions',
                    'first_name': 'Demo',
                    'last_name': 'User',
                    'is_active': True,
                }
            )
        
        if message.conversation.user != current_user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = MessageFeedbackSerializer(message, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LLMChatAPIView(APIView):
    """
    API endpoint for direct LLM chat
    Handles single message interactions without conversation context
    """
    
    # For development: allow anonymous access, in production should be IsAuthenticated
    permission_classes = [permissions.AllowAny]
    
    def get_or_create_demo_user(self):
        """Get or create a demo user for anonymous access"""
        demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@datapro.solutions',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )
        return demo_user

    def post(self, request):
        """Send message to LLM and get response"""
        serializer = LLMChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        print(user_message);
        conversation_id = serializer.validated_data.get('conversation_id')
        provider = serializer.validated_data.get('provider')
        language = serializer.validated_data.get('language', 'en')
        
        
        try:
            # Get user (use demo user for anonymous requests)
            user = request.user if request.user.is_authenticated else self.get_or_create_demo_user()
            
            # Get or create conversation
            if conversation_id:
                conversation = get_object_or_404(
                    Conversation,
                    uuid=conversation_id,
                    user=user
                )
            else:
                conversation = Conversation.objects.create(user=user)
            
            # Get conversation history (last 10 messages)
            history = list(conversation.messages.all().order_by('-timestamp')[:10])
            history.reverse()  # Reverse to get chronological order
            
            # Generate LLM response using Django's async_to_sync
            bot_response, metadata = async_to_sync(LLMManager.generate_chat_response)(
                user_message=user_message,
                conversation_history=history,
                provider=provider,
                language=language
            )
            
            # Save messages
            user_msg = Message.objects.create(
                conversation=conversation,
                content=user_message,
                sender_type='user'
            )
            
            bot_msg = Message.objects.create(
                conversation=conversation,
                content=bot_response,
                sender_type='bot',
                llm_model_used=metadata.get('model'),
                response_time=metadata.get('response_time'),
                tokens_used=metadata.get('tokens_used'),
                metadata=metadata
            )
            
            # Return response
            response_data = {
                'response': bot_response,
                'conversation_id': conversation.uuid,
                'message_id': bot_msg.uuid,
                'timestamp': bot_msg.timestamp,
                'provider': metadata.get('provider', 'unknown'),
                'model': metadata.get('model', 'unknown'),
                'response_time': metadata.get('response_time', 0),
                'tokens_used': metadata.get('tokens_used'),
                'metadata': metadata
            }
            
            response_serializer = LLMChatResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            return Response(
                {'error': 'Failed to generate response', 'details': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSessionViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for viewing user sessions
    Provides read-only access to session data
    """
    
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Filter sessions by current user"""
        return UserSession.objects.filter(user=self.request.user).order_by('-started_at')


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def conversation_search(request):
    """
    Search conversations by content
    """
    query = request.query_params.get('q', '').strip()
    if not query:
        return Response({'error': 'Query parameter "q" is required'}, status=400)
    
    # Search in conversation messages
    user_conversations = Conversation.objects.filter(user=request.user)
    matching_conversations = user_conversations.filter(
        Q(messages__content__icontains=query) |
        Q(title__icontains=query)
    ).distinct().order_by('-updated_at')
    
    # Paginate results
    paginator = StandardResultsSetPagination()
    result_page = paginator.paginate_queryset(matching_conversations, request)
    
    serializer = ConversationListSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def bulk_message_create(request):
    """
    Create multiple messages at once
    """
    serializer = BulkMessageCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    messages_data = serializer.validated_data['messages']
    conversation_id = serializer.validated_data.get('conversation_id')
    
    try:
        # Get or create conversation
        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                uuid=conversation_id,
                user=request.user
            )
        else:
            conversation = Conversation.objects.create(user=request.user)
        
        # Create messages
        created_messages = []
        for msg_data in messages_data:
            message = Message.objects.create(
                conversation=conversation,
                content=msg_data['content'],
                sender_type=msg_data['sender_type'],
                file_attachment=msg_data.get('file_attachment')
            )
            created_messages.append(message)
        
        # Return created messages
        serializer = MessageSerializer(created_messages, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Bulk message creation error: {e}")
        return Response(
            {'error': 'Failed to create messages'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def health_check(request):
    """
    API health check endpoint
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'user': request.user.username,
        'version': '1.0.0'
    })