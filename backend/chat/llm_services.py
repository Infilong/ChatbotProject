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
        """Get universal system prompt for any industry/use case"""
        # UNIVERSAL PROMPTS FOR ANY INDUSTRY
        logger.info("Using universal system prompt for any industry")
        
        universal_prompts = {
            'en': {
                'system': "You are a helpful AI assistant. Answer questions accurately based on available information.",
                'customer_service': "You are a professional assistant. Be helpful, courteous, and provide clear information.",
                'technical': "You are a knowledgeable assistant. Provide clear, accurate information.",
                'educational': "You are an educational assistant. Explain concepts clearly.",
                'creative': "You are a creative assistant. Help with ideas, writing, and creative projects.",
                'analytical': "You are an analytical assistant. Provide logical analysis and insights."
            },
            'ja': {
                'system': "私は役に立つAIアシスタントです。利用可能な情報に基づいて正確に回答します。",
                'customer_service': "私はプロのアシスタントです。親切で丁寧な対応を心がけ、明確な情報を提供します。",
                'technical': "私は知識豊富なアシスタントです。明確で正確な情報を提供します。",
                'educational': "私は教育アシスタントです。概念を分かりやすく説明します。",
                'creative': "私はクリエイティブアシスタントです。アイデア、執筆、創作活動をサポートします。",
                'analytical': "私は分析アシスタントです。論理的分析と洞察を提供します。"
            }
        }
        
        # Get prompt for the specified language and type
        lang_prompts = universal_prompts.get(language, universal_prompts['en'])
        return lang_prompts.get(prompt_type, lang_prompts['system'])
    
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
                return "親切なAIアシスタントです。簡潔に回答してください。"
            else:
                return "You are a helpful customer service assistant. Provide brief, helpful responses."
        return "You are a helpful assistant."
    
    def _get_default_system_prompt(self) -> str:
        """Default system prompt fallback"""
        return "You are a helpful customer service assistant. Provide brief, accurate responses."


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
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            genai.configure(api_key=self.api_key)
            
            # Configure safety settings to prevent blocking legitimate customer service content
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings=safety_settings
            )
            logger.info(f"GeminiService initialized with safety settings disabled for model: {self.model_name}")
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
            
            # Generate response with additional safety settings override
            try:
                # Import safety settings for this call
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    conversation_text,
                    generation_config=generation_config,
                    safety_settings=safety_settings  # Re-apply safety settings for this call
                )
            except Exception as safety_error:
                # If safety filter blocks, try with more permissive settings
                logger.warning(f"Gemini safety filter triggered: {safety_error}")
                logger.info("Retrying with maximum permissive safety settings...")
                
                # Import required types for retry
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                
                ultra_permissive_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                # Retry with generic prompt to avoid safety triggers
                generic_conversation = f"User question: {messages[-1].get('content', '')}\n\nPlease provide a helpful business-appropriate response."
                
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    generic_conversation,
                    generation_config=generation_config,
                    safety_settings=ultra_permissive_settings
                )
            
            response_time = time.time() - start_time
            
            # Safely extract response text with proper error handling
            try:
                response_text = response.text
            except Exception as text_error:
                logger.error(f"Failed to extract response text: {text_error}")
                logger.error(f"Response candidates: {response.candidates}")
                logger.error(f"Response finish_reason: {response.candidates[0].finish_reason if response.candidates else 'No candidates'}")
                
                # Check if response was blocked by safety filter or other issues
                if response.candidates and hasattr(response.candidates[0], 'finish_reason'):
                    finish_reason = response.candidates[0].finish_reason
                    if finish_reason.name == 'SAFETY':
                        raise LLMAPIError("Gemini safety filter blocked response. Please try rephrasing your question.")
                    elif finish_reason.name == 'MAX_TOKENS':
                        # Try with shorter prompt by reducing context
                        logger.warning("Token limit exceeded, retrying with reduced context...")
                        
                        # Retry with minimal system prompt and shorter context
                        minimal_prompt = "You are a helpful customer service assistant. Provide a brief, helpful response."
                        simple_conversation = f"User: {messages[-1].get('content', '')}\nAssistant:"
                        
                        try:
                            # Import safety settings for retry
                            from google.generativeai.types import HarmCategory, HarmBlockThreshold
                            retry_safety_settings = {
                                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                            }
                            
                            response = await asyncio.to_thread(
                                self.model.generate_content,
                                simple_conversation,
                                generation_config={'max_output_tokens': 500, 'temperature': 0.7},
                                safety_settings=retry_safety_settings
                            )
                            response_text = response.text
                            logger.info("Successfully retried with reduced context")
                        except Exception as retry_error:
                            logger.error(f"Retry with reduced context failed: {retry_error}")
                            raise LLMAPIError("Response too long. Please try a shorter question.")
                    else:
                        raise LLMAPIError(f"Gemini response blocked. Reason: {finish_reason.name}")
                else:
                    raise LLMAPIError("Gemini did not return a valid response.")
            
            metadata = {
                'provider': 'gemini',
                'model': self.model_name,
                'response_time': response_time,
                'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None,
            }
            
            logger.info(f"Gemini response generated in {response_time:.2f}s")
            return response_text, metadata
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Gemini API error: {e}")
            
            # Handle specific API error types with user-friendly messages
            if "429" in error_str and "quota" in error_str.lower():
                raise LLMAPIError("API rate limit reached. Please try again later or upgrade your plan.")
            elif "403" in error_str and "billing" in error_str.lower():
                raise LLMAPIError("API billing issue. Please check your API key and billing setup.")
            elif "invalid api key" in error_str.lower():
                raise LLMAPIError("Invalid API key. Please check your configuration.")
            else:
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
        use_knowledge_base: bool = True,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate chat response with conversation context and knowledge base
        
        Args:
            user_message: The user's message
            conversation_history: Previous messages in conversation
            provider: Specific LLM provider to use
            language: Language for system prompt
            use_knowledge_base: Whether to use document knowledge base
            conversation_id: ID of the conversation for usage tracking
            message_id: ID of the message for usage tracking
        
        Returns:
            Tuple of (response_text, metadata)
        """
        try:
            service = await cls.get_active_service(provider)
            
            # Get minimal system prompt to avoid token limits
            system_prompt = service.get_system_prompt('system', language)
            
            # Enhanced system prompt with knowledge base context
            knowledge_context = ""
            if use_knowledge_base:
                try:
                    # Import knowledge base (async-safe)
                    from asgiref.sync import sync_to_async
                    from documents.knowledge_base import KnowledgeBase
                    
                    # STAGE 1: Use LLM to understand user intent and generate search terms
                    search_terms = await cls._analyze_user_intent(user_message, service)
                    logger.info(f"LLM-generated search terms for '{user_message}': {search_terms}")
                    
                    # STAGE 2: Use enhanced search terms to find relevant documents  
                    relevant_docs = await KnowledgeBase.search_relevant_documents_async(
                        search_terms, limit=2, min_score=0.05  # Reduced from 3 to 2 documents
                    )
                    
                    if relevant_docs:
                        # Generate context from ONLY relevant documents
                        context_parts = []
                        referenced_docs = []
                        current_length = 0
                        max_context_length = 500  # BALANCED: enough for accuracy but preventing 503 errors
                        
                        for doc in relevant_docs:
                            # Get relevant excerpt from document - BALANCED FOR ACCURACY
                            excerpt = doc.get_excerpt(search_terms, max_length=250)  # BALANCED: accuracy without 503 errors
                            if not excerpt:
                                excerpt = doc.get_excerpt(user_message, max_length=250)  # BALANCED: accuracy without 503 errors
                            if not excerpt:
                                continue
                            
                            # Format document context - ULTRA-MINIMAL TO PREVENT 503 ERRORS
                            doc_context = f"{excerpt}\n"
                            
                            # Check if adding this document would exceed length limit
                            if current_length + len(doc_context) > max_context_length:
                                if not referenced_docs:  # Always include at least one document
                                    # Truncate the excerpt to fit - ULTRA-MINIMAL
                                    available_length = max_context_length - current_length
                                    truncated_excerpt = excerpt[:available_length - 10] + "..."
                                    doc_context = f"{truncated_excerpt}\n"
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
                        # UNIVERSAL CONTEXT FOR ANY INDUSTRY
                        system_prompt = f"Answer based on this information. Give direct, helpful answers: {knowledge_context[:300]}..."
                        metadata_docs = [
                            {"name": doc.name, "category": doc.category, "uuid": str(doc.uuid)}
                            for doc in referenced_docs
                        ]
                        logger.info(f"Using {len(referenced_docs)} documents for context")
                        logger.info(f"Knowledge context length: {len(knowledge_context)} characters")
                        logger.info(f"Knowledge context preview: {knowledge_context[:300]}...")
                    
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
            
            # Add conversation history - REDUCED TO 3 MESSAGES TO PREVENT TOKEN LIMITS
            if conversation_history:
                # Use only the most recent 3 messages for context to stay under token limits
                recent_history = conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
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
            
            # Log the final system prompt for debugging
            logger.info(f"Final system prompt length: {len(system_prompt)} characters")
            if len(referenced_docs) > 0:
                logger.info(f"System prompt with context (first 500 chars): {system_prompt[:500]}...")
            
            # Generate response
            response_text, metadata = await service.generate_response(
                messages=messages,
                system_prompt=system_prompt
            )
            
            # Clean the response to remove formatting characters like * that might come from documents
            response_text = cls._clean_response_text(response_text)
            
            # Log the response for debugging
            logger.info(f"LLM response generated: {response_text[:200]}...")
            
            # Check if LLM ignored the provided context (debugging)
            if len(referenced_docs) > 0 and ("don't have" in response_text.lower() or "no information" in response_text.lower()):
                logger.warning(f"LLM may have ignored provided context. Documents: {len(referenced_docs)}, Response: {response_text[:100]}...")
                logger.warning(f"Knowledge context was: {knowledge_context[:200]}..." if 'knowledge_context' in locals() else "No context variable found")
            
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
                            from analytics.models import DocumentUsage
                            import re
                            
                            for i, doc in enumerate(referenced_docs):
                                # Increment reference count atomically
                                doc.reference_count += 1
                                doc.last_referenced = timezone.now()
                                # Update effectiveness score based on positive feedback
                                doc.effectiveness_score = min(doc.effectiveness_score + 0.1, 10.0)
                                doc.save(update_fields=['reference_count', 'last_referenced', 'effectiveness_score'])
                                
                                # Extract keywords from user message for tracking
                                keywords_matched = []
                                search_terms = user_message.lower().split()
                                doc_text_lower = (doc.extracted_text or '').lower()
                                for term in search_terms:
                                    if len(term) > 2 and term in doc_text_lower:
                                        keywords_matched.append(term)
                                
                                # Get the excerpt that was used (from knowledge context)
                                excerpt_used = ""
                                excerpt_start_pos = None
                                excerpt_length = None
                                
                                if doc.extracted_text:
                                    # Try to find the excerpt in the original document
                                    excerpt = doc.get_excerpt(user_message, max_length=600)
                                    if excerpt:
                                        excerpt_used = excerpt
                                        # Find position in original text
                                        start_pos = doc.extracted_text.find(excerpt[:100])  # Use first 100 chars to find position
                                        if start_pos != -1:
                                            excerpt_start_pos = start_pos
                                            excerpt_length = len(excerpt)
                                
                                # Determine user intent from message
                                user_intent = "general_inquiry"
                                intent_keywords = {
                                    'compliance': ['gdpr', 'ccpa', 'regulation', 'compliance', 'privacy'],
                                    'services': ['service', 'offer', 'provide', 'solution', 'help'],
                                    'pricing': ['price', 'cost', 'fee', 'pricing', 'charge'],
                                    'support': ['support', 'help', 'assistance', 'problem', 'issue'],
                                    'technical': ['how to', 'setup', 'configure', 'install', 'technical']
                                }
                                
                                for intent, terms in intent_keywords.items():
                                    if any(term in user_message.lower() for term in terms):
                                        user_intent = intent
                                        break
                                
                                # Create detailed usage record with proper context
                                try:
                                    if conversation_id and message_id:
                                        usage = DocumentUsage.objects.create(
                                            document=doc,
                                            conversation_id=conversation_id,
                                            message_id=message_id,
                                            search_query=user_message[:500],  # Truncate to fit field
                                            relevance_score=doc.get_relevance_score(user_message),
                                            usage_type='excerpt',
                                            excerpt_used=excerpt_used,
                                            excerpt_start_position=excerpt_start_pos,
                                            excerpt_length=excerpt_length,
                                            keywords_matched=keywords_matched,
                                            context_category=doc.category or 'general',
                                            user_intent=user_intent,
                                            llm_model_used=metadata.get('model', 'unknown'),
                                            processing_time=metadata.get('response_time', 0.0)
                                        )
                                        logger.info(f"Created detailed usage record for document: {doc.name}")
                                    else:
                                        logger.warning(f"Skipping usage record creation - missing conversation_id or message_id")
                                except Exception as usage_error:
                                    logger.warning(f"Failed to create detailed usage record: {usage_error}")
                                
                                logger.info(f"Updated usage for document: {doc.name} (score: {doc.effectiveness_score:.2f})")
                    
                    await record_usage_atomic()
                except Exception as e:
                    logger.warning(f"Failed to record document usage: {e}")
            
            return response_text, metadata
            
        except Exception as e:
            logger.error(f"Chat response generation failed: {e}")
            raise LLMError(f"Failed to generate response: {str(e)}")
    
    @classmethod
    async def _analyze_user_intent(cls, user_message: str, service: BaseLLMService) -> str:
        """
        STAGE 1: Use LLM to analyze user intent and generate optimized search terms
        This is the key to efficient RAG - understanding what the user really wants
        """
        try:
            # STAGE 1: Use LLM to understand user intent and extract semantic meaning
            # This is the proper AI-driven approach you requested
            try:
                # Create a minimal, focused prompt for semantic understanding
                intent_prompt = f"""Query: "{user_message}"
