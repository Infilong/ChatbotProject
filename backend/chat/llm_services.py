"""
LLM API Integration Services
Integrates with OpenAI, Gemini, and Claude APIs using APIConfiguration model
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from django.conf import settings
from django.utils import timezone
from .models import APIConfiguration, AdminPrompt, Message

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM service errors"""
    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is invalid"""
    pass


class LLMAPIError(LLMError):
    """Raised when LLM API calls fail"""
    pass


class BaseLLMService:
    """Base class for LLM service implementations"""
    
    def __init__(self, api_config: APIConfiguration):
        self.config = api_config
        self.provider = api_config.provider
        self.api_key = api_config.api_key
        self.model_name = api_config.model_name
        
        if not self.config.is_active:
            raise LLMConfigurationError(f"{self.provider} API configuration is inactive")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate response from LLM
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
        
        Returns:
            Tuple of (response_text, metadata)
        """
        raise NotImplementedError("Subclasses must implement generate_response")
    
    def get_system_prompt(self, prompt_type: str = 'system', language: str = 'en') -> str:
        """Get system prompt from AdminPrompt model"""
        try:
            prompt = AdminPrompt.objects.filter(
                prompt_type=prompt_type,
                language=language,
                is_active=True,
                is_default=True
            ).first()
            
            if prompt:
                prompt.increment_usage()
                return prompt.prompt_text
            
            # Fallback to English if no language-specific prompt found
            if language != 'en':
                prompt = AdminPrompt.objects.filter(
                    prompt_type=prompt_type,
                    language='en',
                    is_active=True,
                    is_default=True
                ).first()
                
                if prompt:
                    prompt.increment_usage()
                    return prompt.prompt_text
            
            # Default system prompt if none found
            return self._get_default_system_prompt()
            
        except Exception as e:
            logger.error(f"Error retrieving system prompt: {e}")
            return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Default system prompt fallback"""
        return """You are a helpful AI assistant for DataPro Solutions' customer support system. 
        Provide accurate, helpful responses while maintaining a professional and friendly tone. 
        If you cannot answer a question, suggest escalating to human support."""


class OpenAIService(BaseLLMService):
    """OpenAI API integration service"""
    
    def __init__(self, api_config: APIConfiguration):
        super().__init__(api_config)
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            raise LLMConfigurationError("openai package not installed. Run: pip install openai")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response using OpenAI API"""
        start_time = time.time()
        
        try:
            # Prepare messages for OpenAI format
            openai_messages = []
            
            if system_prompt:
                openai_messages.append({"role": "system", "content": system_prompt})
            
            # Convert messages to OpenAI format
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                openai_messages.append({"role": role, "content": content})
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            response_time = time.time() - start_time
            response_text = response.choices[0].message.content
            
            metadata = {
                'provider': 'openai',
                'model': self.model_name,
                'response_time': response_time,
                'tokens_used': response.usage.total_tokens if response.usage else None,
                'finish_reason': response.choices[0].finish_reason,
            }
            
            logger.info(f"OpenAI response generated in {response_time:.2f}s")
            return response_text, metadata
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMAPIError(f"OpenAI API call failed: {str(e)}")


