"""
Serializers for chat application REST API
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model"""
    
    user = UserSerializer(read_only=True)
    title = serializers.CharField(read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'user', 'title', 'created_at', 'updated_at',
            'is_active', 'total_messages', 'satisfaction_score'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 'total_messages'
        ]
    
    def get_title(self, obj):
        """Get generated title for conversation"""
        return obj.get_title()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'content', 'sender_type', 
            'timestamp', 'feedback', 'file_attachment',
            'metadata', 'response_time', 'llm_model_used'
        ]
        read_only_fields = [
            'id', 'timestamp', 'response_time', 'llm_model_used'
        ]


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = ['content', 'sender_type', 'file_attachment']


class MessageFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for updating message feedback"""
    
    class Meta:
        model = Message
        fields = ['feedback']


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for UserSession model"""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'session_id', 'started_at', 'ended_at',
            'is_active', 'total_conversations', 'total_messages_sent',
            'average_response_time'
        ]
        read_only_fields = [
            'id', 'user', 'started_at', 'total_conversations',
            'total_messages_sent', 'average_response_time'
        ]


class APIConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for APIConfiguration model"""
    
    api_key = serializers.CharField(write_only=True)
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    
    class Meta:
        model = APIConfiguration
        fields = [
            'id', 'provider', 'provider_display', 'model_name',
            'is_active', 'created_at', 'updated_at', 'api_key'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True}
        }


class AdminPromptSerializer(serializers.ModelSerializer):
    """Serializer for AdminPrompt model"""
    
    created_by = UserSerializer(read_only=True)
    prompt_type_display = serializers.CharField(source='get_prompt_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    
    class Meta:
        model = AdminPrompt
        fields = [
            'id', 'name', 'prompt_type', 'prompt_type_display',
            'language', 'language_display', 'prompt_text', 'description',
            'is_active', 'is_default', 'usage_count', 'last_used',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usage_count', 'last_used', 'created_by',
            'created_at', 'updated_at'
        ]


class LLMChatRequestSerializer(serializers.Serializer):
    """Serializer for LLM chat requests"""
    
    message = serializers.CharField(max_length=2000)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    provider = serializers.ChoiceField(
        choices=['openai', 'gemini', 'claude'],
        required=False,
        allow_null=True
    )
    language = serializers.ChoiceField(
        choices=[('en', 'English'), ('ja', 'Japanese')],
        default='en'
    )
    max_tokens = serializers.IntegerField(default=1000, min_value=1, max_value=4000)
    temperature = serializers.FloatField(default=0.7, min_value=0.0, max_value=2.0)


class LLMChatResponseSerializer(serializers.Serializer):
    """Serializer for LLM chat responses"""
    
    response = serializers.CharField()
    conversation_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
    metadata = serializers.DictField()


class LLMTestRequestSerializer(serializers.Serializer):
    """Serializer for LLM test requests"""
    
    provider = serializers.ChoiceField(
        choices=['openai', 'gemini', 'claude']
    )


class LLMTestResponseSerializer(serializers.Serializer):
    """Serializer for LLM test responses"""
    
    status = serializers.CharField()
    provider = serializers.CharField()
    model = serializers.CharField(required=False)
    response = serializers.CharField(required=False)
    response_time = serializers.FloatField(required=False)
    error = serializers.CharField(required=False)