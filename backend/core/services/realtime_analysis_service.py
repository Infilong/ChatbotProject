"""
Real-Time Analysis Service
Provides immediate issue extraction, sentiment analysis, and urgency assessment during conversations
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from django.utils import timezone

from chat.models import Conversation, Message
from .langextract_service import langextract_service

logger = logging.getLogger(__name__)


class RealtimeAnalysisService:
    """Service for real-time conversation analysis during chat interactions"""
    
    def __init__(self):
        self.langextract_service = langextract_service
    
    async def analyze_message_realtime(self, message: Message) -> Dict[str, Any]:
        """
        Analyze a single message in real-time for immediate insights
        
        Args:
            message: Message object to analyze
            
        Returns:
            Dict containing real-time analysis results
        """
        try:
            # Only analyze user messages for real-time insights
            if message.sender_type != 'user':
                return {"type": "bot_message", "analysis": "skipped"}
            
            # Quick sentiment analysis
            sentiment_analysis = await self._quick_sentiment_analysis(message.content)
            
            # Quick issue detection
            issue_detection = await self._quick_issue_detection(message.content)
            
            # Quick urgency assessment
            urgency_assessment = await self._quick_urgency_assessment(message.content, sentiment_analysis)
            
            # Escalation recommendation
            escalation_check = await self._check_escalation_needed(
                message, sentiment_analysis, issue_detection, urgency_assessment
            )
            
            # Combine results
            analysis_result = {
                "message_id": str(message.uuid),
                "timestamp": message.timestamp.isoformat(),
                "sentiment": sentiment_analysis,
                "issues": issue_detection,
                "urgency": urgency_assessment,
                "escalation": escalation_check,
                "analysis_type": "realtime",
                "requires_attention": (
                    sentiment_analysis.get("score", 0) < -0.5 or 
                    urgency_assessment.get("level") in ["high", "critical"] or
                    escalation_check.get("recommended", False)
                )
            }
            
            # Store analysis in message metadata
            if not message.metadata:
                message.metadata = {}
            message.metadata["realtime_analysis"] = analysis_result
            await message.asave(update_fields=['metadata'])
            
            logger.info(f"Completed real-time analysis for message {message.uuid}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed real-time analysis for message {message.uuid}: {e}")
            return {"error": str(e), "message_id": str(message.uuid)}
    
    async def analyze_conversation_realtime(self, conversation: Conversation, recent_messages: int = 3) -> Dict[str, Any]:
        """
        Analyze recent conversation context for real-time insights
        
        Args:
            conversation: Conversation to analyze
            recent_messages: Number of recent messages to analyze
            
        Returns:
            Dict containing conversation-level real-time analysis
        """
        try:
            # Get recent messages
            messages = await conversation.messages.order_by('-timestamp')[:recent_messages].aall()
            
            if not messages:
                return {"status": "no_messages"}
            
            # Analyze conversation flow
            conversation_flow = await self._analyze_conversation_flow(messages)
            
            # Detect conversation issues
            conversation_issues = await self._detect_conversation_issues(messages)
            
            # Check for escalation triggers
            escalation_triggers = await self._check_conversation_escalation(messages, conversation_flow)
            
            # Sentiment trend analysis
            sentiment_trend = await self._analyze_sentiment_trend(messages)
            
            # Customer satisfaction indicators
            satisfaction_indicators = await self._assess_customer_satisfaction(messages, sentiment_trend)
            
            analysis_result = {
                "conversation_id": str(conversation.uuid),
                "analyzed_messages": len(messages),
                "timestamp": timezone.now().isoformat(),
                "conversation_flow": conversation_flow,
                "issues": conversation_issues,
                "escalation": escalation_triggers,
                "sentiment_trend": sentiment_trend,
                "satisfaction": satisfaction_indicators,
                "analysis_type": "realtime_conversation",
                "alerts": self._generate_realtime_alerts(
                    conversation_flow, conversation_issues, escalation_triggers, sentiment_trend
                )
            }
            
            # Update conversation metadata
            if not hasattr(conversation, 'langextract_analysis') or not conversation.langextract_analysis:
                conversation.langextract_analysis = {}
            
            conversation.langextract_analysis["realtime_analysis"] = analysis_result
            await conversation.asave(update_fields=['langextract_analysis'])
            
            logger.info(f"Completed real-time conversation analysis for {conversation.uuid}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed real-time conversation analysis for {conversation.uuid}: {e}")
            return {"error": str(e), "conversation_id": str(conversation.uuid)}
    
    async def _quick_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Fast sentiment analysis using keyword-based approach with LangExtract backup"""
        try:
            # Fast keyword-based sentiment analysis
            text_lower = text.lower()
            
            # Positive indicators
            positive_words = [
                'thank', 'thanks', 'great', 'excellent', 'perfect', 'wonderful',
                'awesome', 'fantastic', 'amazing', 'helpful', 'good', 'satisfied',
                'happy', 'pleased', 'love', 'appreciate'
            ]
            
            # Negative indicators
            negative_words = [
                'frustrated', 'angry', 'terrible', 'awful', 'horrible', 'bad',
                'hate', 'annoyed', 'disappointed', 'unsatisfied', 'problem',
                'issue', 'broken', 'not working', 'failed', 'error', 'bug'
            ]
            
            # Strong negative indicators (higher weight)
            strong_negative = [
                'furious', 'outraged', 'unacceptable', 'disaster', 'nightmare',
                'completely broken', 'totally useless', 'waste of time'
            ]
            
            # Count indicators
            positive_count = sum(1 for word in positive_words if word in text_lower)
            negative_count = sum(1 for word in negative_words if word in text_lower)
            strong_negative_count = sum(1 for phrase in strong_negative if phrase in text_lower)
            
            # Calculate sentiment score (-1 to 1)
            total_sentiment_indicators = positive_count + negative_count + strong_negative_count
            
            if total_sentiment_indicators == 0:
                sentiment_score = 0.0
                sentiment_label = "neutral"
            else:
                weighted_negative = negative_count + (strong_negative_count * 2)
                sentiment_score = (positive_count - weighted_negative) / (positive_count + weighted_negative)
                
                if sentiment_score > 0.3:
                    sentiment_label = "positive"
                elif sentiment_score < -0.3:
                    sentiment_label = "negative"
                else:
                    sentiment_label = "neutral"
            
            # Detect emotional intensity
            intensity_indicators = [
                'very', 'extremely', 'really', 'totally', 'completely', 
                'absolutely', 'so', 'quite', '!!!', 'CAPS'
            ]
            
            has_caps = any(word.isupper() and len(word) > 2 for word in text.split())
            intensity_count = sum(1 for indicator in intensity_indicators if indicator in text_lower)
            if has_caps:
                intensity_count += 1
            
            intensity = "high" if intensity_count > 2 else "medium" if intensity_count > 0 else "low"
            
            return {
                "score": round(sentiment_score, 2),
                "label": sentiment_label,
                "intensity": intensity,
                "positive_indicators": positive_count,
                "negative_indicators": negative_count,
                "strong_negative_indicators": strong_negative_count,
                "confidence": min(0.8, total_sentiment_indicators * 0.2),
                "method": "keyword_based"
            }
            
        except Exception as e:
            logger.error(f"Quick sentiment analysis failed: {e}")
            return {
                "score": 0.0,
                "label": "neutral",
                "intensity": "low",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _quick_issue_detection(self, text: str) -> Dict[str, Any]:
        """Fast issue detection using keyword patterns"""
        try:
            text_lower = text.lower()
            
            # Issue categories with keywords
            issue_patterns = {
                "technical": [
                    "error", "bug", "crash", "not working", "broken", "failed",
                    "won't load", "can't access", "connection", "timeout", "api"
                ],
                "billing": [
                    "charge", "payment", "invoice", "billing", "refund", "cancel",
                    "subscription", "price", "cost", "money", "credit card"
                ],
                "product_feature": [
                    "feature", "functionality", "how to", "can't find", "missing",
                    "where is", "how do i", "unable to", "option", "setting"
                ],
                "user_experience": [
                    "confusing", "complicated", "difficult", "hard to use",
                    "user interface", "ui", "design", "layout", "navigation"
                ],
                "integration": [
                    "integrate", "api", "connect", "sync", "import", "export",
                    "third party", "external", "webhook", "integration"
                ],
                "security": [
                    "security", "password", "login", "access", "permission",
                    "authentication", "unauthorized", "locked out", "hacked"
                ],
                "performance": [
                    "slow", "loading", "performance", "speed", "lag", "delay",
                    "timeout", "response time", "optimization"
                ]
            }
            
            detected_issues = []
            issue_indicators = {}
            
            for category, keywords in issue_patterns.items():
                matches = [keyword for keyword in keywords if keyword in text_lower]
                if matches:
                    detected_issues.append(category)
                    issue_indicators[category] = matches
            
            # Detect urgency keywords
            urgency_keywords = [
                "urgent", "asap", "immediately", "emergency", "critical",
                "right now", "can't wait", "deadline", "important"
            ]
            
            has_urgency = any(keyword in text_lower for keyword in urgency_keywords)
            
            # Detect frustration level
            frustration_indicators = [
                "frustrated", "annoyed", "angry", "fed up", "ridiculous",
                "unacceptable", "terrible", "awful", "horrible"
            ]
            
            frustration_level = sum(1 for indicator in frustration_indicators if indicator in text_lower)
            
            return {
                "categories": detected_issues,
                "indicators": issue_indicators,
                "has_urgency": has_urgency,
                "frustration_level": min(frustration_level, 3),  # Cap at 3
                "total_issues": len(detected_issues),
                "confidence": min(0.9, len(detected_issues) * 0.3)
            }
            
        except Exception as e:
            logger.error(f"Quick issue detection failed: {e}")
            return {
                "categories": [],
                "indicators": {},
                "has_urgency": False,
                "frustration_level": 0,
                "total_issues": 0,
                "error": str(e)
            }
    
    async def _quick_urgency_assessment(self, text: str, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Fast urgency assessment based on keywords and sentiment"""
        try:
            text_lower = text.lower()
            
            # Critical urgency indicators
            critical_indicators = [
                "emergency", "critical", "down", "outage", "can't work",
                "production", "live", "customers affected", "revenue impact"
            ]
            
            # High urgency indicators
            high_indicators = [
                "urgent", "asap", "immediately", "deadline", "time sensitive",
                "important", "priority", "needs attention"
            ]
            
            # Medium urgency indicators
            medium_indicators = [
                "soon", "when possible", "at your convenience", "sometime",
                "would like", "hoping"
            ]
            
            # Check indicators
            has_critical = any(indicator in text_lower for indicator in critical_indicators)
            has_high = any(indicator in text_lower for indicator in high_indicators)
            has_medium = any(indicator in text_lower for indicator in medium_indicators)
            
            # Consider sentiment in urgency
            sentiment_score = sentiment.get("score", 0)
            sentiment_intensity = sentiment.get("intensity", "low")
            
            # Determine urgency level
            if has_critical or (sentiment_score < -0.7 and sentiment_intensity == "high"):
                urgency_level = "critical"
                urgency_score = 4
            elif has_high or (sentiment_score < -0.5 and sentiment_intensity in ["medium", "high"]):
                urgency_level = "high"
                urgency_score = 3
            elif has_medium or sentiment_score < -0.2:
                urgency_level = "medium"
                urgency_score = 2
            else:
                urgency_level = "low"
                urgency_score = 1
            
            # Business impact assessment
            business_impact_indicators = [
                "revenue", "customers", "sales", "money", "loss", "impact",
                "business", "operations", "production", "clients"
            ]
            
            has_business_impact = any(indicator in text_lower for indicator in business_impact_indicators)
            
            return {
                "level": urgency_level,
                "score": urgency_score,
                "indicators": {
                    "critical": [ind for ind in critical_indicators if ind in text_lower],
                    "high": [ind for ind in high_indicators if ind in text_lower],
                    "medium": [ind for ind in medium_indicators if ind in text_lower]
                },
                "business_impact": has_business_impact,
                "sentiment_factor": sentiment_score < -0.3,
                "confidence": 0.8 if (has_critical or has_high) else 0.6
            }
            
        except Exception as e:
            logger.error(f"Quick urgency assessment failed: {e}")
            return {
                "level": "low",
                "score": 1,
                "indicators": {},
                "business_impact": False,
                "sentiment_factor": False,
                "error": str(e)
            }
    
    async def _check_escalation_needed(
        self, 
        message: Message, 
        sentiment: Dict[str, Any], 
        issues: Dict[str, Any], 
        urgency: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if escalation to human support is recommended"""
        try:
            escalation_reasons = []
            escalation_score = 0
            
            # Check sentiment-based escalation
            if sentiment.get("score", 0) < -0.6:
                escalation_reasons.append("Negative sentiment detected")
                escalation_score += 2
            
            if sentiment.get("intensity") == "high" and sentiment.get("label") == "negative":
                escalation_reasons.append("High intensity negative emotion")
                escalation_score += 2
            
            # Check urgency-based escalation
            if urgency.get("level") == "critical":
                escalation_reasons.append("Critical urgency level")
                escalation_score += 3
            elif urgency.get("level") == "high":
                escalation_reasons.append("High urgency level")
                escalation_score += 1
            
            # Check issue complexity
            if issues.get("total_issues", 0) > 2:
                escalation_reasons.append("Multiple complex issues detected")
                escalation_score += 1
            
            # Check frustration level
            if issues.get("frustration_level", 0) >= 2:
                escalation_reasons.append("High customer frustration")
                escalation_score += 2
            
            # Check for specific escalation keywords
            text_lower = message.content.lower()
            escalation_keywords = [
                "speak to manager", "supervisor", "human", "real person",
                "escalate", "transfer", "someone else", "not helpful"
            ]
            
            if any(keyword in text_lower for keyword in escalation_keywords):
                escalation_reasons.append("Direct request for human support")
                escalation_score += 3
            
            # Determine recommendation
            recommended = escalation_score >= 3
            priority = "immediate" if escalation_score >= 5 else "high" if escalation_score >= 3 else "normal"
            
            return {
                "recommended": recommended,
                "priority": priority,
                "score": escalation_score,
                "reasons": escalation_reasons,
                "confidence": min(0.9, escalation_score * 0.2)
            }
            
        except Exception as e:
            logger.error(f"Escalation check failed: {e}")
            return {
                "recommended": False,
                "priority": "normal",
                "score": 0,
                "reasons": [],
                "error": str(e)
            }
    
    async def _analyze_conversation_flow(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze conversation flow and progression"""
        try:
            if not messages:
                return {"status": "no_messages"}
            
            # Reverse to get chronological order
            messages = list(reversed(messages))
            
            user_messages = [msg for msg in messages if msg.sender_type == 'user']
            bot_messages = [msg for msg in messages if msg.sender_type == 'bot']
            
            # Analyze message progression
            message_lengths = [len(msg.content.split()) for msg in user_messages]
            avg_message_length = sum(message_lengths) / len(message_lengths) if message_lengths else 0
            
            # Check for repetition (user asking same thing multiple times)
            repetition_detected = False
            if len(user_messages) > 1:
                recent_messages = [msg.content.lower() for msg in user_messages[-3:]]
                for i, msg in enumerate(recent_messages[:-1]):
                    for j, other_msg in enumerate(recent_messages[i+1:]):
                        if self._similarity_score(msg, other_msg) > 0.7:
                            repetition_detected = True
                            break
            
            # Check conversation progression
            engagement_pattern = self._analyze_engagement_pattern(user_messages)
            
            return {
                "total_exchanges": len(messages),
                "user_messages": len(user_messages),
                "bot_messages": len(bot_messages),
                "avg_user_message_length": round(avg_message_length, 1),
                "repetition_detected": repetition_detected,
                "engagement_pattern": engagement_pattern,
                "conversation_stage": self._determine_conversation_stage(messages)
            }
            
        except Exception as e:
            logger.error(f"Conversation flow analysis failed: {e}")
            return {"error": str(e)}
    
    def _similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _analyze_engagement_pattern(self, user_messages: List[Message]) -> str:
        """Analyze user engagement pattern"""
        if len(user_messages) < 2:
            return "insufficient_data"
        
        message_lengths = [len(msg.content.split()) for msg in user_messages]
        
        # Check if messages are getting longer (more engaged) or shorter (less engaged)
        if len(message_lengths) >= 3:
            recent_avg = sum(message_lengths[-2:]) / 2
            earlier_avg = sum(message_lengths[:-2]) / len(message_lengths[:-2])
            
            if recent_avg > earlier_avg * 1.2:
                return "increasing_engagement"
            elif recent_avg < earlier_avg * 0.8:
                return "decreasing_engagement"
        
        return "stable_engagement"
    
    def _determine_conversation_stage(self, messages: List[Message]) -> str:
        """Determine what stage of conversation this is"""
        if len(messages) <= 2:
            return "opening"
        elif len(messages) <= 6:
            return "exploration"
        elif len(messages) <= 12:
            return "resolution_attempt"
        else:
            return "extended_support"
    
    async def _detect_conversation_issues(self, messages: List[Message]) -> Dict[str, Any]:
        """Detect issues at conversation level"""
        try:
            # Check for bot confusion indicators
            bot_confusion_phrases = [
                "I don't understand", "I'm not sure", "Could you clarify",
                "I don't have information", "I can't help with", "I'm not able to"
            ]
            
            bot_messages = [msg for msg in messages if msg.sender_type == 'bot']
            confusion_count = 0
            
            for bot_msg in bot_messages:
                if any(phrase.lower() in bot_msg.content.lower() for phrase in bot_confusion_phrases):
                    confusion_count += 1
            
            # Check for user repetition
            user_messages = [msg for msg in messages if msg.sender_type == 'user']
            repetition_count = 0
            
            for i, msg in enumerate(user_messages[:-1]):
                next_msg = user_messages[i + 1]
                if self._similarity_score(msg.content.lower(), next_msg.content.lower()) > 0.6:
                    repetition_count += 1
            
            return {
                "bot_confusion_detected": confusion_count > 0,
                "bot_confusion_count": confusion_count,
                "user_repetition_detected": repetition_count > 0,
                "user_repetition_count": repetition_count,
                "conversation_stuck": confusion_count > 1 or repetition_count > 1,
                "needs_intervention": confusion_count > 2 or repetition_count > 2
            }
            
        except Exception as e:
            logger.error(f"Conversation issue detection failed: {e}")
            return {"error": str(e)}
    
    async def _check_conversation_escalation(self, messages: List[Message], flow: Dict[str, Any]) -> Dict[str, Any]:
        """Check for conversation-level escalation triggers"""
        try:
            escalation_factors = []
            escalation_score = 0
            
            # Check conversation length
            if len(messages) > 15:
                escalation_factors.append("Extended conversation (15+ messages)")
                escalation_score += 1
            
            # Check if conversation is stuck
            if flow.get("conversation_stuck", False):
                escalation_factors.append("Conversation appears stuck")
                escalation_score += 2
            
            # Check engagement pattern
            if flow.get("engagement_pattern") == "decreasing_engagement":
                escalation_factors.append("User engagement decreasing")
                escalation_score += 1
            
            # Check repetition
            if flow.get("repetition_detected", False):
                escalation_factors.append("User repeating questions")
                escalation_score += 1
            
            return {
                "recommended": escalation_score >= 2,
                "score": escalation_score,
                "factors": escalation_factors,
                "priority": "high" if escalation_score >= 3 else "medium" if escalation_score >= 2 else "low"
            }
            
        except Exception as e:
            logger.error(f"Conversation escalation check failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_sentiment_trend(self, messages: List[Message]) -> Dict[str, Any]:
        """Analyze sentiment trend over recent messages"""
        try:
            user_messages = [msg for msg in messages if msg.sender_type == 'user']
            
            if len(user_messages) < 2:
                return {"trend": "insufficient_data"}
            
            # Analyze sentiment for each message
            sentiments = []
            for msg in user_messages:
                sentiment = await self._quick_sentiment_analysis(msg.content)
                sentiments.append(sentiment.get("score", 0))
            
            # Calculate trend
            if len(sentiments) >= 3:
                recent_sentiment = sum(sentiments[-2:]) / 2
                earlier_sentiment = sum(sentiments[:-2]) / len(sentiments[:-2])
                
                trend_direction = "improving" if recent_sentiment > earlier_sentiment + 0.2 else \
                                "declining" if recent_sentiment < earlier_sentiment - 0.2 else \
                                "stable"
            else:
                trend_direction = "stable"
            
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            return {
                "trend": trend_direction,
                "average_sentiment": round(avg_sentiment, 2),
                "current_sentiment": round(sentiments[-1], 2) if sentiments else 0,
                "sentiment_scores": [round(s, 2) for s in sentiments],
                "message_count": len(sentiments)
            }
            
        except Exception as e:
            logger.error(f"Sentiment trend analysis failed: {e}")
            return {"error": str(e)}
    
    async def _assess_customer_satisfaction(self, messages: List[Message], sentiment_trend: Dict[str, Any]) -> Dict[str, Any]:
        """Assess customer satisfaction indicators"""
        try:
            # Get user messages
            user_messages = [msg for msg in messages if msg.sender_type == 'user']
            
            satisfaction_indicators = {
                "positive": 0,
                "negative": 0,
                "neutral": 0
            }
            
            # Check for explicit satisfaction indicators
            for msg in user_messages:
                content_lower = msg.content.lower()
                
                if any(phrase in content_lower for phrase in [
                    "thank", "thanks", "helpful", "great", "perfect", "solved"
                ]):
                    satisfaction_indicators["positive"] += 1
                elif any(phrase in content_lower for phrase in [
                    "frustrated", "unhelpful", "not working", "terrible", "awful"
                ]):
                    satisfaction_indicators["negative"] += 1
                else:
                    satisfaction_indicators["neutral"] += 1
            
            # Calculate satisfaction score
            total_messages = sum(satisfaction_indicators.values())
            if total_messages > 0:
                satisfaction_score = (
                    (satisfaction_indicators["positive"] * 1.0) + 
                    (satisfaction_indicators["neutral"] * 0.5) + 
                    (satisfaction_indicators["negative"] * 0.0)
                ) / total_messages
            else:
                satisfaction_score = 0.5
            
            # Combine with sentiment trend
            avg_sentiment = sentiment_trend.get("average_sentiment", 0)
            combined_score = (satisfaction_score + (avg_sentiment + 1) / 2) / 2
            
            # Determine satisfaction level
            if combined_score > 0.7:
                satisfaction_level = "high"
            elif combined_score > 0.4:
                satisfaction_level = "medium"
            else:
                satisfaction_level = "low"
            
            return {
                "level": satisfaction_level,
                "score": round(combined_score, 2),
                "indicators": satisfaction_indicators,
                "sentiment_factor": round(avg_sentiment, 2),
                "trend": sentiment_trend.get("trend", "unknown")
            }
            
        except Exception as e:
            logger.error(f"Customer satisfaction assessment failed: {e}")
            return {"error": str(e)}
    
    def _generate_realtime_alerts(
        self, 
        flow: Dict[str, Any], 
        issues: Dict[str, Any], 
        escalation: Dict[str, Any], 
        sentiment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate real-time alerts for monitoring dashboard"""
        alerts = []
        
        # High priority alerts
        if escalation.get("recommended") and escalation.get("priority") == "high":
            alerts.append({
                "level": "critical",
                "type": "escalation_needed",
                "message": "Conversation requires immediate escalation",
                "factors": escalation.get("factors", [])
            })
        
        if sentiment.get("trend") == "declining" and sentiment.get("average_sentiment", 0) < -0.4:
            alerts.append({
                "level": "warning",
                "type": "sentiment_decline",
                "message": "Customer sentiment declining",
                "current_sentiment": sentiment.get("current_sentiment", 0)
            })
        
        if issues.get("conversation_stuck"):
            alerts.append({
                "level": "warning",
                "type": "conversation_stuck",
                "message": "Conversation appears stuck - intervention may be needed",
                "confusion_count": issues.get("bot_confusion_count", 0),
                "repetition_count": issues.get("user_repetition_count", 0)
            })
        
        if flow.get("total_exchanges", 0) > 15:
            alerts.append({
                "level": "info",
                "type": "extended_conversation",
                "message": "Extended conversation - monitor for resolution",
                "exchange_count": flow.get("total_exchanges", 0)
            })
        
        return alerts


# Global service instance
realtime_analysis_service = RealtimeAnalysisService()