class GeminiService(BaseLLMService):
    """Google Gemini API integration service"""
    
    def __init__(self, api_config: APIConfiguration):
        super().__init__(api_config)
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
        except ImportError:
            raise LLMConfigurationError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response using Gemini API"""
        start_time = time.time()
        
        try:
            # Prepare conversation context
            conversation_text = ""
            
            if system_prompt:
                conversation_text += f"System: {system_prompt}\n\n"
            
            # Build conversation context
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                role_display = 'User' if role == 'user' else 'Assistant'
                conversation_text += f"{role_display}: {content}\n"
            
            # Add prompt for response
            conversation_text += "\nAssistant:"
            
            # Configure generation
            generation_config = {
                'max_output_tokens': max_tokens,
                'temperature': temperature,
            }
            
            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                conversation_text,
                generation_config=generation_config
            )
            
            response_time = time.time() - start_time
            response_text = response.text
            
            metadata = {
                'provider': 'gemini',
                'model': self.model_name,
                'response_time': response_time,
                'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None,
            }
            
            logger.info(f"Gemini response generated in {response_time:.2f}s")
            return response_text, metadata
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise LLMAPIError(f"Gemini API call failed: {str(e)}")


class ClaudeService(BaseLLMService):
    """Anthropic Claude API integration service"""
    
    def __init__(self, api_config: APIConfiguration):
        super().__init__(api_config)
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise LLMConfigurationError("anthropic package not installed. Run: pip install anthropic")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate response using Claude API"""
        start_time = time.time()
        
        try:
            # Prepare messages for Claude format
            claude_messages = []
            
            # Convert messages to Claude format
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                # Claude uses 'user' and 'assistant' roles
                claude_role = 'user' if role == 'user' else 'assistant'
                claude_messages.append({"role": claude_role, "content": content})
            
            # Make API call
            response = await self.client.messages.create(
                model=self.model_name,
                messages=claude_messages,
                system=system_prompt or "",
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            response_time = time.time() - start_time
            response_text = response.content[0].text
            
            metadata = {
                'provider': 'claude',
                'model': self.model_name,
                'response_time': response_time,
                'tokens_used': response.usage.output_tokens if hasattr(response, 'usage') else None,
                'stop_reason': response.stop_reason,
            }
            
            logger.info(f"Claude response generated in {response_time:.2f}s")
            return response_text, metadata
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise LLMAPIError(f"Claude API call failed: {str(e)}")


class LLMManager:
    """Manager class for handling multiple LLM providers"""
    
    _services = {
        'openai': OpenAIService,
        'gemini': GeminiService,
        'claude': ClaudeService,
    }
    
    @classmethod
    async def get_active_service(cls, provider: Optional[str] = None) -> BaseLLMService:
        """Get active LLM service instance"""
        try:
            if provider:
                config = APIConfiguration.objects.get(provider=provider, is_active=True)
            else:
                # Get first active configuration
                config = APIConfiguration.objects.filter(is_active=True).first()
                if not config:
                    raise LLMConfigurationError("No active API configurations found")
            
            service_class = cls._services.get(config.provider)
            if not service_class:
                raise LLMConfigurationError(f"Unsupported provider: {config.provider}")
            
            return service_class(config)
            
        except APIConfiguration.DoesNotExist:
            provider_msg = f" for {provider}" if provider else ""
            raise LLMConfigurationError(f"No active API configuration found{provider_msg}")
    
    @classmethod
    async def generate_chat_response(
        cls,
        user_message: str,
        conversation_history: Optional[List[Message]] = None,
        provider: Optional[str] = None,
        language: str = 'en',
        use_knowledge_base: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate chat response with conversation context and knowledge base
        
        Args:
            user_message: The user's message
            conversation_history: Previous messages in conversation
            provider: Specific LLM provider to use
            language: Language for system prompt
            use_knowledge_base: Whether to use document knowledge base
        
        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            service = await cls.get_active_service(provider)
            
            # Get system prompt
            system_prompt = service.get_system_prompt('system', language)
            
            # Enhanced system prompt with knowledge base context
            if use_knowledge_base:
                from documents.knowledge_base import KnowledgeBase
                
                # Search for relevant documents
                knowledge_context, referenced_docs = KnowledgeBase.get_knowledge_context(
                    user_message, max_documents=3, max_context_length=1500
                )
                
                if knowledge_context:
                    enhanced_system_prompt = f"""{system_prompt}

IMPORTANT: You have access to the company's knowledge base documents. Use this information to provide accurate, specific answers.

=== KNOWLEDGE BASE CONTEXT ===
{knowledge_context}

=== INSTRUCTIONS ===
1. Prioritize information from the knowledge base documents above
2. If the question can be answered using the documents, provide a detailed answer
3. Always mention when you're referencing company documents
4. If documents don't contain relevant information, provide general assistance
5. Be specific and cite the document name when referencing information

Answer the user's question using the provided context when relevant."""
                    
                    system_prompt = enhanced_system_prompt
                    metadata_docs = [
                        {
                            'id': doc.id,
                            'name': doc.name,
                            'category': doc.category or 'General'
                        }
                        for doc in referenced_docs
                    ]
                else:
                    referenced_docs = []
                    metadata_docs = []
            else:
                referenced_docs = []
                metadata_docs = []
            
            # Build message history
            messages = []
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-8:]:  # Reduced to 8 to leave room for knowledge context
                    role = 'user' if msg.sender_type == 'user' else 'assistant'
                    messages.append({
                        'role': role,
                        'content': msg.content
                    })
            
            # Add current user message
            messages.append({
                'role': 'user',
                'content': user_message
            })
            
            # Generate response
            response_text, metadata = await service.generate_response(
                messages=messages,
                system_prompt=system_prompt
            )
            
            # Add knowledge base metadata
            metadata['knowledge_base_used'] = use_knowledge_base
            metadata['referenced_documents'] = metadata_docs
            metadata['document_count'] = len(referenced_docs)
            
            # Record document usage (will be updated with feedback later)
            if referenced_docs:
                KnowledgeBase.record_document_usage(referenced_docs, feedback_positive=True)
            
            return response_text, metadata
            
        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            raise LLMError(f"Failed to generate response: {str(e)}")
    
    @classmethod
    async def test_configuration(cls, provider: str) -> Dict[str, Any]:
        """Test API configuration with a simple request"""
        try:
            service = await cls.get_active_service(provider)
            
            test_messages = [
                {'role': 'user', 'content': 'Hello, please respond with "Configuration test successful"'}
            ]
            
            response, metadata = await service.generate_response(
                messages=test_messages,
                max_tokens=50,
                temperature=0.1
            )
            
            return {
                'status': 'success',
                'provider': provider,
                'model': service.model_name,
                'response': response,
                'response_time': metadata.get('response_time', 0),
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'provider': provider,
                'error': str(e),
            }