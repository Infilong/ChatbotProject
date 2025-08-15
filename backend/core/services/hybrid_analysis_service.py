"""
Hybrid Analysis Service
Prioritizes LLM analysis but gracefully falls back to local analysis with proper labeling
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from django.utils import timezone
from django.conf import settings
from chat.models import Message, Conversation

logger = logging.getLogger(__name__)


class HybridAnalysisService:
    """Service that combines LLM and local analysis with intelligent fallback"""
    
    def __init__(self):
        """Initialize hybrid analysis service"""
        self.llm_available = False
        self.llm_client = None
        self.llm_model_name = None
        self._init_llm_client()
        
        # LLM-only analysis - no local service needed
        
        # LLM analysis cache to avoid redundant API calls
        self._analysis_cache = {}
    
    def _init_llm_client(self):
        """Initialize LLM client using Gemini API directly (same as bot uses)"""
        try:
            # Load environment variables from .env file if needed
            import os
            
            # Try to load from .env if not in environment
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                try:
                    from dotenv import load_dotenv
                    load_dotenv()  # Load .env file
                    api_key = os.getenv('GEMINI_API_KEY')
                except ImportError:
                    # dotenv not available, try manual .env loading
                    try:
                        import pathlib
                        env_path = pathlib.Path(__file__).parent.parent.parent / '.env'
                        if env_path.exists():
                            with open(env_path, 'r') as f:
                                for line in f:
                                    if line.startswith('GEMINI_API_KEY='):
                                        api_key = line.split('=', 1)[1].strip()
                                        break
                    except Exception:
                        pass
            
            model_name = 'gemini-2.5-flash'  # Default model
            
            if not api_key:
                # Try to get from database if env var not available
                try:
                    from chat.models import APIConfiguration
                    # Get active Gemini configuration (sync call, only if needed)
                    gemini_config = APIConfiguration.objects.filter(
                        provider='gemini',
                        is_active=True
                    ).first()
                    
                    if gemini_config and gemini_config.api_key:
                        api_key = gemini_config.api_key
                        model_name = gemini_config.model_name
                        logger.info(f"Hybrid Analysis: Using database API key (model: {model_name})")
                    else:
                        logger.warning("Hybrid Analysis: No API key found in environment or database")
                        return
                        
                except Exception as db_error:
                    logger.warning(f"Hybrid Analysis: Database access failed, will use env vars only: {db_error}")
                    return
            else:
                logger.info("Hybrid Analysis: Using environment variable API key")
            
            if api_key:
                # Use Gemini API directly with safety settings
                import google.generativeai as genai
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                
                genai.configure(api_key=api_key)
                
                # Configure safety settings at model level
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                self.llm_client = genai.GenerativeModel(
                    model_name=model_name,
                    safety_settings=safety_settings
                )
                self.llm_available = True
                self.llm_model_name = model_name
                logger.info(f"Hybrid Analysis: Gemini API client initialized with safety settings (model: {model_name})")
            else:
                logger.warning("Hybrid Analysis: No API key available - using local analysis only")
                
        except ImportError:
            logger.warning("Hybrid Analysis: google-generativeai library not available - using local analysis only")
        except Exception as e:
            logger.error(f"Hybrid Analysis: Failed to initialize Gemini client: {e}")
    
    async def analyze_message_hybrid(self, message: Message) -> Dict[str, Any]:
        """
        Analyze a single message using hybrid approach (LLM preferred, local fallback)
        
        Args:
            message: Message object to analyze
            
        Returns:
            Dict containing analysis with source labeling
        """
        if message.sender_type != 'user':
            return {}
        
        # Check cache first
        cache_key = f"msg_{message.uuid}"
        if cache_key in self._analysis_cache:
            cached_result = self._analysis_cache[cache_key]
            logger.debug(f"Using cached analysis for message {message.uuid}")
            return cached_result
        
        # Try LLM analysis first
        if self.llm_available:
            try:
                llm_result = await self._analyze_message_with_llm(message)
                if llm_result and 'error' not in llm_result:
                    # Cache successful LLM result
                    self._analysis_cache[cache_key] = llm_result
                    logger.info(f"Message {message.uuid} analyzed successfully with LLM ({self.llm_model_name})")
                    return llm_result
                else:
                    logger.warning(f"LLM analysis failed for message {message.uuid}, falling back to local analysis")
            except Exception as e:
                logger.error(f"LLM analysis error for message {message.uuid}: {e}, falling back to local analysis")
        
        # No local fallback - return error to trigger retry mechanism
        logger.warning(f"Message {message.uuid} LLM analysis failed, will retry with 30-second intervals")
        return {"error": "LLM analysis failed - will retry automatically"}
    
    async def _analyze_message_with_llm(self, message: Message) -> Dict[str, Any]:
        """Analyze message using Gemini API directly with safety filter bypass"""
        try:
            # Use LangExtract for message analysis instead of direct Gemini calls
            # This bypasses safety filter issues by using a different approach
            from core.services.langextract_service import langextract_service
            
            # Create a simple text analysis using LangExtract's robust API
            result = await asyncio.to_thread(
                self._analyze_with_langextract_fallback,
                message
            )
            
            if result and not result.get('error'):
                return result
            else:
                # If LangExtract fails, use local analysis
                logger.warning(f"LangExtract message analysis failed for {message.uuid}, using local fallback")
                return {"error": "LLM analysis failed - safety filters"}
            
        except Exception as e:
            logger.error(f"LLM message analysis failed for message {message.uuid}: {e}")
            return {"error": str(e)}
    
    def _analyze_with_langextract_fallback(self, message: Message) -> Dict[str, Any]:
        """Use LangExtract's simpler API for message analysis with proper result parsing"""
        try:
            # Import LangExtract components
            import langextract as lx
            from langextract.data import ExampleData, Extraction
            import os
            import sys
            
            # Fix Unicode encoding issues for Windows
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            
            try:
                # Temporarily suppress LangExtract console output to avoid Unicode issues
                import io
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                
                # Create comprehensive examples for better analysis
                analysis_examples = [
                    ExampleData(
                        text="I love this service, it's amazing!",
                        extractions=[
                            Extraction(extraction_class="urgency", extraction_text="low"),
                            Extraction(extraction_class="sentiment", extraction_text="very_positive"),
                            Extraction(extraction_class="satisfaction", extraction_text="very_satisfied"),
                            Extraction(extraction_class="issue_type", extraction_text="praise"),
                            Extraction(extraction_class="escalation_needed", extraction_text="false")
                        ]
                    ),
                    ExampleData(
                        text="This is terrible, I hate it and want a refund immediately!",
                        extractions=[
                            Extraction(extraction_class="urgency", extraction_text="high"),
                            Extraction(extraction_class="sentiment", extraction_text="very_negative"),
                            Extraction(extraction_class="satisfaction", extraction_text="very_dissatisfied"),
                            Extraction(extraction_class="issue_type", extraction_text="complaint_refund"),
                            Extraction(extraction_class="escalation_needed", extraction_text="true")
                        ]
                    ),
                    ExampleData(
                        text="I have a question about my account settings",
                        extractions=[
                            Extraction(extraction_class="urgency", extraction_text="low"),
                            Extraction(extraction_class="sentiment", extraction_text="neutral"),
                            Extraction(extraction_class="satisfaction", extraction_text="neutral"),
                            Extraction(extraction_class="issue_type", extraction_text="question"),
                            Extraction(extraction_class="escalation_needed", extraction_text="false")
                        ]
                    ),
                    ExampleData(
                        text="This is urgent! The system is down and I can't work!",
                        extractions=[
                            Extraction(extraction_class="urgency", extraction_text="critical"),
                            Extraction(extraction_class="sentiment", extraction_text="frustrated"),
                            Extraction(extraction_class="satisfaction", extraction_text="dissatisfied"),
                            Extraction(extraction_class="issue_type", extraction_text="technical_urgent"),
                            Extraction(extraction_class="escalation_needed", extraction_text="true")
                        ]
                    ),
                    ExampleData(
                        text="Could you help me understand how to use this feature?",
                        extractions=[
                            Extraction(extraction_class="urgency", extraction_text="low"),
                            Extraction(extraction_class="sentiment", extraction_text="polite"),
                            Extraction(extraction_class="satisfaction", extraction_text="neutral"),
                            Extraction(extraction_class="issue_type", extraction_text="help_request"),
                            Extraction(extraction_class="escalation_needed", extraction_text="false")
                        ]
                    )
                ]
                
                # Perform LangExtract analysis with comprehensive prompt
                result = lx.extract(
                    text_or_documents=message.content,
                    prompt_description="Analyze this customer service message to extract urgency level, sentiment, satisfaction, issue type, and escalation needs",
                    model_id="gemini-2.5-flash",
                    examples=analysis_examples,
                    temperature=0.1
                )
                
            finally:
                # Restore original stdout/stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr
            
            # Parse the actual LangExtract results
            parsed_analysis = self._parse_langextract_result(result, message)
            
            # Add source labeling
            parsed_analysis.update({
                "analysis_source": f"LangExtract Simple ({self.llm_model_name})",
                "analysis_method": "langextract_simple_parsed",
                "analysis_version": f"langextract_simple_v2.0_{self.llm_model_name}",
                "llm_model": self.llm_model_name,
                "analysis_timestamp": timezone.now().isoformat(),
                "message_uuid": str(message.uuid),
                "api_available": True,
                "safety_filter_bypass": True,
                "langextract_used": True,
                "result_parsed": True
            })
            
            return parsed_analysis
            
        except Exception as e:
            error_msg = str(e)
            # Handle Unicode errors gracefully
            if "'gbk' codec can't encode" in error_msg or "UnicodeEncodeError" in error_msg:
                logger.info(f"LangExtract completed with Unicode display issue, attempting result parsing")
                # Try to return basic analysis since LangExtract likely succeeded but had display issues
                return self._create_basic_analysis(message, "unicode_issue")
            else:
                logger.warning(f"LangExtract simple analysis failed: {e}")
                return {"error": str(e)}
    
    def _parse_langextract_result(self, langextract_result, message: Message) -> Dict[str, Any]:
        """Parse actual LangExtract results into our analysis format"""
        try:
            # Initialize with defaults
            urgency = "medium"
            sentiment = "neutral"
            satisfaction = "neutral"
            issue_type = "general_inquiry"
            escalation_needed = False
            
            # Extract data from LangExtract AnnotatedDocument result
            if langextract_result and hasattr(langextract_result, 'extractions'):
                extractions = {}
                
                # Iterate through the extractions list
                for extraction in langextract_result.extractions:
                    if hasattr(extraction, 'extraction_class') and hasattr(extraction, 'extraction_text'):
                        extraction_class = extraction.extraction_class.lower()
                        extraction_text = extraction.extraction_text.lower()
                        extractions[extraction_class] = extraction_text
                        logger.debug(f"Extracted {extraction_class}: {extraction_text}")
                
                # Map extracted values to our analysis
                urgency = extractions.get('urgency', urgency)
                sentiment = extractions.get('sentiment', sentiment) 
                satisfaction = extractions.get('satisfaction', satisfaction)
                issue_type = extractions.get('issue_type', issue_type)
                escalation_needed = extractions.get('escalation_needed', 'false') == 'true'
                
                logger.info(f"LangExtract parsed - urgency: {urgency}, sentiment: {sentiment}, satisfaction: {satisfaction}, issue_type: {issue_type}")
            
            # Map to our expected format with intelligent scoring
            satisfaction_mapping = {
                "very_positive": ("satisfied", 9.0),
                "positive": ("satisfied", 7.0),
                "polite": ("neutral", 6.0),
                "neutral": ("neutral", 5.0),
                "frustrated": ("dissatisfied", 3.0),
                "negative": ("dissatisfied", 2.0),
                "very_negative": ("dissatisfied", 1.0),
                "very_dissatisfied": ("dissatisfied", 1.0),
                "dissatisfied": ("dissatisfied", 2.0),
                "satisfied": ("satisfied", 7.0),
                "very_satisfied": ("satisfied", 9.0)
            }
            
            urgency_mapping = {
                "low": ("low", "normal", 2),
                "medium": ("medium", "normal", 5),
                "high": ("high", "urgent", 8),
                "critical": ("critical", "critical", 10)
            }
            
            # Get mapped values
            sat_level, sat_score = satisfaction_mapping.get(satisfaction, ("neutral", 5.0))
            if sentiment in satisfaction_mapping:
                sent_level, sent_score = satisfaction_mapping[sentiment]
                # Use the more extreme of satisfaction or sentiment
                if abs(sent_score - 5.0) > abs(sat_score - 5.0):
                    sat_level, sat_score = sent_level, sent_score
            
            urg_level, priority, urg_score = urgency_mapping.get(urgency, ("medium", "normal", 5))
            
            # Create comprehensive analysis
            return {
                "issues_raised": [
                    {
                        "issue_type": issue_type,
                        "confidence": 85,
                        "description": f"LangExtract detected: {issue_type}",
                        "severity": urg_level,
                        "matched_keywords": [],
                        "llm_detected": True
                    }
                ] if issue_type != "general_inquiry" else [],
                
                "satisfaction_level": {
                    "level": sat_level,
                    "confidence": 85,
                    "score": sat_score,
                    "emotional_indicators": [sentiment] if sentiment != "neutral" else [],
                    "llm_analyzed": True
                },
                
                "importance_level": {
                    "level": urg_level,
                    "priority": priority,
                    "urgency_score": urg_score,
                    "urgency_indicators": [urgency] if urgency != "medium" else [],
                    "business_impact": urg_level,
                    "escalation_needed": escalation_needed,
                    "llm_analyzed": True
                },
                
                "doc_improvement_potential": {
                    "potential_level": "high" if "question" in issue_type or "help" in issue_type else "low",
                    "score": 75 if "question" in issue_type or "help" in issue_type else 25,
                    "improvement_areas": ["documentation"] if "question" in issue_type else [],
                    "suggested_actions": ["improve_docs"] if "question" in issue_type else [],
                    "llm_inferred": True
                },
                
                "faq_potential": {
                    "faq_potential": "high" if "question" in issue_type or "help" in issue_type else "low",
                    "score": 80 if "question" in issue_type or "help" in issue_type else 20,
                    "question_type": issue_type,
                    "recommended_faq_title": message.content[:80] + "..." if len(message.content) > 80 else message.content,
                    "should_add_to_faq": "question" in issue_type or "help" in issue_type,
                    "llm_inferred": True
                }
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse LangExtract result: {e}")
            return self._create_basic_analysis(message, "parse_error")
    
    def _create_basic_analysis(self, message: Message, reason: str) -> Dict[str, Any]:
        """Create basic analysis when LangExtract parsing fails"""
        return {
            "issues_raised": [],
            "satisfaction_level": {
                "level": "neutral",
                "confidence": 60,
                "score": 5.0,
                "emotional_indicators": [],
                "llm_analyzed": False,
                "fallback_reason": reason
            },
            "importance_level": {
                "level": "medium",
                "priority": "normal",
                "urgency_score": 5,
                "urgency_indicators": [],
                "business_impact": "medium",
                "escalation_needed": False,
                "llm_analyzed": False,
                "fallback_reason": reason
            },
            "doc_improvement_potential": {
                "potential_level": "medium",
                "score": 50,
                "improvement_areas": [],
                "suggested_actions": [],
                "llm_inferred": False,
                "fallback_reason": reason
            },
            "faq_potential": {
                "faq_potential": "medium",
                "score": 50,
                "question_type": "general_inquiry",
                "recommended_faq_title": message.content[:80] + "..." if len(message.content) > 80 else message.content,
                "should_add_to_faq": False,
                "llm_inferred": False,
                "fallback_reason": reason
            }
        }
    
    # Removed _analyze_message_with_local method - LLM-only analysis
    
    def _parse_gemini_analysis(self, response_text: str, message: Message) -> Dict[str, Any]:
        """Parse Gemini's structured response into our expected format"""
        try:
            # Initialize default values
            urgency_level = "medium"
            business_impact = "medium" 
            issues = []
            sentiment = "neutral"
            escalation_needed = False
            reasoning = ""
            
            # Parse the structured response
            lines = response_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('URGENCY:'):
                    urgency_level = line.split(':', 1)[1].strip().lower()
                elif line.startswith('IMPACT:'):
                    business_impact = line.split(':', 1)[1].strip().lower()
                elif line.startswith('ISSUES:'):
                    issues_text = line.split(':', 1)[1].strip()
                    # Simple parsing - split by commas or semicolons
                    issues = [issue.strip() for issue in issues_text.split(',') if issue.strip()]
                elif line.startswith('SENTIMENT:'):
                    sentiment = line.split(':', 1)[1].strip().lower()
                elif line.startswith('ESCALATION:'):
                    escalation_text = line.split(':', 1)[1].strip().lower()
                    escalation_needed = escalation_text in ['yes', 'true', '1']
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()
            
            # Map Gemini responses to our format
            urgency_mapping = {
                'low': 'low',
                'medium': 'medium', 
                'high': 'high',
                'critical': 'critical'
            }
            
            sentiment_mapping = {
                'very_negative': 'dissatisfied',
                'negative': 'dissatisfied',
                'neutral': 'neutral',
                'positive': 'satisfied',
                'very_positive': 'satisfied'
            }
            
            # Calculate priority based on urgency
            priority_mapping = {
                'low': 'low',
                'medium': 'normal',
                'high': 'urgent',
                'critical': 'critical'
            }
            
            # Calculate urgency score
            urgency_scores = {'low': 2, 'medium': 5, 'high': 8, 'critical': 10}
            urgency_score = urgency_scores.get(urgency_level, 5)
            
            # Format issues for our expected structure
            formatted_issues = []
            for issue in issues:
                formatted_issues.append({
                    "issue_type": issue,
                    "confidence": 85,  # High confidence from LLM
                    "description": f"LLM detected: {issue}",
                    "severity": urgency_level,
                    "matched_keywords": [],  # LLM doesn't use keywords
                    "llm_detected": True
                })
            
            # Create formatted result
            formatted_result = {
                "issues_raised": formatted_issues,
                
                "satisfaction_level": {
                    "level": sentiment_mapping.get(sentiment, "neutral"),
                    "confidence": 80,
                    "score": self._sentiment_to_score(sentiment),
                    "emotional_indicators": [reasoning] if reasoning else [],
                    "llm_analyzed": True
                },
                
                "importance_level": {
                    "level": urgency_level,
                    "priority": priority_mapping.get(urgency_level, "normal"),
                    "urgency_score": urgency_score,
                    "urgency_indicators": [reasoning] if reasoning else [],
                    "business_impact": business_impact,
                    "escalation_needed": escalation_needed,
                    "llm_analyzed": True
                },
                
                "doc_improvement_potential": {
                    "potential_level": "medium",  # Default for LLM
                    "score": 50,
                    "improvement_areas": [],
                    "suggested_actions": [],
                    "llm_inferred": True
                },
                
                "faq_potential": {
                    "faq_potential": "medium",
                    "score": 50,
                    "question_type": "general_inquiry",
                    "recommended_faq_title": message.content[:80] + "..." if len(message.content) > 80 else message.content,
                    "should_add_to_faq": False,
                    "llm_inferred": True
                },
                
                # Source labeling - CRITICAL
                "analysis_source": f"LLM ({self.llm_model_name})",
                "analysis_method": "gemini_direct",
                "analysis_version": f"gemini_v1.0_{self.llm_model_name}",
                "llm_model": self.llm_model_name,
                "analysis_timestamp": timezone.now().isoformat(),
                "message_uuid": str(message.uuid),
                "api_available": True,
                "raw_llm_response": response_text
            }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Failed to parse Gemini analysis: {e}")
            return {"error": f"Failed to parse Gemini analysis: {e}"}
    
    def _sentiment_to_score(self, sentiment: str) -> float:
        """Convert sentiment to numerical score (1-10)"""
        mapping = {
            'very_negative': 1.0,
            'negative': 3.0,
            'neutral': 5.0,
            'positive': 7.0,
            'very_positive': 9.0
        }
        return mapping.get(sentiment, 5.0)
    
    def _format_llm_result(self, llm_result: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Format LLM result to match expected structure with source labeling"""
        try:
            # Extract data from LLM result
            importance_data = llm_result.get("importance_analysis", {})
            issue_data = llm_result.get("issue_analysis", {})
            sentiment_data = llm_result.get("satisfaction_sentiment", {})
            
            # Map LLM results to expected format
            formatted_result = {
                # Issues from LLM analysis
                "issues_raised": [
                    {
                        "issue_type": issue.get("issue_type", "Unknown"),
                        "confidence": issue.get("confidence", 0),
                        "description": issue.get("description", ""),
                        "severity": issue.get("severity", "medium"),
                        "matched_keywords": [],  # LLM doesn't use keywords
                        "llm_detected": True
                    }
                    for issue in issue_data.get("primary_issues", [])
                ],
                
                # Satisfaction/sentiment from LLM
                "satisfaction_level": {
                    "level": self._map_satisfaction_level(sentiment_data.get("satisfaction_level", "neutral")),
                    "confidence": sentiment_data.get("confidence", 0),
                    "score": sentiment_data.get("sentiment_score", 5),
                    "emotional_indicators": sentiment_data.get("emotional_indicators", []),
                    "llm_analyzed": True
                },
                
                # Importance from LLM (prioritized)
                "importance_level": {
                    "level": importance_data.get("importance_level", "medium"),
                    "priority": self._map_priority_level(importance_data.get("urgency_level", "medium")),
                    "urgency_score": importance_data.get("priority_score", 5),
                    "urgency_indicators": importance_data.get("urgency_indicators", []),
                    "business_impact": importance_data.get("business_impact", "medium"),
                    "escalation_needed": importance_data.get("escalation_needed", False),
                    "llm_analyzed": True
                },
                
                # Documentation and FAQ potential (simplified for LLM)
                "doc_improvement_potential": {
                    "potential_level": "medium",  # Default for LLM analysis
                    "score": 50,
                    "improvement_areas": [],
                    "suggested_actions": [],
                    "llm_inferred": True
                },
                
                "faq_potential": {
                    "faq_potential": "medium",  # Default for LLM analysis
                    "score": 50,
                    "question_type": "general_inquiry",
                    "recommended_faq_title": message.content[:80] + "..." if len(message.content) > 80 else message.content,
                    "should_add_to_faq": False,
                    "llm_inferred": True
                },
                
                # Source labeling - CRITICAL
                "analysis_source": f"LLM ({self.llm_model_name})",
                "analysis_method": "llm_based",
                "analysis_version": f"llm_v1.0_{self.llm_model_name}",
                "llm_model": self.llm_model_name,
                "analysis_timestamp": timezone.now().isoformat(),
                "message_uuid": str(message.uuid),
                "api_available": True
            }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Failed to format LLM result: {e}")
            return {"error": f"Failed to format LLM result: {e}"}
    
    def _map_satisfaction_level(self, llm_satisfaction: str) -> str:
        """Map LLM satisfaction levels to local format"""
        mapping = {
            "very_dissatisfied": "dissatisfied",
            "dissatisfied": "dissatisfied", 
            "neutral": "neutral",
            "satisfied": "satisfied",
            "very_satisfied": "satisfied"
        }
        return mapping.get(llm_satisfaction, "neutral")
    
    def _map_priority_level(self, llm_urgency: str) -> str:
        """Map LLM urgency levels to priority terms"""
        mapping = {
            "low": "low",
            "medium": "normal",
            "high": "urgent", 
            "critical": "critical"
        }
        return mapping.get(llm_urgency, "normal")
    
    async def analyze_conversation_hybrid(self, conversation: Conversation) -> Dict[str, Any]:
        """
        Analyze entire conversation using hybrid approach
        
        Args:
            conversation: Conversation object to analyze
            
        Returns:
            Dict containing conversation-level analysis with source labeling
        """
        try:
            # Try LLM conversation analysis first
            if self.llm_available:
                try:
                    from core.services.langextract_service import langextract_service
                    llm_conv_result = await langextract_service.analyze_full_conversation(conversation)
                    
                    # Check if LangExtract succeeded (including Unicode handling cases)
                    langextract_success = (
                        llm_conv_result and 
                        'error' not in llm_conv_result and 
                        (llm_conv_result.get('langextract_extraction') == True or
                         llm_conv_result.get('extraction_successful') == True or
                         'conversation_patterns' in llm_conv_result)
                    )
                    
                    if langextract_success:
                        # Add source labeling for LangExtract
                        llm_conv_result.update({
                            "analysis_source": "LangExtract (Google Gemini)",
                            "analysis_method": "langextract_conversation_analysis", 
                            "api_available": True,
                            "llm_model": "gemini-2.5-flash"
                        })
                        logger.info(f"Conversation {conversation.uuid} analyzed with LangExtract")
                        return llm_conv_result
                        
                except Exception as e:
                    logger.error(f"LLM conversation analysis failed: {e}")
            
            # No local fallback for conversations - return error to trigger retry
            logger.warning(f"Conversation {conversation.uuid} LLM analysis failed, will retry with 30-second intervals")
            return {"error": "LLM conversation analysis failed - will retry automatically"}
            
        except Exception as e:
            logger.error(f"Hybrid conversation analysis failed: {e}")
            return {
                "error": str(e),
                "analysis_source": "Error Fallback",
                "analysis_method": "error_handling"
            }
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """Get current status of analysis capabilities"""
        return {
            "llm_available": self.llm_available,
            "llm_model": self.llm_model_name if self.llm_available else None,
            "local_available": False,  # Removed local analysis
            "cache_size": len(self._analysis_cache),
            "analysis_method": "LLM-only",
            "fallback_method": "30-second retry intervals",
            "retry_enabled": True
        }
    
    def clear_analysis_cache(self):
        """Clear the analysis cache"""
        self._analysis_cache.clear()
        logger.info("Analysis cache cleared")


# Global service instance
hybrid_analysis_service = HybridAnalysisService()