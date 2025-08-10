"""Custom exceptions for chat functionality"""

from typing import Optional, Dict, Any


class ChatBaseException(Exception):
    """Base exception for chat-related errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization"""
        return {
            'error': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'exception_type': self.__class__.__name__
        }


class LLMProviderException(ChatBaseException):
    """Exception for LLM provider-related errors"""
    
    def __init__(self, provider: str, message: str, api_error: Optional[str] = None):
        super().__init__(
            message=f"LLM Provider '{provider}' error: {message}",
            error_code="LLM_PROVIDER_ERROR",
            details={'provider': provider, 'api_error': api_error}
        )
        self.provider = provider
        self.api_error = api_error


class ConversationException(ChatBaseException):
    """Exception for conversation management errors"""
    
    def __init__(self, conversation_id: str, message: str):
        super().__init__(
            message=f"Conversation '{conversation_id}': {message}",
            error_code="CONVERSATION_ERROR",
            details={'conversation_id': conversation_id}
        )
        self.conversation_id = conversation_id


class KnowledgeBaseException(ChatBaseException):
    """Exception for knowledge base related errors"""
    
    def __init__(self, message: str, document_id: Optional[str] = None):
        super().__init__(
            message=f"Knowledge Base error: {message}",
            error_code="KNOWLEDGE_BASE_ERROR",
            details={'document_id': document_id} if document_id else {}
        )
        self.document_id = document_id


class APIConfigurationException(ChatBaseException):
    """Exception for API configuration errors"""
    
    def __init__(self, provider: str, message: str):
        super().__init__(
            message=f"API Configuration for '{provider}': {message}",
            error_code="API_CONFIG_ERROR",
            details={'provider': provider}
        )
        self.provider = provider


class SessionException(ChatBaseException):
    """Exception for session management errors"""
    
    def __init__(self, user_id: int, message: str):
        super().__init__(
            message=f"Session error for user {user_id}: {message}",
            error_code="SESSION_ERROR",
            details={'user_id': user_id}
        )
        self.user_id = user_id


class ValidationException(ChatBaseException):
    """Exception for data validation errors"""
    
    def __init__(self, field: str, message: str, value: Any = None):
        super().__init__(
            message=f"Validation error for '{field}': {message}",
            error_code="VALIDATION_ERROR",
            details={'field': field, 'value': str(value) if value is not None else None}
        )
        self.field = field
        self.value = value
