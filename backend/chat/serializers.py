"""
Serializers for chat application REST API
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Conversation, Message, UserSession, APIConfiguration, AdminPrompt


# Secure Chat API Serializers
class ChatRequestSerializer(serializers.Serializer):
    """Validates incoming chat requests"""
    message = serializers.CharField(
        max_length=2000,
        min_length=1,
        required=True,
        help_text=_("User message content")
    )
    conversation_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=_("Optional conversation UUID to continue existing conversation")
    )
    provider = serializers.ChoiceField(
        choices=['openai', 'gemini', 'claude'],
        default='gemini',
        required=False,
        help_text=_("LLM provider to use")
    )
    language = serializers.ChoiceField(
        choices=['en', 'ja'],
        default='en',
        required=False,
        help_text=_("Response language")
    )


class ChatResponseSerializer(serializers.Serializer):
    """Formats chat response data"""
    conversation_id = serializers.UUIDField(
        help_text=_("Conversation UUID")
    )
    message_id = serializers.UUIDField(
        help_text=_("Message UUID")
    )
    response = serializers.CharField(
        help_text=_("LLM response content")
    )
    timestamp = serializers.DateTimeField(
        help_text=_("Response timestamp")
    )
    provider = serializers.CharField(
        help_text=_("LLM provider used")
    )
    model = serializers.CharField(
        help_text=_("Specific model used")
    )
    response_time = serializers.FloatField(
        help_text=_("Response time in seconds")
    )
    tokens_used = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=_("Tokens consumed")
    )
    metadata = serializers.DictField(
        required=False,
        help_text=_("Additional response metadata")
    )


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model"""
    
    user = UserSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'uuid', 'user', 'title', 'created_at', 'updated_at',
            'is_active', 'total_messages', 'satisfaction_score', 'langextract_analysis', 
            'message_count', 'last_message_time'
        ]
        read_only_fields = [
            'id', 'uuid', 'user', 'created_at', 'updated_at', 'message_count', 'total_messages'
        ]
    
    
    def get_message_count(self, obj):
        """Get total message count"""
        return obj.messages.count()
    
    def get_last_message_time(self, obj):
        """Get last message timestamp"""
        last_msg = obj.messages.order_by('-timestamp').first()
        return last_msg.timestamp if last_msg else obj.created_at


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    
    conversation_title = serializers.CharField(source='conversation.get_title', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'uuid', 'conversation', 'conversation_title', 'content', 
            'sender_type', 'timestamp', 'feedback', 'file_attachment',
            'metadata', 'response_time', 'llm_model_used', 'tokens_used'
        ]
        read_only_fields = [
            'id', 'uuid', 'timestamp', 'response_time', 'llm_model_used', 
            'tokens_used', 'conversation_title'
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
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
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
    conversation_id = serializers.UUIDField()
    message_id = serializers.UUIDField()
    timestamp = serializers.DateTimeField()
    provider = serializers.CharField()
    model = serializers.CharField()
    response_time = serializers.FloatField()
    tokens_used = serializers.IntegerField(required=False)
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


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists"""
    
    preview_text = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ['id', 'uuid', 'title', 'preview_text', 'message_count', 'updated_at']
    
    def get_preview_text(self, obj):
        """Get preview from first user message"""
        first_msg = obj.messages.filter(sender_type='user').first()
        if first_msg and first_msg.content:
            return first_msg.content[:100] + '...' if len(first_msg.content) > 100 else first_msg.content
        return "New conversation"
    
    def get_message_count(self, obj):
        """Get message count"""
        return obj.messages.count()


class ConversationStatsSerializer(serializers.Serializer):
    """Serializer for conversation statistics"""
    
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    avg_messages_per_conversation = serializers.FloatField()
    user_satisfaction_rating = serializers.FloatField()
    popular_providers = serializers.ListField()
    recent_activity = serializers.ListField()


class BulkMessageCreateSerializer(serializers.Serializer):
    """Serializer for bulk message operations"""
    
    messages = MessageCreateSerializer(many=True)
    conversation_id = serializers.UUIDField(required=False)
    
    def validate_messages(self, value):
        """Validate messages list"""
        if len(value) > 50:
            raise serializers.ValidationError("Cannot create more than 50 messages at once")
        return value


class ConversationExportSerializer(serializers.Serializer):
    """Serializer for conversation export"""
    
    format = serializers.ChoiceField(choices=['json', 'csv', 'txt'], default='json')
    include_metadata = serializers.BooleanField(default=True)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        """Cross-field validation"""
        if data.get('date_from') and data.get('date_to'):
            if data['date_from'] >= data['date_to']:
                raise serializers.ValidationError("date_from must be before date_to")
        return data