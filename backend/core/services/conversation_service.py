import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from django.http import JsonResponse
from django.contrib.auth.models import User
from datetime import datetime


class ConversationService:
    """Service for managing admin chat conversations and session data"""
    
    @staticmethod
    def generate_conversation_id() -> str:
        """Generate a unique conversation ID"""
        return f"conv_{uuid.uuid4().hex[:8]}"
    
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
        """Get chat history for a specific conversation"""
        session_key, _ = cls.get_session_keys(request.user.id, conversation_id)
        return request.session.get(session_key, [])
    
    @classmethod
    def get_all_conversations(cls, request) -> List[Dict[str, Any]]:
        """Get all conversations for the current user"""
        _, conversations_key = cls.get_session_keys(request.user.id)
        return request.session.get(conversations_key, [])
    
    @classmethod
    def save_message_to_session(cls, request, conversation_id: str, role: str, 
                              content: str, metadata: Optional[Dict] = None) -> None:
        """Save a message to session storage"""
        session_key, conversations_key = cls.get_session_keys(request.user.id, conversation_id)
        
        # Get or create conversation history
        history = request.session.get(session_key, [])
        
        # Create message object
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        history.append(message)
        request.session[session_key] = history
        
        # Update conversation metadata
        conversations = request.session.get(conversations_key, [])
        conversation_exists = False
        
        for conv in conversations:
            if conv['id'] == conversation_id:
                conv['last_updated'] = datetime.now().isoformat()
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
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'message_count': len(history)
            })
        
        request.session[conversations_key] = conversations
        request.session.modified = True
    
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
