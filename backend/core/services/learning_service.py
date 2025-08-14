"""
Learning and Improvement Service
Implements conversation pattern learning, user feedback collection, and continuous improvement
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from chat.models import Conversation, Message, ConversationInsight, LearningPattern, UnknownIssue
from .langextract_service import langextract_service

logger = logging.getLogger(__name__)


class ConversationLearningService:
    """Service for learning from conversations and improving the system"""
    
    def __init__(self):
        self.langextract_service = langextract_service
    
    async def process_conversation_completion(self, conversation: Conversation) -> Dict[str, Any]:
        """
        Process a completed conversation for learning and insights
        
        Args:
            conversation: Completed conversation to analyze
            
        Returns:
            Dict containing processing results
        """
        try:
            logger.info(f"Processing conversation {conversation.uuid} for learning")
            
            # Run comprehensive LangExtract analysis
            analysis_result = await self.langextract_service.analyze_full_conversation(conversation)
            
            # Extract and store structured insights
            await self._extract_and_store_insights(conversation, analysis_result)
            
            # Identify learning patterns
            await self._identify_learning_patterns(conversation, analysis_result)
            
            # Detect unknown issues
            await self._detect_unknown_issues(conversation, analysis_result)
            
            # Process user feedback if available
            await self._process_user_feedback(conversation)
            
            # Update conversation satisfaction score
            await self._update_conversation_satisfaction(conversation)
            
            logger.info(f"Successfully processed conversation {conversation.uuid} for learning")
            
            return {
                "status": "success",
                "conversation_id": str(conversation.uuid),
                "insights_extracted": True,
                "patterns_identified": True,
                "unknown_issues_detected": True
            }
            
        except Exception as e:
            logger.error(f"Failed to process conversation {conversation.uuid} for learning: {e}")
            return {
                "status": "error",
                "conversation_id": str(conversation.uuid),
                "error": str(e)
            }
    
    async def _extract_and_store_insights(self, conversation: Conversation, analysis_result: Dict[str, Any]):
        """Extract insights from LangExtract analysis and store in ConversationInsight model"""
        try:
            insights_data = analysis_result.get('customer_insights', {})
            patterns_data = analysis_result.get('conversation_patterns', {})
            
            # Extract sentiment analysis
            sentiment_analysis = insights_data.get('sentiment_analysis', {})
            overall_sentiment = sentiment_analysis.get('overall_sentiment', 'neutral')
            satisfaction_score = sentiment_analysis.get('satisfaction_score')
            emotional_indicators = sentiment_analysis.get('emotional_indicators', [])
            
            # Extract issue analysis
            issue_extraction = insights_data.get('issue_extraction', {})
            primary_issues = issue_extraction.get('primary_issues', [])
            issue_categories = issue_extraction.get('issue_categories', [])
            pain_points = issue_extraction.get('pain_points', [])
            
            # Extract urgency assessment
            urgency_assessment = insights_data.get('urgency_assessment', {})
            urgency_level = urgency_assessment.get('urgency_level', 'low')
            importance_level = urgency_assessment.get('importance_level', 'low')
            escalation_recommended = urgency_assessment.get('escalation_recommended', False)
            escalation_reason = urgency_assessment.get('escalation_reason', '')
            
            # Extract business intelligence
            business_intelligence = insights_data.get('business_intelligence', {})
            customer_segment = business_intelligence.get('customer_segment', '')
            feature_requests = business_intelligence.get('feature_requests', [])
            churn_risk_indicators = business_intelligence.get('churn_risk_indicators', [])
            upsell_opportunities = business_intelligence.get('upsell_opportunities', [])
            
            # Extract conversation flow data
            conversation_flow = patterns_data.get('conversation_flow', {})
            resolution_status = conversation_flow.get('resolution_status', 'unresolved')
            conversation_quality = conversation_flow.get('conversation_quality')
            
            # Create or update ConversationInsight
            insight, created = await ConversationInsight.objects.aupdate_or_create(
                conversation=conversation,
                defaults={
                    'overall_sentiment': overall_sentiment,
                    'satisfaction_score': satisfaction_score,
                    'emotional_indicators': emotional_indicators,
                    'primary_issues': primary_issues,
                    'issue_categories': issue_categories,
                    'pain_points': pain_points,
                    'urgency_level': urgency_level,
                    'importance_level': importance_level,
                    'escalation_recommended': escalation_recommended,
                    'escalation_reason': escalation_reason,
                    'resolution_status': resolution_status,
                    'conversation_quality': conversation_quality,
                    'customer_segment': customer_segment,
                    'feature_requests': feature_requests,
                    'churn_risk_indicators': churn_risk_indicators,
                    'upsell_opportunities': upsell_opportunities,
                    'raw_langextract_data': analysis_result,
                    'analysis_version': '1.0'
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} ConversationInsight for conversation {conversation.uuid}")
            
        except Exception as e:
            logger.error(f"Failed to extract and store insights for conversation {conversation.uuid}: {e}")
    
    async def _identify_learning_patterns(self, conversation: Conversation, analysis_result: Dict[str, Any]):
        """Identify and store learning patterns from conversation analysis"""
        try:
            patterns_data = analysis_result.get('conversation_patterns', {})
            unknown_data = analysis_result.get('unknown_patterns', {})
            
            # Pattern 1: Bot Performance Issues
            bot_performance = patterns_data.get('bot_performance', {})
            if bot_performance:
                response_relevance = bot_performance.get('response_relevance', 10)
                response_helpfulness = bot_performance.get('response_helpfulness', 10)
                knowledge_gaps = bot_performance.get('knowledge_gaps', [])
                improvement_opportunities = bot_performance.get('improvement_opportunities', [])
                
                # If bot performance is poor, create a learning pattern
                if response_relevance < 7 or response_helpfulness < 7 or knowledge_gaps:
                    await self._create_or_update_pattern(
                        pattern_type='performance_issue',
                        title=f"Bot Performance Issue in {conversation.get_title()[:50]}",
                        description=f"Bot showed poor performance: relevance={response_relevance}/10, helpfulness={response_helpfulness}/10",
                        pattern_data={
                            'response_relevance': response_relevance,
                            'response_helpfulness': response_helpfulness,
                            'knowledge_gaps': knowledge_gaps,
                            'improvement_opportunities': improvement_opportunities
                        },
                        conversation=conversation,
                        priority='high' if response_relevance < 5 or response_helpfulness < 5 else 'medium'
                    )
            
            # Pattern 2: User Behavior Patterns
            user_behavior = patterns_data.get('user_behavior_patterns', {})
            if user_behavior:
                communication_style = user_behavior.get('communication_style')
                patience_level = user_behavior.get('patience_level')
                engagement_level = user_behavior.get('engagement_level')
                
                # Track patterns of frustrated or disengaged users
                if patience_level in ['low', 'impatient'] or engagement_level == 'disengaged':
                    await self._create_or_update_pattern(
                        pattern_type='user_behavior',
                        title=f"User Frustration Pattern: {communication_style or 'Unknown'} Style",
                        description=f"User showed {patience_level} patience and {engagement_level} engagement",
                        pattern_data=user_behavior,
                        conversation=conversation,
                        priority='high' if patience_level == 'impatient' else 'medium'
                    )
            
            # Pattern 3: Escalation Triggers
            insights_data = analysis_result.get('customer_insights', {})
            urgency_assessment = insights_data.get('urgency_assessment', {})
            if urgency_assessment.get('escalation_recommended'):
                escalation_reason = urgency_assessment.get('escalation_reason', '')
                await self._create_or_update_pattern(
                    pattern_type='escalation_trigger',
                    title=f"Escalation Trigger: {escalation_reason[:50]}",
                    description=escalation_reason,
                    pattern_data=urgency_assessment,
                    conversation=conversation,
                    priority='critical'
                )
            
            # Pattern 4: Knowledge Gaps
            unknown_issues = unknown_data.get('unknown_issues', {})
            knowledge_gaps = unknown_issues.get('knowledge_gaps', [])
            for gap in knowledge_gaps:
                if isinstance(gap, dict):
                    await self._create_or_update_pattern(
                        pattern_type='knowledge_gap',
                        title=f"Knowledge Gap: {gap.get('topic', 'Unknown Topic')}",
                        description=gap.get('gap_description', ''),
                        pattern_data=gap,
                        conversation=conversation,
                        priority='high'
                    )
            
            logger.info(f"Identified learning patterns for conversation {conversation.uuid}")
            
        except Exception as e:
            logger.error(f"Failed to identify learning patterns for conversation {conversation.uuid}: {e}")
    
    async def _detect_unknown_issues(self, conversation: Conversation, analysis_result: Dict[str, Any]):
        """Detect and store unknown issues that the bot couldn't handle"""
        try:
            unknown_data = analysis_result.get('unknown_patterns', {})
            
            if not unknown_data.get('requires_review', False):
                return
            
            unknown_issues = unknown_data.get('unknown_issues', {})
            unresolved_queries = unknown_issues.get('unresolved_queries', [])
            
            # Get bot messages to understand what the bot said
            bot_messages = await conversation.messages.filter(sender_type='bot').aall()
            user_messages = await conversation.messages.filter(sender_type='user').aall()
            
            # Process each unresolved query
            for i, query in enumerate(unresolved_queries):
                if not query:
                    continue
                
                # Find corresponding user and bot messages
                user_msg = None
                bot_msg = None
                
                if i < len(user_messages):
                    user_msg = user_messages[i]
                if i < len(bot_messages):
                    bot_msg = bot_messages[i]
                
                # Determine issue category
                category = self._categorize_unknown_issue(query, unknown_data)
                
                # Create UnknownIssue record
                unknown_issue = await UnknownIssue.objects.acreate(
                    conversation=conversation,
                    category=category,
                    user_query=user_msg.content if user_msg else query,
                    bot_response=bot_msg.content if bot_msg else "No response available",
                    issue_description=f"Bot was unable to properly address this query: {query}",
                    context_data={
                        'langextract_analysis': unknown_data,
                        'conversation_title': conversation.get_title(),
                        'message_index': i
                    },
                    suggested_improvements=unknown_data.get('learning_opportunities', {}).get('training_data_suggestions', [])
                )
                
                # Calculate priority score
                unknown_issue.calculate_priority_score()
                await unknown_issue.asave(update_fields=['priority_score'])
                
                logger.info(f"Created UnknownIssue {unknown_issue.uuid} for conversation {conversation.uuid}")
            
        except Exception as e:
            logger.error(f"Failed to detect unknown issues for conversation {conversation.uuid}: {e}")
    
    def _categorize_unknown_issue(self, query: str, unknown_data: Dict[str, Any]) -> str:
        """Categorize an unknown issue based on content and analysis"""
        query_lower = query.lower()
        
        # Check for technical terms
        if any(term in query_lower for term in ['api', 'integration', 'technical', 'code', 'error']):
            return 'technical_limitation'
        
        # Check for new features or use cases
        if any(term in query_lower for term in ['new', 'feature', 'can you', 'do you support']):
            return 'new_use_case'
        
        # Check for complex queries
        if len(query.split()) > 15 or '?' in query and query.count('?') > 1:
            return 'complex_query'
        
        # Check for unclear intent
        if any(term in query_lower for term in ['unclear', 'confusing', 'what do you mean']):
            return 'unclear_intent'
        
        # Check learning opportunities for integration needs
        learning_opportunities = unknown_data.get('learning_opportunities', {})
        if learning_opportunities.get('integration_needs'):
            return 'integration_need'
        
        # Default to knowledge gap
        return 'knowledge_gap'
    
    async def _create_or_update_pattern(
        self, 
        pattern_type: str, 
        title: str, 
        description: str, 
        pattern_data: Dict[str, Any], 
        conversation: Conversation,
        priority: str = 'medium'
    ):
        """Create or update a learning pattern"""
        try:
            # Check if similar pattern already exists
            existing_pattern = await LearningPattern.objects.filter(
                pattern_type=pattern_type,
                title__icontains=title[:30]  # Match first 30 chars of title
            ).afirst()
            
            if existing_pattern:
                # Update existing pattern
                existing_pattern.increment_frequency(conversation)
                existing_pattern.pattern_data.update(pattern_data)
                if existing_pattern.priority_level != 'critical' and priority == 'critical':
                    existing_pattern.priority_level = priority
                await existing_pattern.asave(update_fields=['pattern_data', 'priority_level'])
                logger.info(f"Updated existing learning pattern {existing_pattern.uuid}")
            else:
                # Create new pattern
                new_pattern = await LearningPattern.objects.acreate(
                    pattern_type=pattern_type,
                    title=title,
                    description=description,
                    pattern_data=pattern_data,
                    priority_level=priority,
                    confidence_score=0.8  # Default confidence
                )
                await new_pattern.source_conversations.aadd(conversation)
                logger.info(f"Created new learning pattern {new_pattern.uuid}")
                
        except Exception as e:
            logger.error(f"Failed to create/update learning pattern: {e}")
    
    async def _process_user_feedback(self, conversation: Conversation):
        """Process user feedback from messages in the conversation"""
        try:
            # Get messages with feedback
            feedback_messages = await conversation.messages.filter(
                feedback__isnull=False
            ).aall()
            
            positive_feedback = 0
            negative_feedback = 0
            
            for message in feedback_messages:
                if message.feedback == 'positive':
                    positive_feedback += 1
                elif message.feedback == 'negative':
                    negative_feedback += 1
            
            if positive_feedback > 0 or negative_feedback > 0:
                # Update conversation satisfaction based on feedback
                total_feedback = positive_feedback + negative_feedback
                satisfaction_ratio = positive_feedback / total_feedback if total_feedback > 0 else 0.5
                
                # Convert to 1-10 scale
                feedback_satisfaction = 1 + (satisfaction_ratio * 9)
                
                # Update conversation's satisfaction score
                conversation.satisfaction_score = feedback_satisfaction
                await conversation.asave(update_fields=['satisfaction_score'])
                
                # If there's negative feedback, create a learning pattern
                if negative_feedback > 0:
                    await self._create_or_update_pattern(
                        pattern_type='user_behavior',
                        title=f"Negative Feedback Pattern",
                        description=f"User provided negative feedback ({negative_feedback} negative, {positive_feedback} positive)",
                        pattern_data={
                            'positive_feedback': positive_feedback,
                            'negative_feedback': negative_feedback,
                            'satisfaction_score': feedback_satisfaction
                        },
                        conversation=conversation,
                        priority='high' if negative_feedback > positive_feedback else 'medium'
                    )
                
                logger.info(f"Processed user feedback for conversation {conversation.uuid}: {positive_feedback} positive, {negative_feedback} negative")
                
        except Exception as e:
            logger.error(f"Failed to process user feedback for conversation {conversation.uuid}: {e}")
    
    async def _update_conversation_satisfaction(self, conversation: Conversation):
        """Update conversation satisfaction score based on analysis and feedback"""
        try:
            # Get existing insight
            insight = await conversation.insight if hasattr(conversation, 'insight') else None
            
            if insight:
                # Use LangExtract satisfaction score if available
                langextract_satisfaction = insight.satisfaction_score
                
                # Use feedback-based satisfaction if available
                feedback_satisfaction = conversation.satisfaction_score
                
                # Combine scores with preference for feedback
                if feedback_satisfaction and langextract_satisfaction:
                    # Weight feedback more heavily (70% feedback, 30% analysis)
                    final_satisfaction = (feedback_satisfaction * 0.7) + (langextract_satisfaction * 0.3)
                elif feedback_satisfaction:
                    final_satisfaction = feedback_satisfaction
                elif langextract_satisfaction:
                    final_satisfaction = langextract_satisfaction
                else:
                    final_satisfaction = 5.0  # Neutral default
                
                # Update conversation
                conversation.satisfaction_score = final_satisfaction
                await conversation.asave(update_fields=['satisfaction_score'])
                
                logger.info(f"Updated satisfaction score for conversation {conversation.uuid}: {final_satisfaction}")
                
        except Exception as e:
            logger.error(f"Failed to update satisfaction score for conversation {conversation.uuid}: {e}")
    
    async def get_learning_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get learning insights and recommendations for system improvement"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get top learning patterns
            top_patterns = await LearningPattern.objects.filter(
                last_observed__gte=cutoff_date
            ).order_by('-frequency_count', '-priority_level')[:10].aall()
            
            # Get critical unknown issues
            critical_issues = await UnknownIssue.objects.filter(
                identified_at__gte=cutoff_date,
                resolution_status='pending'
            ).order_by('-priority_score')[:5].aall()
            
            # Get sentiment trends
            insights = await ConversationInsight.objects.filter(
                analyzed_at__gte=cutoff_date
            ).aall()
            
            sentiment_distribution = {}
            satisfaction_scores = []
            escalation_count = 0
            
            for insight in insights:
                # Count sentiments
                sentiment = insight.overall_sentiment or 'neutral'
                sentiment_distribution[sentiment] = sentiment_distribution.get(sentiment, 0) + 1
                
                # Collect satisfaction scores
                if insight.satisfaction_score:
                    satisfaction_scores.append(insight.satisfaction_score)
                
                # Count escalations
                if insight.escalation_recommended:
                    escalation_count += 1
            
            # Calculate average satisfaction
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
            
            return {
                "time_period_days": days,
                "top_learning_patterns": [
                    {
                        "type": pattern.pattern_type,
                        "title": pattern.title,
                        "frequency": pattern.frequency_count,
                        "priority": pattern.priority_level,
                        "status": pattern.status
                    }
                    for pattern in top_patterns
                ],
                "critical_unknown_issues": [
                    {
                        "category": issue.category,
                        "description": issue.issue_description[:100],
                        "priority_score": issue.priority_score,
                        "frequency": issue.frequency_count
                    }
                    for issue in critical_issues
                ],
                "sentiment_trends": {
                    "distribution": sentiment_distribution,
                    "average_satisfaction": round(avg_satisfaction, 2),
                    "total_conversations": len(insights),
                    "escalation_rate": round((escalation_count / len(insights) * 100) if insights else 0, 2)
                },
                "recommendations": await self._generate_improvement_recommendations(top_patterns, critical_issues)
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning insights: {e}")
            return {"error": str(e)}
    
    async def _generate_improvement_recommendations(self, patterns: List, issues: List) -> List[str]:
        """Generate actionable improvement recommendations"""
        recommendations = []
        
        # Analyze patterns for recommendations
        knowledge_gaps = [p for p in patterns if p.pattern_type == 'knowledge_gap']
        performance_issues = [p for p in patterns if p.pattern_type == 'performance_issue']
        escalation_triggers = [p for p in patterns if p.pattern_type == 'escalation_trigger']
        
        if knowledge_gaps:
            recommendations.append(f"Address {len(knowledge_gaps)} knowledge gaps by adding relevant documentation or training data")
        
        if performance_issues:
            recommendations.append(f"Improve bot performance - {len(performance_issues)} conversations showed poor response quality")
        
        if escalation_triggers:
            recommendations.append(f"Review and optimize escalation triggers - {len(escalation_triggers)} patterns identified")
        
        # Analyze issues for recommendations
        technical_issues = [i for i in issues if i.category == 'technical_limitation']
        new_use_cases = [i for i in issues if i.category == 'new_use_case']
        integration_needs = [i for i in issues if i.category == 'integration_need']
        
        if technical_issues:
            recommendations.append(f"Consider technical improvements to handle {len(technical_issues)} identified limitations")
        
        if new_use_cases:
            recommendations.append(f"Evaluate {len(new_use_cases)} new use cases for potential feature development")
        
        if integration_needs:
            recommendations.append(f"Review {len(integration_needs)} integration requirements for system expansion")
        
        if not recommendations:
            recommendations.append("System is performing well - continue monitoring for new patterns")
        
        return recommendations


# Global service instance
learning_service = ConversationLearningService()