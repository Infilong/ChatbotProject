"""
WebSocket consumers for real-time chat functionality
"""

import json
import logging
from typing import Dict, Any
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from .models import Conversation, Message, UserSession
from .llm_services import LLMManager, LLMError

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat with LLM integration"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_name = f"chat_{self.scope['user'].id if self.scope['user'].is_authenticated else 'anonymous'}"
        self.room_group_name = f"chat_{self.room_name}"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'status': 'connected',
            'message': 'Connected to chat system'
        }))
        
        logger.info(f"WebSocket connected: {self.room_name}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket disconnected: {self.room_name} (code: {close_code})")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing_indicator(data)
            elif message_type == 'feedback':
                await self.handle_message_feedback(data)
            else:
                await self.send_error("Unknown message type")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_error("Internal server error")
    
    async def handle_chat_message(self, data: Dict[str, Any]):
        """Handle chat message from user"""
        try:
            # Validate required fields
            user_message = data.get('message', '').strip()
            if not user_message:
                await self.send_error("Message cannot be empty")
                return
            
            # Check if user is authenticated
            if not self.scope['user'].is_authenticated:
                await self.send_error("Authentication required")
                return
            
            user = self.scope['user']
            conversation_id = data.get('conversation_id')
            
            # Get or create conversation
            conversation = await self.get_or_create_conversation(user, conversation_id)
            
            # Save user message
            user_msg = await self.save_message(
                conversation=conversation,
                content=user_message,
                sender_type='user'
            )
            
            # Send user message confirmation
            await self.send(text_data=json.dumps({
                'type': 'message',
                'sender': 'user',
                'message': user_message,
                'message_id': user_msg.id,
                'timestamp': user_msg.timestamp.isoformat(),
                'conversation_id': conversation.id
            }))
            
            # Send typing indicator for bot
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'sender': 'bot',
                'typing': True
            }))
            
            try:
                # Get conversation history for context
                history = await self.get_conversation_history(conversation)
                
                # Generate LLM response
                language = data.get('language', 'en')
                provider = data.get('provider')  # Optional specific provider
                
                bot_response, metadata = await LLMManager.generate_chat_response(
                    user_message=user_message,
                    conversation_history=history,
                    provider=provider,
                    language=language
                )
                
                # Save bot response
                bot_msg = await self.save_message(
                    conversation=conversation,
                    content=bot_response,
                    sender_type='bot',
                    metadata=metadata
                )
                
                # Stop typing indicator
                await self.send(text_data=json.dumps({
                    'type': 'typing',
                    'sender': 'bot',
                    'typing': False
                }))
                
                # Send bot response
                await self.send(text_data=json.dumps({
                    'type': 'message',
                    'sender': 'bot',
                    'message': bot_response,
                    'message_id': bot_msg.id,
                    'timestamp': bot_msg.timestamp.isoformat(),
                    'conversation_id': conversation.id,
                    'metadata': {
                        'provider': metadata.get('provider'),
                        'model': metadata.get('model'),
                        'response_time': metadata.get('response_time')
                    }
                }))
                
            except LLMError as e:
                logger.error(f"LLM error: {e}")
                await self.send_error_response(str(e))
            except Exception as e:
                logger.error(f"Unexpected error generating response: {e}")
                await self.send_error_response("Sorry, I'm having trouble generating a response right now.")
                
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await self.send_error("Failed to process message")
    
    async def handle_typing_indicator(self, data: Dict[str, Any]):
        """Handle typing indicator"""
        is_typing = data.get('typing', False)
        
        # Broadcast typing status to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_status',
                'sender': 'user',
                'typing': is_typing
            }
        )
    
    async def handle_message_feedback(self, data: Dict[str, Any]):
        """Handle user feedback on messages"""
        try:
            message_id = data.get('message_id')
            feedback_type = data.get('feedback')  # 'positive' or 'negative'
            
            if not message_id or feedback_type not in ['positive', 'negative']:
                await self.send_error("Invalid feedback data")
                return
            
            await self.update_message_feedback(message_id, feedback_type)
            
            await self.send(text_data=json.dumps({
                'type': 'feedback_received',
                'message_id': message_id,
                'feedback': feedback_type,
                'status': 'success'
            }))
            
        except Exception as e:
            logger.error(f"Error handling feedback: {e}")
            await self.send_error("Failed to record feedback")
    
    async def send_error(self, message: str):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    async def send_error_response(self, error_message: str):
        """Send error as bot response"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender': 'bot',
            'typing': False
        }))
        
        await self.send(text_data=json.dumps({
            'type': 'message',
            'sender': 'bot',
            'message': error_message,
            'timestamp': timezone.now().isoformat(),
            'is_error': True
        }))
    
    # Group message handlers
    async def typing_status(self, event):
        """Handle typing status broadcast"""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'sender': event['sender'],
            'typing': event['typing']
        }))
    
    # Database operations (async wrappers)
    @database_sync_to_async
    def get_or_create_conversation(self, user, conversation_id=None):
        """Get existing conversation or create new one"""
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=user)
                return conversation
            except Conversation.DoesNotExist:
                pass
        
        # Create new conversation
        conversation = Conversation.objects.create(user=user)
        return conversation
    
    @database_sync_to_async
    def save_message(self, conversation, content, sender_type, metadata=None):
        """Save message to database"""
        message = Message.objects.create(
            conversation=conversation,
            content=content,
            sender_type=sender_type,
            metadata=metadata or {},
            llm_model_used=metadata.get('model') if metadata else None,
            response_time=metadata.get('response_time') if metadata else None,
        )
        return message
    
    @database_sync_to_async
    def get_conversation_history(self, conversation, limit=10):
        """Get recent conversation history"""
        return list(
            conversation.messages.all()
            .order_by('-timestamp')[:limit]
            .reverse()
        )
    
    @database_sync_to_async
    def update_message_feedback(self, message_id, feedback_type):
        """Update message feedback"""
        try:
            message = Message.objects.get(id=message_id)
            message.feedback = feedback_type
            message.save(update_fields=['feedback'])
        except Message.DoesNotExist:
            logger.error(f"Message {message_id} not found for feedback update")


class AdminChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for admin monitoring and intervention"""
    
    async def connect(self):
        """Handle admin WebSocket connection"""
        # Check if user is admin
        if not (self.scope['user'].is_authenticated and self.scope['user'].is_staff):
            await self.close()
            return
        
        self.room_group_name = "admin_chat_monitor"
        
        # Join admin monitoring group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'admin_connected',
            'message': 'Connected to admin chat monitoring'
        }))
        
        logger.info(f"Admin WebSocket connected: {self.scope['user'].username}")
    
    async def disconnect(self, close_code):
        """Handle admin WebSocket disconnection"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"Admin WebSocket disconnected: {self.scope['user'].username}")
    
    async def receive(self, text_data):
        """Handle admin commands"""
        try:
            data = json.loads(text_data)
            command = data.get('command')
            
            if command == 'get_active_chats':
                await self.send_active_chats()
            elif command == 'intervene':
                await self.handle_admin_intervention(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Unknown command'
                }))
                
        except Exception as e:
            logger.error(f"Error handling admin command: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Command processing failed'
            }))
    
    async def send_active_chats(self):
        """Send list of active chat sessions"""
        # This would query active conversations and send summary
        # Implementation depends on specific admin requirements
        pass
    
    async def handle_admin_intervention(self, data):
        """Handle admin intervention in chat"""
        # This would allow admins to send messages or take over conversations
        # Implementation depends on specific admin requirements
        pass