"""
Google LangExtract integration for conversation analysis
Provides structured insights from unstructured chat conversations
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class LangExtractService:
    """Service for analyzing conversations using Google LangExtract"""
    
    def __init__(self):
        # For now, we'll simulate LangExtract functionality
        # In production, this would connect to Google LangExtract API
        self.api_key = getattr(settings, 'LANGEXTRACT_API_KEY', None)
    
    def analyze_conversation(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a conversation for insights, sentiment, and intelligence
        
        Args:
            messages: List of message objects with 'role', 'content', 'timestamp'
            
        Returns:
            Structured analysis with sentiment, satisfaction, issues, etc.
        """
        try:
            # Simulate LangExtract analysis
            # In production, this would call Google LangExtract API
            
            conversation_text = self._prepare_conversation_text(messages)
            analysis = self._simulate_langextract_analysis(conversation_text, messages)
            
            return analysis
            
        except Exception as e:
            logger.error(f"LangExtract analysis failed: {e}")
            return self._get_fallback_analysis()
    
    def _prepare_conversation_text(self, messages: List[Dict[str, Any]]) -> str:
        """Prepare conversation text for analysis"""
        conversation_lines = []
        
        for msg in messages:
            role = "Customer" if msg.get('role') == 'user' else "Assistant"
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            conversation_lines.append(f"[{timestamp}] {role}: {content}")
        
        return "\\n".join(conversation_lines)
    
    def _simulate_langextract_analysis(self, conversation_text: str, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate Google LangExtract analysis"""
        
        # Count user vs assistant messages
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
        
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
            "conversation_metrics": {
                "total_messages": len(messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "conversation_length": len(conversation_text.split()),
                "avg_message_length": sum(len(msg.get('content', '').split()) for msg in messages) / max(len(messages), 1)
            },
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
            "key_insights": ["Analysis service unavailable"],
            "analysis_timestamp": datetime.now().isoformat(),
            "analysis_version": "fallback_v1.0"
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