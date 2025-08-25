"""
REST API views for chat application
Provides comprehensive API endpoints for frontend integration
"""

import json
import logging
import uuid
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
# Removed demo user fallback - all APIs now require proper authentication

logger = logging.getLogger(__name__)


def update_customer_session_activity(user):
    """
    Helper function to update customer session last activity when users send messages
    Simple tracking: only updates last_activity timestamp when user is active
    """
    try:
        # Get or create active session for the user
        active_session = UserSession.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if not active_session:
            # Create new session if none exists
            active_session = UserSession.objects.create(
                user=user,
                session_id=str(uuid.uuid4()),
                is_active=True
            )
            logger.info(f"Created new Customer Session for user activity: {active_session.session_id}")
        else:
            # Update last_activity (auto_now=True will handle this automatically on save)
            active_session.save()
            logger.info(f"Updated Customer Session last activity: {active_session.session_id}")
        
        return active_session
        
    except Exception as e:
        logger.error(f"Error updating customer session activity: {e}")
        return None



class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API endpoints"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationViewSet(ModelViewSet):
    """
    ViewSet for managing conversations
    Provides CRUD operations for conversations with UUID-based lookup
    """
    
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]  # Require authentication
    pagination_class = StandardResultsSetPagination
    lookup_field = 'uuid'  # Use UUID for URL lookups instead of pk
    
    def get_queryset(self):
        """Filter conversations by authenticated user only"""
        if not self.request.user.is_authenticated:
            return Conversation.objects.none()  # Return empty queryset for unauthenticated users
        
        return Conversation.objects.filter(user=self.request.user).order_by('-updated_at')
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer
    
    def perform_create(self, serializer):
        """Set authenticated user when creating conversation"""
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required to create conversations")
        
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, uuid=None):
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
            # Check for duplicate user message in the last 5 minutes to prevent resend duplicates
            recent_cutoff = timezone.now() - timedelta(minutes=5)
            existing_msg = conversation.messages.filter(
                content=user_message,
                sender_type='user',
                timestamp__gte=recent_cutoff
            ).first()
            
            if existing_msg:
                # Message already exists - check if it has a bot response
                bot_response_exists = conversation.messages.filter(
                    sender_type='bot',
                    timestamp__gte=existing_msg.timestamp
                ).exists()
                
                if bot_response_exists:
                    # Complete conversation already exists, return the existing bot response
                    latest_bot_msg = conversation.messages.filter(
                        sender_type='bot',
                        timestamp__gte=existing_msg.timestamp
                    ).first()
                    
                    response_serializer = LLMChatResponseSerializer({
                        'response': latest_bot_msg.content,
                        'conversation_id': conversation.uuid,
                        'message_id': latest_bot_msg.uuid,
                        'timestamp': latest_bot_msg.timestamp,
                        'provider': latest_bot_msg.metadata.get('provider', 'unknown') if latest_bot_msg.metadata else 'unknown',
                        'model': latest_bot_msg.llm_model_used or 'unknown',
                        'response_time': latest_bot_msg.response_time or 0,
                        'tokens_used': latest_bot_msg.tokens_used,
                        'metadata': latest_bot_msg.metadata or {},
                        'note': 'Returned existing response (duplicate message detected)'
                    })
                    
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                else:
                    # User message exists but no bot response - this is a retry after API error
                    user_msg = existing_msg
                    print(f"ConversationViewSet: Retrying LLM call for existing message: {user_msg.id}")
            else:
                # Save new user message
                print(f"*** ConversationViewSet: About to call ConversationService.save_message_to_session ***")
                print(f"Request user: {request.user.username} (ID: {request.user.id})")
                print(f"Conversation UUID: {conversation.uuid}")
                print(f"User message: {user_message}")
                
                user_msg = ConversationService.save_message_to_session(
                    request=request,
                    conversation_id=str(conversation.uuid),
                    role='user',
                    content=user_message
                )
                
                print(f"*** ConversationViewSet: ConversationService returned message with ID: {getattr(user_msg, 'id', 'NO_ID')} ***")
            
            # Get conversation history (last 10 messages)
            history = list(conversation.messages.all().order_by('-timestamp')[:10])
            history.reverse()  # Reverse to get chronological order
            
            # Generate LLM response using Django's async_to_sync with proper context
            bot_response, metadata = async_to_sync(LLMManager.generate_chat_response)(
                user_message=user_message,
                conversation_history=history,
                provider=provider,
                language=language,
                conversation_id=conversation.id,
                message_id=user_msg.id
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
            error_msg = str(e)
            logger.error(f"LLM error in conversation {conversation.uuid}: {e}")
            
            # Handle rate limit errors with appropriate status code
            if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                return Response(
                    {'error': 'API rate limit exceeded', 'details': error_msg},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                return Response(
                    {'error': 'Failed to generate response', 'details': error_msg},
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
        """Get LangExtract analysis for this conversation (non-blocking)"""
        conversation = self.get_object()
        
        try:
            # Check if analysis already exists from background processing
            if conversation.langextract_analysis and conversation.langextract_analysis != {}:
                # Return existing analysis
                return Response({
                    'conversation_id': conversation.uuid,
                    'analysis': conversation.langextract_analysis,
                    'message_count': conversation.total_messages,
                    'status': 'completed',
                    'processing_mode': conversation.langextract_analysis.get('processing_mode', 'background'),
                    'analysis_timestamp': conversation.langextract_analysis.get('processed_at', 
                                                                             conversation.updated_at.isoformat())
                })
            else:
                # Analysis not available - queue it for background processing
                from core.services.async_analysis_service import async_analysis_service
                
                # Schedule analysis with immediate processing (no delay for manual requests)
                task_id = async_analysis_service.schedule_conversation_analysis(
                    conversation, 
                    delay_seconds=0  # Immediate processing for manual analysis requests
                )
                
                logger.info(f"Queued immediate analysis for conversation {conversation.uuid}, task ID: {task_id}")
                
                # Return processing status
                return Response({
                    'conversation_id': conversation.uuid,
                    'status': 'processing',
                    'message': 'Analysis has been queued for processing. Check back in a few seconds.',
                    'task_id': task_id,
                    'message_count': conversation.total_messages,
                    'estimated_completion': 'within 10 seconds'
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
    Provides CRUD operations for messages with UUID-based lookup
    """
    
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]  # Require authentication
    pagination_class = StandardResultsSetPagination
    lookup_field = 'uuid'  # Use UUID for URL lookups instead of pk
    
    def get_queryset(self):
        """Filter messages by authenticated user's conversations"""
        if not self.request.user.is_authenticated:
            return Message.objects.none()  # Return empty queryset for unauthenticated users
        
        user_conversations = Conversation.objects.filter(user=self.request.user)
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
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required to create messages")
        
        # Get the conversation from the request data
        conversation_id = self.request.data.get('conversation')
        if not conversation_id:
            raise ValidationError("Conversation ID is required")
        
        # Get conversation and verify user access
        try:
            conversation = Conversation.objects.get(uuid=conversation_id)
        except Conversation.DoesNotExist:
            raise ValidationError("Conversation not found")
        
        # Verify authenticated user owns the conversation
        if conversation.user != self.request.user:
            raise PermissionDenied("You don't have permission to add messages to this conversation")
        
        # Save the message
        serializer.save(conversation=conversation)
    
    @action(detail=True, methods=['post'])
    def feedback(self, request, uuid=None):
        """Submit feedback for a message"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        message = self.get_object()
        
        # Check if message belongs to authenticated user's conversation
        if message.conversation.user != request.user:
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
    
    # Require authentication for message creation
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Send message to LLM and get response"""
        # DEBUG: ENTRY - This method was called
        import sys
        print("=" * 80, file=sys.stderr)
        print("ENTRY ENTRY ENTRY - LLMChatAPIView.post() called!!!", file=sys.stderr)
        print(f"Request path = {request.path}", file=sys.stderr)
        print(f"Request method = {request.method}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        sys.stderr.flush()
        
        # DEBUG: Log authentication details
        print(f"DEBUG: request.user = {request.user}")
        print(f"DEBUG: request.user.is_authenticated = {request.user.is_authenticated}")
        print(f"DEBUG: request.user.id = {getattr(request.user, 'id', 'NO_ID')}")
        print(f"DEBUG: request.user.username = {getattr(request.user, 'username', 'NO_USERNAME')}")
        print(f"DEBUG: Authorization header = {request.headers.get('Authorization', 'NO_AUTH_HEADER')}")
        
        if not request.user.is_authenticated:
            print("DEBUG: User not authenticated, returning 401")
            print("=" * 60)
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        print(f"DEBUG: User IS authenticated! Proceeding with user {request.user.username} (ID: {request.user.id})")
        print("=" * 60)
        
        serializer = LLMChatRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user_message = serializer.validated_data['message']
        print(user_message);
        conversation_id = serializer.validated_data.get('conversation_id')
        provider = serializer.validated_data.get('provider')
        language = serializer.validated_data.get('language', 'en')
        
        
        try:
            # Use authenticated user only
            user = request.user
            print(f"DEBUG: Using user = {user} (ID: {user.id})")
            
            # Get or create conversation using UUID (industry best practice)
            if conversation_id:
                try:
                    # Try to get existing conversation by UUID
                    conversation = Conversation.objects.get(
                        uuid=conversation_id,
                        user=user
                    )
                    print(f"Continuing existing conversation: {conversation.uuid}")
                except Conversation.DoesNotExist:
                    print(f"Conversation {conversation_id} not found for user {user.username}")
                    # Return error if provided UUID doesn't exist - don't create new one
                    return Response(
                        {
                            'error': 'Conversation not found',
                            'details': f'No conversation found with ID {conversation_id}',
                            'conversation_id': conversation_id
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Check if user already has a recent conversation with the same message to prevent duplicate conversations
                recent_cutoff = timezone.now() - timedelta(minutes=5)
                existing_conversation = Conversation.objects.filter(
                    user=user,
                    created_at__gte=recent_cutoff,
                    messages__content=user_message,
                    messages__sender_type='user'
                ).first()
                
                if existing_conversation:
                    print(f"Found existing conversation with same message: {existing_conversation.uuid}")
                    conversation = existing_conversation
                else:
                    # Create new conversation only if no recent conversation with same message exists
                    print(f"DEBUG: About to create conversation with user = {user} (ID: {user.id}, username: {user.username})")
                    conversation = Conversation.objects.create(user=user)
                    print(f"DEBUG: Created conversation {conversation.uuid} with user {conversation.user.username} (ID: {conversation.user.id})")
                    
                    # Double check what's in the database
                    fresh_conv = Conversation.objects.get(uuid=conversation.uuid)
                    print(f"DEBUG: Fresh from DB - conversation {fresh_conv.uuid} belongs to {fresh_conv.user.username} (ID: {fresh_conv.user.id})")
                    
                    # Track user activity when starting new conversation
                    update_customer_session_activity(user)
            
            # Get conversation history (last 10 messages)
            history = list(conversation.messages.all().order_by('-timestamp')[:10])
            history.reverse()  # Reverse to get chronological order
            
            # Check for duplicate user message in the last 5 minutes to prevent resend duplicates
            recent_cutoff = timezone.now() - timedelta(minutes=5)
            existing_msg = conversation.messages.filter(
                content=user_message,
                sender_type='user',
                timestamp__gte=recent_cutoff
            ).first()
            
            if existing_msg:
                # Message already exists - check if it has a bot response
                bot_response_exists = conversation.messages.filter(
                    sender_type='bot',
                    timestamp__gte=existing_msg.timestamp
                ).exists()
                
                if bot_response_exists:
                    # Complete conversation already exists, return the existing bot response
                    latest_bot_msg = conversation.messages.filter(
                        sender_type='bot',
                        timestamp__gte=existing_msg.timestamp
                    ).first()
                    
                    response_data = {
                        'response': latest_bot_msg.content,
                        'conversation_id': conversation.uuid,
                        'message_id': latest_bot_msg.uuid,
                        'timestamp': latest_bot_msg.timestamp,
                        'provider': latest_bot_msg.metadata.get('provider', 'unknown') if latest_bot_msg.metadata else 'unknown',
                        'model': latest_bot_msg.llm_model_used or 'unknown',
                        'response_time': latest_bot_msg.response_time or 0,
                        'tokens_used': latest_bot_msg.tokens_used,
                        'metadata': latest_bot_msg.metadata or {},
                        'note': 'Returned existing response (duplicate message detected)'
                    }
                    
                    response_serializer = LLMChatResponseSerializer(response_data)
                    return Response(response_serializer.data, status=status.HTTP_200_OK)
                else:
                    # User message exists but no bot response - this is a retry after API error
                    user_msg = existing_msg
                    print(f"Retrying LLM call for existing message: {user_msg.id}")
            else:
                # New message - save user message first to get its ID for document usage tracking
                user_msg = Message(
                    conversation=conversation,
                    content=user_message,
                    sender_type='user'
                )
                user_msg.save()  # Use save() to trigger signals for analysis
                
                # Track user activity when sending message
                update_customer_session_activity(user)
            
            # Generate LLM response using Django's async_to_sync with proper context
            bot_response, metadata = async_to_sync(LLMManager.generate_chat_response)(
                user_message=user_message,
                conversation_history=history,
                provider=provider,
                language=language,
                conversation_id=conversation.id,
                message_id=user_msg.id
            )
            
            # Create bot message
            bot_msg = Message(
                conversation=conversation,
                content=bot_response,
                sender_type='bot',
                llm_model_used=metadata.get('model'),
                response_time=metadata.get('response_time'),
                tokens_used=metadata.get('tokens_used'),
                metadata=metadata
            )
            bot_msg.save()  # Use save() to trigger signals
            
            # Note: We don't track bot responses, only user activity
            
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
            error_msg = str(e)
            logger.error(f"LLM error: {e}")
            
            # Handle rate limit errors with appropriate status code
            if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                return Response(
                    {'error': 'API rate limit exceeded', 'details': error_msg},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                return Response(
                    {'error': 'Failed to generate response', 'details': error_msg},
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
    Search conversations by content - requires authentication
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    query = request.query_params.get('q', '').strip()
    if not query:
        return Response({'error': 'Query parameter "q" is required'}, status=400)
    
    # Search in authenticated user's conversation messages only
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
            message = Message(
                conversation=conversation,
                content=msg_data['content'],
                sender_type=msg_data['sender_type'],
                file_attachment=msg_data.get('file_attachment')
            )
            message.save()  # Use save() to trigger signals
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


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def test_debug_endpoint(request):
    """
    Test debug endpoint to verify code execution
    """
    print("=" * 80)
    print("TEST DEBUG ENDPOINT CALLED!")
    print("=" * 80)
    return Response({
        'status': 'debug_endpoint_working',
        'timestamp': timezone.now().isoformat(),
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])  # For demo purposes
def automatic_analysis_status(request):
    """
    Get status of automatic analysis system
    """
    try:
        from core.services.automatic_analysis_service import automatic_analysis_service
        
        # Get analysis statistics
        total_conversations = Conversation.objects.count()
        analyzed_conversations = Conversation.objects.filter(
            langextract_analysis__isnull=False
        ).count()
        pending_conversations = total_conversations - analyzed_conversations
        
        # Get recent activity
        recent_analyzed = Conversation.objects.filter(
            langextract_analysis__isnull=False,
            updated_at__gte=timezone.now() - timezone.timedelta(hours=24)
        ).count()
        
        return Response({
            'status': 'active',
            'analysis_statistics': {
                'total_conversations': total_conversations,
                'analyzed_conversations': analyzed_conversations,
                'pending_conversations': pending_conversations,
                'analyzed_last_24h': recent_analyzed,
                'analysis_percentage': round((analyzed_conversations / total_conversations * 100) if total_conversations > 0 else 0, 1)
            },
            'automatic_analysis_config': {
                'min_messages_for_analysis': automatic_analysis_service.MIN_MESSAGES_FOR_ANALYSIS,
                'analysis_delay_minutes': automatic_analysis_service.ANALYSIS_DELAY_MINUTES,
                'max_analysis_delay_hours': automatic_analysis_service.MAX_ANALYSIS_DELAY_HOURS
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # For demo purposes
def trigger_automatic_analysis(request):
    """
    Manually trigger automatic analysis for all pending conversations
    """
    try:
        from core.services.automatic_analysis_service import automatic_analysis_service
        import asyncio
        
        # Run the batch analysis
        result = asyncio.run(automatic_analysis_service.analyze_pending_conversations())
        
        return Response({
            'status': 'success',
            'message': f"Analysis completed: {result['analyzed_count']} analyzed, {result['skipped_count']} skipped",
            'details': result,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual trigger of automatic analysis failed: {e}")
        return Response({
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def message_analysis_status(request):
    """
    Get status of message analysis system (now using simple direct processing)
    """
    try:
        from core.services.message_analysis_service import message_analysis_service
        
        # Get analysis statistics from the message analysis service
        stats = message_analysis_service.get_analysis_stats()
        
        return Response({
            'analysis_system': {
                'service_type': 'direct_processing',
                'queue_based': False,
                'background_workers': False,
                'admin_freeze_prevention': True,
                'database_transaction_safety': True
            },
            'database_statistics': {
                'total_user_messages': stats.get('total_user_messages', 0),
                'analyzed_messages': stats.get('analyzed_messages', 0),
                'pending_messages': stats.get('pending_messages', 0),
                'analysis_percentage': stats.get('analysis_percentage', 0.0)
            },
            'analysis_method': {
                'llm_provider': 'LangExtract + Gemini',
                'model': 'gemini-2.5-flash',
                'processing_mode': 'direct_signal_based',
                'async_database_ops': True,
                'service_handler': stats.get('service_type', 'unknown')
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)