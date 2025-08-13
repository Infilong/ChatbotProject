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
        """Get system prompt from AdminPrompt model (sync version)"""
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
                    
        except Exception as e:
            logger.warning(f"Failed to get admin prompt: {e}")
        
        # Ultimate fallback - hardcoded prompt
        return self._get_fallback_prompt(prompt_type, language)
    
    async def aget_system_prompt(self, prompt_type: str = 'system', language: str = 'en') -> str:
        """Get system prompt from AdminPrompt model (async version)"""
        try:
            prompt = await AdminPrompt.objects.filter(
                prompt_type=prompt_type,
                language=language,
                is_active=True,
                is_default=True
            ).afirst()
            
            if prompt:
                # Increment usage synchronously for now
                from asgiref.sync import sync_to_async
                await sync_to_async(prompt.increment_usage)()
                return prompt.prompt_text
            
            # Fallback to English if no language-specific prompt found
            if language != 'en':
                prompt = await AdminPrompt.objects.filter(
                    prompt_type=prompt_type,
                    language='en',
                    is_active=True,
                    is_default=True
                ).afirst()
                
                if prompt:
                    await sync_to_async(prompt.increment_usage)()
                    return prompt.prompt_text
            
        except Exception as e:
            logger.warning(f"Failed to get admin prompt: {e}")
        
        # Ultimate fallback - hardcoded prompt
        return self._get_fallback_prompt(prompt_type, language)
    
    def _get_fallback_prompt(self, prompt_type: str, language: str) -> str:
        """Fallback system prompts when database is unavailable"""
        if prompt_type == 'system':
            if language == 'ja':
                return "あなたは親切で知識豊富なAIアシスタントです。ユーザーの質問に正確で有用な回答を提供してください。"
            else:
                return "You are a helpful and knowledgeable AI assistant. Provide accurate and useful responses to user questions."
        return "You are a helpful AI assistant."
    
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
                config = await APIConfiguration.objects.aget(provider=provider, is_active=True)
            else:
                # Get first active configuration
                config = await APIConfiguration.objects.filter(is_active=True).afirst()
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
            
            # Get system prompt (async version)
            system_prompt = await service.aget_system_prompt('system', language)
            
            # Enhanced system prompt with knowledge base context
            knowledge_context = ""
            if use_knowledge_base:
                try:
                    # Import knowledge base (async-safe)
                    from asgiref.sync import sync_to_async
                    from documents.knowledge_base import KnowledgeBase
                    
                    # Use async version of document search with LLM preprocessing
                    relevant_docs = await KnowledgeBase.search_relevant_documents_async(user_message)
                    
                    if relevant_docs:
                        # Generate context from documents
                        context_parts = []
                        referenced_docs = []
                        current_length = 0
                        max_context_length = 2000
                        
                        for doc in relevant_docs:
                            # Get relevant excerpt from document
                            excerpt = doc.get_excerpt(user_message, max_length=600)
                            if not excerpt:
                                continue
                            
                            # Format document context
                            doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}
Content: {excerpt}
---
"""
                            
                            # Check if adding this document would exceed length limit
                            if current_length + len(doc_context) > max_context_length:
                                if not referenced_docs:  # Always include at least one document
                                    # Truncate the excerpt to fit
                                    available_length = max_context_length - current_length
                                    truncated_excerpt = excerpt[:available_length - 100] + "..."
                                    doc_context = f"""
[Document: {doc.name}]
Category: {doc.category or 'General'}
Content: {truncated_excerpt}
---
"""
                                    context_parts.append(doc_context)
                                    referenced_docs.append(doc)
                                break
                            
                            context_parts.append(doc_context)
                            referenced_docs.append(doc)
                            current_length += len(doc_context)
                        
                        knowledge_context = ''.join(context_parts)
                    else:
                        knowledge_context = ""
                        referenced_docs = []
                    
                    if knowledge_context:
                        system_prompt += f"""

KNOWLEDGE BASE CONTEXT:
{knowledge_context}

CRITICAL INSTRUCTIONS FOR USING KNOWLEDGE BASE:
1. ALWAYS prioritize information from the Knowledge Base above general knowledge
2. If the user's question relates to content in the Knowledge Base, answer STRICTLY based on that information
3. Use SEMANTIC UNDERSTANDING - match user intent even if exact words differ (e.g., "technologies you use" matches tech-related content)
4. TOLERATE TYPOS - understand misspelled words like "businesse" (business), "startaps" (startups), "cousultation" (consultation)
5. If no Knowledge Base content matches the query, clearly state this and provide general assistance
6. When referencing Knowledge Base content, be specific and cite the relevant sections"""
                        metadata_docs = [
                            {"name": doc.name, "category": doc.category, "uuid": str(doc.uuid)}
                            for doc in referenced_docs
                        ]
                        logger.info(f"Using {len(referenced_docs)} documents for context")
                    
                except Exception as e:
                    logger.warning(f"Knowledge base integration failed: {e}")
                    # Continue without knowledge base
            
            # Initialize variables
            if 'referenced_docs' not in locals():
                referenced_docs = []
            if 'metadata_docs' not in locals():
                metadata_docs = []
            
            # Build message history
            messages = []
            
            # Add conversation history
            if conversation_history:
                # Use the most recent 8 messages for context
                recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
                for msg in recent_history:
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
                try:
                    from asgiref.sync import sync_to_async
                    from django.db import transaction
                    from django.utils import timezone
                    
                    # Create async-safe document usage recording function
                    @sync_to_async
                    def record_usage_atomic():
                        with transaction.atomic():
                            for doc in referenced_docs:
                                # Increment reference count atomically
                                doc.reference_count += 1
                                doc.last_referenced = timezone.now()
                                # Update effectiveness score based on positive feedback
                                doc.effectiveness_score = min(doc.effectiveness_score + 0.1, 10.0)
                                doc.save(update_fields=['reference_count', 'last_referenced', 'effectiveness_score'])
                                logger.info(f"Updated usage for document: {doc.name} (score: {doc.effectiveness_score:.2f})")
                    
                    await record_usage_atomic()
                except Exception as e:
                    logger.warning(f"Failed to record document usage: {e}")
            
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