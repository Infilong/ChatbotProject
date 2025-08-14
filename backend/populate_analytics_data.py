"""
Script to populate analytics data by analyzing existing conversations
This runs synchronously to avoid async context issues
"""

import os
import sys
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from chat.models import Conversation, Message


def analyze_conversation_sync(conversation):
    """Synchronous fallback analysis for a conversation"""
    print(f"Analyzing: {conversation.title}")
    
    try:
        # Get conversation messages
        messages = list(conversation.messages.all().order_by('timestamp'))
        if not messages:
            print(f"  No messages found")
            return None
        
        # Format conversation text
        conversation_text = ""
        for msg in messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            sender = "Customer" if msg.sender_type == 'user' else "Bot"
            content = msg.content.strip()
            conversation_text += f"[{timestamp}] {sender}: {content}\n"
        
        # Basic sentiment analysis
        text_lower = conversation_text.lower()
        positive_words = ['good', 'great', 'excellent', 'helpful', 'thank', 'perfect', 'solved', 'wonderful', 'happy', 'satisfied']
        negative_words = ['bad', 'terrible', 'frustrated', 'angry', 'problem', 'issue', 'broken', 'not working', 'hate', 'disappointed']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            overall_sentiment = "positive"
            satisfaction_score = 8.0
        elif negative_count > positive_count:
            overall_sentiment = "negative"
            satisfaction_score = 4.0
        else:
            overall_sentiment = "neutral"
            satisfaction_score = 6.0
        
        # Issue detection
        issue_keywords = {
            "technical": ["error", "bug", "not working", "broken", "api", "integration", "oauth"],
            "billing": ["payment", "charge", "invoice", "billing", "refund", "money", "cost"],
            "support": ["help", "support", "question", "how", "password", "reset", "account"]
        }
        
        detected_categories = []
        for category, keywords in issue_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_categories.append(category)
        
        # Urgency detection
        urgency_keywords = ["urgent", "immediately", "asap", "critical", "emergency", "frustrated", "third time", "again"]
        urgency_indicators = [phrase for phrase in urgency_keywords if phrase in text_lower]
        has_high_urgency = len(urgency_indicators) > 0
        
        # Conversation type detection
        if "billing" in detected_categories or "charge" in text_lower or "refund" in text_lower:
            conversation_type = "billing_issue"
        elif "technical" in detected_categories or "api" in text_lower or "integration" in text_lower:
            conversation_type = "technical_support"
        elif "password" in text_lower or "reset" in text_lower or "account" in text_lower:
            conversation_type = "account_support"
        else:
            conversation_type = "general_inquiry"
        
        # Resolution status
        resolution_indicators = ["thank", "solved", "perfect", "worked", "resolved", "fixed"]
        escalation_indicators = ["escalat", "manager", "supervisor", "human", "agent"]
        
        if any(indicator in text_lower for indicator in resolution_indicators):
            resolution_status = "resolved"
        elif any(indicator in text_lower for indicator in escalation_indicators):
            resolution_status = "escalated"
        else:
            resolution_status = "ongoing"
        
        # Count messages
        user_messages = sum(1 for msg in messages if msg.sender_type == 'user')
        bot_messages = sum(1 for msg in messages if msg.sender_type == 'bot')
        
        # Build comprehensive analysis
        analysis_result = {
            "conversation_patterns": {
                "conversation_flow": {
                    "conversation_type": conversation_type,
                    "user_journey_stage": "support",
                    "conversation_quality": satisfaction_score,
                    "resolution_status": resolution_status
                },
                "user_behavior_patterns": {
                    "communication_style": "frustrated" if has_high_urgency else "neutral",
                    "technical_expertise": "intermediate",
                    "patience_level": "low" if has_high_urgency else "medium",
                    "engagement_level": "highly_engaged" if user_messages > 3 else "moderately_engaged"
                },
                "bot_performance": {
                    "response_relevance": 8.0 if resolution_status == "resolved" else 6.0,
                    "response_helpfulness": 8.0 if resolution_status == "resolved" else 6.0,
                    "knowledge_gaps": [],
                    "improvement_opportunities": ["Better urgency detection"] if has_high_urgency else []
                },
                "fallback_analysis": True,
                "message_counts": {
                    "user_messages": user_messages,
                    "bot_messages": bot_messages,
                    "total_messages": len(messages)
                }
            },
            "customer_insights": {
                "sentiment_analysis": {
                    "overall_sentiment": overall_sentiment,
                    "satisfaction_score": satisfaction_score,
                    "emotional_indicators": urgency_indicators,
                    "sentiment_progression": []
                },
                "issue_extraction": {
                    "primary_issues": [],
                    "issue_categories": detected_categories,
                    "pain_points": urgency_indicators
                },
                "urgency_assessment": {
                    "urgency_level": "high" if has_high_urgency else "medium",
                    "importance_level": "high" if "billing" in detected_categories else "medium",
                    "urgency_indicators": urgency_indicators,
                    "escalation_recommended": has_high_urgency,
                    "escalation_reason": "High urgency indicators detected" if has_high_urgency else ""
                },
                "business_intelligence": {
                    "customer_segment": "individual",
                    "use_case_category": conversation_type,
                    "feature_requests": [],
                    "competitive_mentions": [],
                    "churn_risk_indicators": urgency_indicators if has_high_urgency else [],
                    "upsell_opportunities": []
                },
                "fallback_analysis": True
            },
            "unknown_patterns": {
                "unknown_issues": {
                    "unresolved_queries": [] if resolution_status == "resolved" else ["Incomplete resolution"],
                    "knowledge_gaps": [],
                    "new_use_cases": [],
                    "terminology_issues": []
                },
                "learning_opportunities": {
                    "training_data_suggestions": [],
                    "prompt_improvements": ["Better urgency response"] if has_high_urgency else [],
                    "new_intents": [],
                    "integration_needs": []
                },
                "bot_confusion_detected": False,
                "requires_review": has_high_urgency,
                "fallback_analysis": True
            },
            "analysis_timestamp": timezone.now().isoformat(),
            "conversation_id": str(conversation.uuid),
            "metadata": {
                "automatic_analysis": False,
                "manual_analysis": True,
                "forced_analysis": True,
                "analysis_triggered_at": timezone.now().isoformat(),
                "analysis_method": "synchronous_fallback"
            }
        }
        
        print(f"  Sentiment: {overall_sentiment}, Score: {satisfaction_score}")
        print(f"  Type: {conversation_type}, Status: {resolution_status}")
        print(f"  Categories: {detected_categories}")
        print(f"  Urgency: {'High' if has_high_urgency else 'Medium'}")
        
        return analysis_result
        
    except Exception as e:
        print(f"  Error analyzing conversation: {e}")
        return None


