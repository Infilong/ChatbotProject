"""
Google LangExtract integration for conversation analysis
Provides structured insights from unstructured chat conversations
"""

import json
import logging
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

# Import LangExtract if available
try:
    import langextract as lx
    LANGEXTRACT_AVAILABLE = True
except ImportError:
    LANGEXTRACT_AVAILABLE = False
    logger.warning("LangExtract not installed. Install with: pip install langextract")


class LangExtractService:
    """Service for analyzing conversations using Google LangExtract"""
    
    def __init__(self):
        self.langextract_available = LANGEXTRACT_AVAILABLE
        self.api_key = self._get_api_key()
        self.default_model = "gemini-2.5-flash"  # Updated to latest recommended model
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from APIConfiguration model or environment"""
        try:
            from chat.models import APIConfiguration
            
            # Try to get API key from admin-configured sources
            # Priority: Gemini (recommended for LangExtract) -> OpenAI -> Claude
            for provider in ['gemini', 'openai', 'claude']:
                try:
                    config = APIConfiguration.objects.get(provider=provider, is_active=True)
                    if config.api_key:
                        logger.info(f"Using {provider} API key from admin configuration for LangExtract")
                        return config.api_key
                except APIConfiguration.DoesNotExist:
                    continue
            
            # Fallback to environment variables
            env_key = os.getenv('LANGEXTRACT_API_KEY') or getattr(settings, 'LANGEXTRACT_API_KEY', None)
            if env_key:
                logger.info("Using API key from environment for LangExtract")
                return env_key
                
            logger.warning("No API key found for LangExtract. Configure in Django admin or set LANGEXTRACT_API_KEY")
            return None
            
        except Exception as e:
            logger.error(f"Error getting API key for LangExtract: {e}")
            return None
    
    def analyze_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a conversation for insights, sentiment, and intelligence
        
        Args:
            messages: List of message objects with 'role', 'content', 'timestamp'
            
        Returns:
            Structured analysis with sentiment, satisfaction, issues, etc.
        """
        try:
            # Check if we can use real LangExtract
            if self.langextract_available and self.api_key:
                return self._real_langextract_analysis(messages)
            else:
                logger.info("Using simulated analysis - LangExtract not available or no API key")
                return self._simulate_langextract_analysis(messages)
            
        except Exception as e:
            logger.error(f"LangExtract analysis failed: {e}")
            return self._get_fallback_analysis()
    
    def _real_langextract_analysis(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use real LangExtract API for conversation analysis"""
        try:
            # Prepare conversation text
            conversation_text = self._prepare_conversation_text(messages)
            
            # Log the API call details
            logger.info(f"Making LangExtract API call with model: {self.default_model}")
            logger.info(f"API key configured: {bool(self.api_key)}")
            logger.info(f"Conversation text length: {len(conversation_text)} characters")
            logger.info(f"Provider detected: {self._get_provider_from_key()}")
            
            # Define extraction prompt for LangExtract with correct format
            prompt_description = """
            Analyze this customer support conversation and extract structured information.
            
            You must respond with ONLY valid JSON in this exact format with an "extractions" key:
            
            {
              "extractions": [
                {
                  "extraction_class": "sentiment",
                  "extraction_text": "positive or negative or neutral"
                },
                {
                  "extraction_class": "satisfaction_level", 
                  "extraction_text": "number from 1 to 10"
                },
                {
                  "extraction_class": "issues_raised",
                  "extraction_text": "comma-separated list of issues"
                },
                {
                  "extraction_class": "urgency_level",
                  "extraction_text": "high or medium or low"
                },
                {
                  "extraction_class": "resolution_status",
                  "extraction_text": "resolved or pending or escalated"
                },
                {
                  "extraction_class": "customer_intent",
                  "extraction_text": "support_request or complaint or sales_inquiry"
                },
                {
                  "extraction_class": "key_insights",
                  "extraction_text": "comma-separated actionable insights"
                },
                {
                  "extraction_class": "conversation_summary",
                  "extraction_text": "brief summary of the conversation"
                }
              ]
            }
            
            Return only this JSON format. No other text.
            """
            
            # Configure settings to help with JSON parsing
            model_settings = {
                'fence_output': True,  # Expect fenced JSON output like ```json
                'use_schema_constraints': False,  # Disable strict schema validation
                'temperature': 0.1  # Low temperature for consistent output
            }
            
            logger.info("Calling LangExtract API...")
            
            # Use the working method: proper ExampleData structure
            from langextract.data import ExampleData, Extraction
            
            # Create examples with the correct LangExtract format
            examples = [
                ExampleData(
                    text="I love this service! You guys are amazing and helped me so quickly.",
                    extractions=[
                        Extraction(extraction_class="sentiment", extraction_text="positive"),
                        Extraction(extraction_class="satisfaction_level", extraction_text="9"),
                        Extraction(extraction_class="urgency_level", extraction_text="low"),
                        Extraction(extraction_class="customer_intent", extraction_text="support_request")
                    ]
                ),
                ExampleData(
                    text="This is terrible! I can't access my account and need help immediately!",
                    extractions=[
                        Extraction(extraction_class="sentiment", extraction_text="negative"),
                        Extraction(extraction_class="satisfaction_level", extraction_text="2"),
                        Extraction(extraction_class="urgency_level", extraction_text="high"),
                        Extraction(extraction_class="customer_intent", extraction_text="complaint")
                    ]
                ),
                ExampleData(
                    text="Hi, I need help with my password reset please.",
                    extractions=[
                        Extraction(extraction_class="sentiment", extraction_text="neutral"),
                        Extraction(extraction_class="satisfaction_level", extraction_text="6"),
                        Extraction(extraction_class="urgency_level", extraction_text="medium"),
                        Extraction(extraction_class="customer_intent", extraction_text="support_request")
                    ]
                )
            ]
            
            # Make the API call with proper examples
            logger.info("Making LangExtract API call with proper examples...")
            
            # Suppress console output from LangExtract to avoid Unicode errors on Windows
            import os
            import sys
            from contextlib import redirect_stdout, redirect_stderr
            from io import StringIO
            
            # Log detailed API call information
            logger.info("=== LangExtract API Call Details ===")
            logger.info(f"Target Model: {self.default_model}")
            logger.info(f"API Key: {self.api_key[:10]}...{self.api_key[-4:]}")
            logger.info(f"Conversation Length: {len(conversation_text)} characters")
            logger.info(f"Examples Provided: {len(examples)} ExampleData objects")
            logger.info(f"Model Settings: {model_settings}")
            logger.info("=====================================")
            
            result = None
            try:
                # Log network call start
                import time
                start_time = time.time()
                logger.info("🌐 Starting Gemini API network call...")
                
                # Redirect all console output to capture buffers
                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                    result = lx.extract(
                        text_or_documents=conversation_text,
                        prompt_description=prompt_description,
                        examples=examples,
                        model_id=self.default_model,
                        api_key=self.api_key,
                        **model_settings
                    )
                
                # Log network call completion
                end_time = time.time()
                call_duration = end_time - start_time
                logger.info(f"✅ Gemini API call completed in {call_duration:.2f} seconds")
                    
            except UnicodeEncodeError as unicode_error:
                # This is a known Windows console encoding issue in LangExtract
                # The API call usually succeeds, but the progress output fails
                logger.warning(f"LangExtract console output Unicode error (Windows): {unicode_error}")
                
                # Try a workaround: call again but with minimal settings to avoid progress output
                logger.info("Attempting workaround for Unicode console issue...")
                try:
                    # Set environment variable to suppress colored output
                    old_force_color = os.environ.get('FORCE_COLOR')
                    old_no_color = os.environ.get('NO_COLOR')
                    os.environ['NO_COLOR'] = '1'  # Disable colored output
                    if old_force_color:
                        del os.environ['FORCE_COLOR']
                    
                    # Try again with simplified settings
                    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                        result = lx.extract(
                            text_or_documents=conversation_text,
                            prompt_description=prompt_description,
                            examples=examples,
                            model_id=self.default_model,
                            api_key=self.api_key,
                            fence_output=False,  # Disable fenced output
                            use_schema_constraints=False,
                            temperature=0.1
                        )
                    
                    # Restore environment
                    if old_force_color:
                        os.environ['FORCE_COLOR'] = old_force_color
                    if old_no_color:
                        os.environ['NO_COLOR'] = old_no_color
                    else:
                        del os.environ['NO_COLOR']
                        
                    logger.info("Successfully worked around Unicode console issue")
                    
                except Exception as retry_error:
                    logger.error(f"Workaround also failed: {retry_error}")
                    if result is None:
                        raise unicode_error  # Re-raise original error if no result
            
            logger.info("=== LangExtract API Response ===")
            logger.info(f"✅ API call successful!")
            logger.info(f"Response type: {type(result)}")
            logger.info(f"Response object: {result}")
            
            # Log response details
            if hasattr(result, 'extractions'):
                logger.info(f"Extractions found: {len(result.extractions) if result.extractions else 0}")
                if result.extractions:
                    logger.info("=== Extraction Details ===")
                    for i, extraction in enumerate(result.extractions):
                        logger.info(f"  [{i+1}] Class: {getattr(extraction, 'extraction_class', 'Unknown')}")
                        logger.info(f"      Text: {getattr(extraction, 'extraction_text', 'Unknown')}")
            
            logger.info("===============================")
            
            # Extract data from LangExtract AnnotatedDocument result
            extracted_data = {}
            if hasattr(result, 'extractions') and result.extractions:
                # Parse extractions into a dictionary - LangExtract returns pairs
                # Each extraction has extraction_class and extraction_text alternating
                current_class = None
                for extraction in result.extractions:
                    if hasattr(extraction, 'extraction_class') and hasattr(extraction, 'extraction_text'):
                        if extraction.extraction_class == 'extraction_class':
                            # This extraction contains the class name
                            current_class = extraction.extraction_text
                        elif extraction.extraction_class == 'extraction_text' and current_class:
                            # This extraction contains the value for the current class
                            extracted_data[current_class] = extraction.extraction_text
                            current_class = None  # Reset for next pair
                        else:
                            # Handle direct class-value pairs (fallback)
                            extracted_data[extraction.extraction_class] = extraction.extraction_text
                
                logger.info(f"Parsed extracted data: {extracted_data}")
                
                # If we didn't get the expected format, try direct parsing
                if not extracted_data and result.extractions:
                    logger.warning("Using fallback extraction parsing...")
                    for extraction in result.extractions:
                        if hasattr(extraction, 'extraction_class') and hasattr(extraction, 'extraction_text'):
                            extracted_data[extraction.extraction_class] = extraction.extraction_text
            
            # Convert LangExtract result to our expected format
            analysis_result = {
                "sentiment": extracted_data.get("sentiment", "neutral"),
                "satisfaction_level": int(extracted_data.get("satisfaction_level", 5)) if extracted_data.get("satisfaction_level") and extracted_data.get("satisfaction_level").isdigit() else 5,
                "issues_raised": extracted_data.get("issues_raised", "General Inquiry").split(", ") if extracted_data.get("issues_raised") else ["General Inquiry"],
                "urgency_indicators": extracted_data.get("urgency_level", "low"),
                "resolution_status": extracted_data.get("resolution_status", "in_progress"),
                "customer_intent": extracted_data.get("customer_intent", "general_inquiry"),
                "key_insights": extracted_data.get("key_insights", "Standard interaction").split(", ") if extracted_data.get("key_insights") else ["Standard interaction"],
                "conversation_metrics": self._calculate_metrics(messages),
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_version": "langextract_v1.0",
                "model_used": self.default_model,
                "conversation_summary": extracted_data.get("conversation_summary", ""),
                "langextract_raw_result": str(result)  # Store raw result for debugging
            }
            
            logger.info("Successfully completed LangExtract analysis")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Real LangExtract analysis failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            
            # Log more details about the failure
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Try to determine the specific cause
            if "api_key" in str(e).lower():
                logger.error("API key issue detected")
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                logger.error("Network connection issue detected")
            elif "quota" in str(e).lower() or "limit" in str(e).lower():
                logger.error("API quota/limit issue detected")
            
            # Fallback to simulation
            return self._simulate_langextract_analysis(messages)
    
    def _get_provider_from_key(self) -> str:
        """Determine which provider is being used based on the API key source"""
        try:
            from chat.models import APIConfiguration
            for provider in ['gemini', 'openai', 'claude']:
                try:
                    config = APIConfiguration.objects.get(provider=provider, is_active=True)
                    if config.api_key == self.api_key:
                        return provider
                except APIConfiguration.DoesNotExist:
                    continue
            return 'gemini'  # Default assumption
        except:
            return 'gemini'
    
    def _calculate_metrics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate conversation metrics"""
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        assistant_messages = [msg for msg in messages if msg.get('role') in ['assistant', 'bot']]
        
        total_words = sum(len(msg.get('content', '').split()) for msg in messages)
        avg_message_length = total_words / len(messages) if messages else 0
        
        return {
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "conversation_length": total_words,
            "avg_message_length": round(avg_message_length, 1)
        }
    
    def _prepare_conversation_text(self, messages: List[Dict[str, Any]]) -> str:
        """Prepare conversation text for analysis"""
        conversation_lines = []
        
        for msg in messages:
            role = "Customer" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            conversation_lines.append(f"[{timestamp}] {role}: {content}")
        
        return "\\n".join(conversation_lines)
    
    def _simulate_langextract_analysis(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate Google LangExtract analysis"""
        
        # Prepare conversation text for analysis
        conversation_text = self._prepare_conversation_text(messages)
        
        # Count user vs assistant messages
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        assistant_messages = [msg for msg in messages if msg.get('role') in ['assistant', 'bot']]
        
        # Analyze sentiment based on keywords
        sentiment = self._analyze_sentiment(conversation_text)
        satisfaction_level = self._calculate_satisfaction(conversation_text, sentiment)
        issues_detected = self._detect_issues(conversation_text)
        urgency_level = self._assess_urgency(conversation_text)
        
        # Customer intent classification
        intent = self._classify_intent(user_messages)
        
        # Resolution status
        resolution_status = self._assess_resolution_status(conversation_text, len(messages))
        
        return {
            "sentiment": sentiment,
            "satisfaction_level": satisfaction_level,
            "issues_raised": issues_detected,
            "urgency_indicators": urgency_level,
            "resolution_status": resolution_status,
            "customer_intent": intent,
            "conversation_metrics": self._calculate_metrics(messages),
            "key_insights": self._extract_key_insights(conversation_text, sentiment, intent),
            "analysis_timestamp": datetime.now().isoformat(),
            "analysis_version": "simulated_v1.0"
        }
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of conversation"""
        text_lower = text.lower()
        
        positive_words = ['thank', 'great', 'good', 'excellent', 'perfect', 'amazing', 'helpful', 'satisfied']
        negative_words = ['bad', 'terrible', 'awful', 'problem', 'issue', 'frustrated', 'angry', 'disappointed']
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        if positive_score > negative_score:
            return "positive"
        elif negative_score > positive_score:
            return "negative"
        else:
            return "neutral"
    
    def _calculate_satisfaction(self, text: str, sentiment: str) -> int:
        """Calculate satisfaction score 1-10"""
        base_score = 5  # neutral
        
        if sentiment == "positive":
            base_score = 7
        elif sentiment == "negative":
            base_score = 3
        
        # Adjust based on specific keywords
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['excellent', 'perfect', 'amazing']):
            base_score = min(10, base_score + 2)
        elif any(word in text_lower for word in ['good', 'helpful', 'satisfied']):
            base_score = min(10, base_score + 1)
        elif any(word in text_lower for word in ['terrible', 'awful', 'frustrated']):
            base_score = max(1, base_score - 2)
        elif any(word in text_lower for word in ['bad', 'problem', 'issue']):
            base_score = max(1, base_score - 1)
        
        return base_score
    
    def _detect_issues(self, text: str) -> List[str]:
        """Detect issues and categorize them"""
        issues = []
        text_lower = text.lower()
        
        issue_categories = {
            "Technical Issues": ['bug', 'error', 'broken', 'not working', 'crash', 'slow'],
            "Account Issues": ['account', 'login', 'password', 'access', 'billing'],
            "Product Questions": ['how to', 'help', 'tutorial', 'guide', 'feature'],
            "Complaints": ['complaint', 'frustrated', 'angry', 'disappointed', 'terrible'],
            "Refund/Return": ['refund', 'return', 'cancel', 'money back']
        }
        
        for category, keywords in issue_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                issues.append(category)
        
        return issues if issues else ["General Inquiry"]
    
    def _assess_urgency(self, text: str) -> str:
        """Assess urgency level"""
        text_lower = text.lower()
        
        high_urgency_words = ['urgent', 'emergency', 'immediately', 'asap', 'critical', 'broken']
        medium_urgency_words = ['soon', 'quickly', 'problem', 'issue', 'important']
        
        if any(word in text_lower for word in high_urgency_words):
            return "high"
        elif any(word in text_lower for word in medium_urgency_words):
            return "medium"
        else:
            return "low"
    
    def _classify_intent(self, user_messages: List[Dict[str, Any]]) -> str:
        """Classify customer intent"""
        if not user_messages:
            return "unknown"
        
        first_message = user_messages[0].get('content', '').lower()
        
        if any(word in first_message for word in ['help', 'how', 'tutorial', 'guide']):
            return "support_request"
        elif any(word in first_message for word in ['buy', 'purchase', 'price', 'cost']):
            return "sales_inquiry"
        elif any(word in first_message for word in ['complaint', 'problem', 'issue', 'wrong']):
            return "complaint"
        elif any(word in first_message for word in ['refund', 'cancel', 'return']):
            return "refund_request"
        else:
            return "general_inquiry"
    
    def _assess_resolution_status(self, text: str, message_count: int) -> str:
        """Assess if the conversation was resolved"""
        text_lower = text.lower()
        
        resolution_indicators = ['thank you', 'thanks', 'solved', 'resolved', 'fixed', 'perfect']
        escalation_indicators = ['manager', 'supervisor', 'escalate', 'not satisfied']
        
        if any(indicator in text_lower for indicator in resolution_indicators):
            return "resolved"
        elif any(indicator in text_lower for indicator in escalation_indicators):
            return "escalated"
        elif message_count > 10:
            return "pending"
        else:
            return "in_progress"
    
    def _extract_key_insights(self, text: str, sentiment: str, intent: str) -> List[str]:
        """Extract actionable business insights"""
        insights = []
        
        # Sentiment-based insights
        if sentiment == "negative":
            insights.append("Customer expressed dissatisfaction - follow-up recommended")
        elif sentiment == "positive":
            insights.append("Positive customer interaction - potential for testimonial/review")
        
        # Intent-based insights
        if intent == "complaint":
            insights.append("Complaint identified - monitor for pattern recognition")
        elif intent == "sales_inquiry":
            insights.append("Sales opportunity - ensure proper follow-up")
        
        # General insights
        text_lower = text.lower()
        if 'competitor' in text_lower:
            insights.append("Competitor mentioned - competitive analysis opportunity")
        
        if any(word in text_lower for word in ['feature', 'improvement', 'suggestion']):
            insights.append("Product feedback received - forward to product team")
        
        return insights if insights else ["Standard customer interaction"]
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when LangExtract fails"""
        return {
            "sentiment": "neutral",
            "satisfaction_level": 5,
            "issues_raised": ["Analysis Failed"],
            "urgency_indicators": "low",
            "resolution_status": "unknown",
            "customer_intent": "unknown",
            "conversation_metrics": {
                "total_messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "conversation_length": 0,
                "avg_message_length": 0
            },
            "key_insights": self._get_error_insights(),
            "analysis_timestamp": datetime.now().isoformat(),
            "analysis_version": "fallback_v1.0",
            "error": "LangExtract analysis failed"
        }
    
    def _get_error_insights(self) -> List[str]:
        """Generate helpful error insights for troubleshooting"""
        insights = []
        
        if not self.langextract_available:
            insights.append("Install LangExtract with: pip install langextract")
        
        if not self.api_key:
            insights.append("Configure API key in Django admin under 'API Configurations'")
            insights.append("Supported providers: OpenAI, Gemini, Claude")
            
        if not insights:
            insights.append("Check logs for detailed error information")
            
        return insights
    
    def is_configured(self) -> bool:
        """Check if LangExtract is properly configured"""
        return self.langextract_available and bool(self.api_key)
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get detailed configuration status for admin dashboard"""
        try:
            from chat.models import APIConfiguration
            active_configs = APIConfiguration.objects.filter(is_active=True).count()
        except:
            active_configs = 0
            
        return {
            "langextract_installed": self.langextract_available,
            "api_key_configured": bool(self.api_key),
            "active_api_configurations": active_configs,
            "default_model": self.default_model,
            "ready_for_analysis": self.is_configured()
        }
    
    def batch_analyze_conversations(self, conversation_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze multiple conversations in batch"""
        results = []
        
        for conversation in conversation_list:
            messages = conversation.get('messages', [])
            analysis = self.analyze_conversation(messages)
            
            results.append({
                "conversation_id": conversation.get('id'),
                "analysis": analysis
            })
        
        return results
    
    def save_analysis_to_db(self, conversation_id: int, analysis_result: Dict[str, Any]) -> bool:
        """Save LangExtract analysis results to ConversationAnalysis model"""
        try:
            from analytics.models import ConversationAnalysis
            from chat.models import Conversation
            
            # Get the conversation
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Create or update analysis record
            analysis, created = ConversationAnalysis.objects.get_or_create(
                conversation=conversation,
                defaults={
                    'sentiment': analysis_result.get('sentiment', 'neutral'),
                    'satisfaction_level': analysis_result.get('satisfaction_level', 5),
                    'issues_raised': analysis_result.get('issues_raised', []),
                    'urgency_indicators': analysis_result.get('urgency_indicators', []),
                    'resolution_status': analysis_result.get('resolution_status', 'pending'),
                    'customer_intent': analysis_result.get('customer_intent', 'unknown'),
                    'key_insights': analysis_result.get('key_insights', []),
                    'source_spans': analysis_result.get('source_spans', []),
                    'confidence_score': analysis_result.get('confidence_score', 0.0),
                    'langextract_model_used': analysis_result.get('model_used', self.default_model),
                    'processing_time': analysis_result.get('processing_time', 0.0)
                }
            )
            
            # If not created, update existing record
            if not created:
                analysis.sentiment = analysis_result.get('sentiment', analysis.sentiment)
                analysis.satisfaction_level = analysis_result.get('satisfaction_level', analysis.satisfaction_level)
                analysis.issues_raised = analysis_result.get('issues_raised', analysis.issues_raised)
                analysis.urgency_indicators = analysis_result.get('urgency_indicators', analysis.urgency_indicators)
                analysis.resolution_status = analysis_result.get('resolution_status', analysis.resolution_status)
                analysis.customer_intent = analysis_result.get('customer_intent', analysis.customer_intent)
                analysis.key_insights = analysis_result.get('key_insights', analysis.key_insights)
                analysis.source_spans = analysis_result.get('source_spans', analysis.source_spans)
                analysis.confidence_score = analysis_result.get('confidence_score', analysis.confidence_score)
                analysis.langextract_model_used = analysis_result.get('model_used', analysis.langextract_model_used)
                analysis.processing_time = analysis_result.get('processing_time', analysis.processing_time)
                analysis.save()
            
            logger.info(f"Successfully saved LangExtract analysis for conversation {conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save analysis to database: {e}")
            return False
    
    def analyze_and_save_conversation(self, conversation_id: int) -> Dict[str, Any]:
        """Analyze a conversation and save results to database"""
        try:
            from chat.models import Conversation
            
            # Get conversation messages
            conversation = Conversation.objects.get(id=conversation_id)
            messages = []
            for msg in conversation.messages.all():
                messages.append({
                    'role': 'user' if msg.sender_type == 'user' else 'assistant',
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                })
            
            if not messages:
                return {
                    'success': False,
                    'error': 'No messages found in conversation'
                }
            
            # Perform analysis
            start_time = time.time()
            analysis_result = self.analyze_conversation(messages)
            processing_time = time.time() - start_time
            
            # Add processing time to result
            analysis_result['processing_time'] = processing_time
            
            # Save to database
            saved = self.save_analysis_to_db(conversation_id, analysis_result)
            
            return {
                'success': saved,
                'analysis': analysis_result,
                'conversation_id': conversation_id,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze and save conversation {conversation_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'conversation_id': conversation_id
            }
    
    def bulk_analyze_conversations(self, conversation_ids: List[int] = None) -> Dict[str, Any]:
        """Analyze multiple conversations and save to database"""
        try:
            from chat.models import Conversation
            
            # Get conversations to analyze
            if conversation_ids:
                conversations = Conversation.objects.filter(id__in=conversation_ids)
            else:
                # Analyze conversations without existing analysis
                conversations = Conversation.objects.filter(analysis__isnull=True)[:50]  # Limit to 50
            
            total_conversations = conversations.count()
            logger.info(f"Starting bulk analysis of {total_conversations} conversations")
            
            results = {
                'success': 0,
                'failed': 0,
                'results': [],
                'errors': []
            }
            
            for i, conversation in enumerate(conversations, 1):
                logger.info(f"Processing conversation {i}/{total_conversations} (ID: {conversation.id})")
                
                # Check if conversation has messages
                message_count = conversation.messages.count()
                if message_count == 0:
                    logger.warning(f"Skipping conversation {conversation.id}: no messages")
                    results['failed'] += 1
                    results['errors'].append({
                        'conversation_id': conversation.id,
                        'error': 'No messages in conversation'
                    })
                    continue
                
                logger.info(f"Analyzing conversation {conversation.id} with {message_count} messages")
                
                # Perform analysis
                result = self.analyze_and_save_conversation(conversation.id)
                
                if result['success']:
                    results['success'] += 1
                    logger.info(f"Successfully analyzed conversation {conversation.id}")
                else:
                    results['failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Failed to analyze conversation {conversation.id}: {error_msg}")
                    results['errors'].append({
                        'conversation_id': conversation.id,
                        'error': error_msg
                    })
                    
                results['results'].append(result)
            
            logger.info(f"Bulk analysis completed: {results['success']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Bulk analysis failed: {e}")
            return {
                'success': 0,
                'failed': 0,
                'error': str(e),
                'results': [],
                'errors': []
            }
    
    def bulk_analyze_conversations_with_progress(self, conversation_ids: List[int], request=None) -> Dict[str, Any]:
        """Analyze multiple conversations with real-time progress updates"""
        try:
            from chat.models import Conversation
            
            # Get conversations to analyze
            conversations = Conversation.objects.filter(id__in=conversation_ids)
            total_conversations = conversations.count()
            
            logger.info(f"Starting bulk analysis of {total_conversations} conversations with progress tracking")
            
            results = {
                'success': 0,
                'failed': 0,
                'results': [],
                'errors': []
            }
            
            def update_progress(status, current_step, processed=None, success_count=None, error_count=None):
                """Update progress in session"""
                if request and hasattr(request, 'session'):
                    try:
                        progress = request.session.get('langextract_progress', {})
                        progress['status'] = status
                        progress['current_step'] = current_step
                        if processed is not None:
                            progress['processed'] = processed
                        if success_count is not None:
                            progress['success_count'] = success_count
                        if error_count is not None:
                            progress['error_count'] = error_count
                        request.session['langextract_progress'] = progress
                        request.session.save()
                        logger.info(f"Progress updated: {status} - {current_step}")
                    except Exception as e:
                        logger.error(f"Failed to update progress: {e}")
            
            # Update initial progress
            update_progress('processing', 'Starting analysis...', 0, 0, 0)
            
            for i, conversation in enumerate(conversations, 1):
                # Update progress for current conversation
                update_progress(
                    'processing', 
                    f'Analyzing conversation {i}/{total_conversations} (ID: {conversation.id})',
                    i-1,
                    results['success'],
                    results['failed']
                )
                
                logger.info(f"Processing conversation {i}/{total_conversations} (ID: {conversation.id})")
                
                # Check if conversation has messages
                message_count = conversation.messages.count()
                if message_count == 0:
                    logger.warning(f"Skipping conversation {conversation.id}: no messages")
                    results['failed'] += 1
                    results['errors'].append({
                        'conversation_id': conversation.id,
                        'error': 'No messages in conversation'
                    })
                    continue
                
                logger.info(f"Analyzing conversation {conversation.id} with {message_count} messages")
                
                # Update progress with API call status
                update_progress(
                    'processing',
                    f'Calling Gemini API for conversation {conversation.id}...',
                    i-1,
                    results['success'],
                    results['failed']
                )
                
                # Perform analysis
                result = self.analyze_and_save_conversation(conversation.id)
                
                if result['success']:
                    results['success'] += 1
                    logger.info(f"Successfully analyzed conversation {conversation.id}")
                else:
                    results['failed'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Failed to analyze conversation {conversation.id}: {error_msg}")
                    results['errors'].append({
                        'conversation_id': conversation.id,
                        'error': error_msg
                    })
                    
                results['results'].append(result)
                
                # Update progress after processing
                update_progress(
                    'processing',
                    f'Completed conversation {i}/{total_conversations}',
                    i,
                    results['success'],
                    results['failed']
                )
            
            # Final progress update
            update_progress(
                'completed',
                f'Analysis complete: {results["success"]} successful, {results["failed"]} failed',
                total_conversations,
                results['success'],
                results['failed']
            )
            
            logger.info(f"Bulk analysis completed: {results['success']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Bulk analysis failed: {e}")
            
            # Update progress with error status
            if request and request.session:
                progress = request.session.get('langextract_progress', {})
                progress['status'] = 'error'
                progress['current_step'] = f'Analysis failed: {str(e)}'
                request.session['langextract_progress'] = progress
                request.session.save()
            
            return {
                'success': 0,
                'failed': 0,
                'error': str(e),
                'results': [],
                'errors': []
            }
    
    def get_analytics_summary(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary analytics from multiple conversation analyses"""
        if not analyses:
            return {"error": "No analyses provided"}
        
        total_conversations = len(analyses)
        sentiments = [a.get('analysis', {}).get('sentiment', 'neutral') for a in analyses]
        satisfaction_scores = [a.get('analysis', {}).get('satisfaction_level', 5) for a in analyses]
        
        sentiment_counts = {
            'positive': sentiments.count('positive'),
            'negative': sentiments.count('negative'),
            'neutral': sentiments.count('neutral')
        }
        
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        
        return {
            "total_conversations_analyzed": total_conversations,
            "sentiment_distribution": sentiment_counts,
            "average_satisfaction": round(avg_satisfaction, 2),
            "high_satisfaction_rate": len([s for s in satisfaction_scores if s >= 7]) / total_conversations * 100,
            "analysis_generated_at": datetime.now().isoformat()
        }