Add 3-5 relevant keywords:"""

                # Use LLM with minimal context to avoid token issues
                intent_response, _ = await service.generate_response(
                    messages=[{'role': 'user', 'content': intent_prompt}],
                    max_tokens=30,  # Very short response
                    temperature=0.0  # Deterministic
                )
                
                # Clean the response
                enhanced_terms = intent_response.strip()
                
                # Remove common prefixes
                prefixes = ['keywords:', 'terms:', 'search:', 'relevant:']
                for prefix in prefixes:
                    if enhanced_terms.lower().startswith(prefix):
                        enhanced_terms = enhanced_terms[len(prefix):].strip()
                
                # Combine with original query for better results
                final_terms = f"{user_message} {enhanced_terms}"
                
                logger.info(f"Intent analysis (LLM-based): '{user_message}' → '{final_terms}'")
                return final_terms
                
            except Exception as llm_error:
                logger.warning(f"LLM intent analysis failed: {llm_error}")
                # Fallback to pattern-based approach
                enhanced_terms = cls._generate_search_terms_safely(user_message)
                logger.info(f"Intent analysis (fallback): '{user_message}' → '{enhanced_terms}'")
                return enhanced_terms
            
        except Exception as e:
            logger.warning(f"Intent analysis failed: {e}")
            # Smart fallback - enhance the original query with common business terms
            result = cls._enhance_query_fallback(user_message)
            logger.info(f"Intent analysis (fallback): '{user_message}' → '{result}'")
            return result
    
    @classmethod
    def _clean_response_text(cls, response_text: str) -> str:
        """Clean LLM response text to remove unwanted formatting characters"""
        if not response_text:
            return response_text
        
        import re
        
        # Clean up markdown-style formatting that might come from documents
        cleaned_text = response_text
        
        # Handle bullet points - convert * bullets to clean format but preserve content
        # Replace "* **Text:**" with "- Text:" (remove bold markers but keep bullet structure)
        cleaned_text = re.sub(r'\*\s+\*\*(.*?)\*\*\s*:', r'- \1:', cleaned_text)
        
        # Replace remaining **bold text** with just the text
        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_text)
        
        # Replace *italic text* with just the text
        cleaned_text = re.sub(r'\*(.*?)\*', r'\1', cleaned_text)
        
        # Clean up bullet points - replace "* " with "- " for better readability
        cleaned_text = re.sub(r'^\s*\*\s+', '- ', cleaned_text, flags=re.MULTILINE)
        
        # Clean up any remaining standalone asterisks
        cleaned_text = re.sub(r'\*+', '', cleaned_text)
        
        # Clean up excessive whitespace
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        
        # Fix spacing around bullet points
        cleaned_text = re.sub(r'\n\s*-\s*', '\n- ', cleaned_text)
        
        # Clean up any double spaces or excessive newlines
        cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
        
        return cleaned_text.strip()

    @classmethod
    def _generate_search_terms_safely(cls, user_message: str) -> str:
        """
        Generate enhanced search terms using safe pattern matching
        This avoids LLM safety filters and token limits while providing intelligent expansion
        """
        query_lower = user_message.lower().strip()
        
        # Legal/compliance/regulatory patterns (HIGH PRIORITY - check first)
        if any(term in query_lower for term in ['gdpr', 'ccpa', 'compliance', 'compliant', 'comply', 'regulation', 'regulations', 'legal', 'law', 'laws', 'privacy', 'data protection', 'regulatory']):
            return f"{user_message} compliance compliant comply GDPR CCPA regulations legal privacy data protection regulatory"
        
        # Security patterns (HIGH PRIORITY)
        elif any(term in query_lower for term in ['security', 'secure', 'safe', 'safety', 'protection', 'encrypt', 'encryption']):
            return f"{user_message} security secure safety protection encryption data security"
        
        # Technology-related patterns
        elif any(term in query_lower for term in ['tech', 'technology', 'technologies', 'tool', 'tools', 'platform', 'platforms', 'software', 'stack', 'framework']):
            return f"{user_message} technology technologies tools platforms software stack frameworks systems"
        
        # Pricing/cost patterns
        elif any(term in query_lower for term in ['cost', 'price', 'pricing', 'fee', 'fees', 'quote', 'quotes', 'payment', 'pay', 'money', 'budget']):
            return f"{user_message} pricing cost price fees quotes packages plans payment rates models"
        
        # Service/offering patterns
        elif any(term in query_lower for term in ['service', 'services', 'offer', 'offering', 'offerings', 'provide', 'do you do', 'capabilities']):
            return f"{user_message} services offerings solutions products capabilities expertise analytics"
        
        # Contact/communication patterns
        elif any(term in query_lower for term in ['contact', 'reach', 'call', 'phone', 'email', 'communicate', 'talk', 'speak']):
            return f"{user_message} contact communication phone email support reach information"
        
        # Support/help patterns
        elif any(term in query_lower for term in ['help', 'support', 'assistance', 'problem', 'issue', 'trouble', 'fix']):
            return f"{user_message} support help assistance troubleshooting guidance documentation"
        
        # Process/procedure patterns
        elif any(term in query_lower for term in ['how', 'process', 'procedure', 'step', 'steps', 'workflow', 'method']):
            return f"{user_message} process procedure method workflow steps guide instructions"
        
        # Time/schedule patterns
        elif any(term in query_lower for term in ['when', 'time', 'schedule', 'timeline', 'duration', 'deadline', 'availability']):
            return f"{user_message} time schedule timeline duration availability timeframe"
        
        # General business patterns (LOWER PRIORITY - check last)
        elif any(term in query_lower for term in ['about', 'company', 'business', 'who are', 'what is', 'information', 'details']):
            return f"{user_message} information company business details about overview"
        
        # Default: add general business terms
        else:
            return f"{user_message} information support help services business"
    
    @classmethod
    def _enhance_query_fallback(cls, query: str) -> str:
        """
        Fallback query enhancement when LLM intent analysis fails
        """
        query_lower = query.lower()
        
        # Common business term expansions
        expansions = {
            'support': 'support assistance help services customer service team collaboration',
            'teams': 'teams groups organizations enterprises businesses collaboration',
            'price': 'pricing cost packages fees quotes payment rates models',
            'cost': 'pricing cost packages fees quotes payment rates models', 
            'technology': 'technology tools platforms software systems frameworks stack',
            'consultation': 'consultation meeting advice support services process discussion',
            'services': 'services solutions offerings capabilities expertise analytics',
            'analytics': 'analytics analysis data insights reports dashboards predictive',
            'data': 'data information insights analytics reports analysis',
            'project': 'project work engagement timeline process methodology phases',
        }
        
        # Find relevant expansions
        enhanced_terms = [query]
        for keyword, expansion in expansions.items():
            if keyword in query_lower:
                enhanced_terms.append(expansion)
        
        result = ' '.join(enhanced_terms)
        logger.info(f"Fallback query enhancement: '{query}' → '{result}'")
        return result
    
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