def populate_analytics():
    """Populate analytics data for all unanalyzed conversations"""
    print("=== Populating Analytics Data ===")
    
    # Get unanalyzed conversations
    unanalyzed_conversations = Conversation.objects.filter(langextract_analysis__exact={})
    total_count = unanalyzed_conversations.count()
    
    print(f"Found {total_count} unanalyzed conversations")
    
    if total_count == 0:
        print("No conversations need analysis!")
        return
    
    analyzed_count = 0
    error_count = 0
    
    for conversation in unanalyzed_conversations:
        try:
            analysis_result = analyze_conversation_sync(conversation)
            
            if analysis_result:
                # Save analysis to database
                conversation.langextract_analysis = analysis_result
                conversation.save(update_fields=['langextract_analysis'])
                analyzed_count += 1
                print(f"  [+] Saved analysis")
            else:
                error_count += 1
                print(f"  [-] Analysis failed")
                
        except Exception as e:
            error_count += 1
            print(f"  [-] Error: {e}")
    
    print(f"\n=== Results ===")
    print(f"Total conversations: {total_count}")
    print(f"Successfully analyzed: {analyzed_count}")
    print(f"Errors: {error_count}")
    
    # Show final statistics
    total_conversations = Conversation.objects.count()
    analyzed_conversations = Conversation.objects.exclude(langextract_analysis__exact={}).count()
    coverage = (analyzed_conversations / total_conversations * 100) if total_conversations > 0 else 0
    
    print(f"\n=== Database Summary ===")
    print(f"Total conversations: {total_conversations}")
    print(f"Analyzed conversations: {analyzed_conversations}")
    print(f"Analysis coverage: {coverage:.1f}%")
    
    print(f"\n[+] Analytics data populated! Check the Django admin at:")
    print(f"  http://localhost:8000/admin/analytics/analyticssummary/")


if __name__ == '__main__':
    populate_analytics()