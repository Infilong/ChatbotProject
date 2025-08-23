import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from chat.models import Conversation, Message


class ConversationService:
    """Service for managing admin chat conversations and session data"""
    
    @staticmethod
    def generate_conversation_id() -> str:
        """Generate a unique conversation ID"""
        return str(uuid.uuid4())  # Full UUID
    
    @staticmethod
    def get_session_keys(user_id: int, conversation_id: str = None) -> Tuple[str, str]:
        """Get session keys for conversation storage"""
        conversations_key = f"admin_conversations_{user_id}"
        if conversation_id:
            session_key = f"admin_conversation_{user_id}_{conversation_id}"
            return session_key, conversations_key
        return None, conversations_key
    
    @classmethod
    def get_conversation_history(cls, request, conversation_id: str) -> List[Dict[str, Any]]:
        """Get chat history for a specific conversation from database"""
        try:
            conversation = Conversation.objects.get(uuid=conversation_id, user=request.user)
            messages = Message.objects.filter(conversation=conversation).order_by('timestamp')
            return [cls._serialize_message(msg) for msg in messages]
        except Conversation.DoesNotExist:
            raise ValueError(f"Conversation not found: {conversation_id}")
        except Exception as e:
            raise Exception(f"Error fetching conversation history: {str(e)}")
    
    @classmethod
    def get_all_conversations(cls, request) -> List[Dict[str, Any]]:
        """Get all conversations for the current user from Django sessions"""
        _, conversations_key = cls.get_session_keys(request.user.id)
        return request.session.get(conversations_key, [])
    
    @classmethod
    def save_message_to_session(cls, request, conversation_id: str, role: str, 
                              content: str, metadata: Optional[Dict] = None) -> Message:
        """Save a message to database and return the Message instance"""
        try:
            print(f"ConversationService.save_message_to_session - request.user = {request.user} (ID: {getattr(request.user, 'id', 'NO_ID')})")
            print(f"ConversationService.save_message_to_session - conversation_id = {conversation_id}")
            
            # Get or create conversation (FIXED: Make conversation UUID user-specific)
            conversation, created = Conversation.objects.get_or_create(
                uuid=conversation_id,
                user=request.user,  # CRITICAL FIX: Include user in the get query
                defaults={}
            )
            print(f"ConversationService.save_message_to_session - conversation.user = {conversation.user.username} (ID: {conversation.user.id}), created = {created}")
            
            # Convert role to sender_type format
            sender_type = 'user' if role == 'user' else 'bot'
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                content=content,
                sender_type=sender_type,
                metadata=metadata or {},
                llm_model_used=metadata.get('model') if metadata else None,
                response_time=metadata.get('response_time') if metadata else None
            )
            
            # Update conversation title if needed (check for None or empty string)
            if (not conversation.title or conversation.title.strip() == '') and sender_type == 'user':
                conversation.title = content[:50] + ('...' if len(content) > 50 else '')
                conversation.save()
            
            return message
            
        except Exception as e:
            # Fallback to session-based storage for backward compatibility
            session_key, conversations_key = cls.get_session_keys(request.user.id, conversation_id)
            
            # Get or create conversation history
            history = request.session.get(session_key, [])
            
            # Create message object
            message = {
                'role': role,
                'content': content,
                'timestamp': timezone.now().isoformat(),
                'metadata': metadata or {}
            }
            
            history.append(message)
            request.session[session_key] = history
            
            # Update conversation metadata
            conversations = request.session.get(conversations_key, [])
            conversation_exists = False
            
            for conv in conversations:
                if conv['id'] == conversation_id:
                    conv['last_updated'] = timezone.now().isoformat()
                    conv['message_count'] = len(history)
                    # Update title from first user message if not set
                    if not conv.get('title') or conv['title'] == 'New Conversation':
                        first_user_message = next((msg for msg in history if msg['role'] == 'user'), None)
                        if first_user_message:
                            conv['title'] = first_user_message['content'][:40] + (
                                '...' if len(first_user_message['content']) > 40 else ''
                            )
                    conversation_exists = True
                    break
            
            if not conversation_exists:
                conversations.append({
                    'id': conversation_id,
                    'title': content[:40] + ('...' if len(content) > 40 else '') if role == 'user' else 'New Conversation',
                    'created_at': timezone.now().isoformat(),
                    'last_updated': timezone.now().isoformat(),
                    'message_count': len(history)
                })
            
            request.session[conversations_key] = conversations
            request.session.modified = True
            
            # Return a mock message object for session-based fallback
            class MockMessage:
                def __init__(self):
                    self.uuid = str(uuid.uuid4())
                    self.timestamp = timezone.now()
                    
            return MockMessage()
    
    @classmethod
    def create_new_conversation(cls, request) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = cls.generate_conversation_id()
        _, conversations_key = cls.get_session_keys(request.user.id)
        
        conversations = request.session.get(conversations_key, [])
        conversations.append({
            'id': conversation_id,
            'title': 'New Conversation',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'message_count': 0
        })
        
        request.session[conversations_key] = conversations
        request.session.modified = True
        
        return conversation_id
    
    @classmethod
    def delete_conversation(cls, request, conversation_id: str) -> bool:
        """Delete a conversation and return success status"""
        try:
            session_key, conversations_key = cls.get_session_keys(request.user.id, conversation_id)
            
            # Delete conversation history
            if session_key in request.session:
                del request.session[session_key]
            
            # Remove from conversations list
            conversations = request.session.get(conversations_key, [])
            conversations = [c for c in conversations if c['id'] != conversation_id]
            request.session[conversations_key] = conversations
            request.session.modified = True
            
            return True
        except Exception:
            return False
    
    @classmethod
    def clear_all_conversations(cls, request) -> bool:
        """Clear all conversations for the current user"""
        try:
            _, conversations_key = cls.get_session_keys(request.user.id)
            conversations = request.session.get(conversations_key, [])
            
            # Delete all conversation sessions
            for conv in conversations:
                session_key, _ = cls.get_session_keys(request.user.id, conv['id'])
                if session_key in request.session:
                    del request.session[session_key]
            
            # Clear conversations list
            request.session[conversations_key] = []
            request.session.modified = True
            
            return True
        except Exception:
            return False
    
    @classmethod
    def get_conversation_count(cls, request) -> int:
        """Get the number of conversations for the current user"""
        _, conversations_key = cls.get_session_keys(request.user.id)
        conversations = request.session.get(conversations_key, [])
        return len(conversations)
    
    @staticmethod
    def _serialize_message(message) -> Dict[str, Any]:
        """Serialize a Message model instance to dictionary format"""
        return {
            'id': str(message.uuid),
            'role': message.sender_type,
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'metadata': message.metadata or {},
            'feedback': message.feedback,
            'llm_model_used': message.llm_model_used,
            'response_time': message.response_time
        }
