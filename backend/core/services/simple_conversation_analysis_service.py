"""
Simple Conversation Analysis Service
Provides basic conversation-level analysis without external dependencies
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from chat.models import Conversation, Message

logger = logging.getLogger(__name__)


class SimpleConversationAnalysisService:
    """Service for basic conversation-level analysis using message-level data"""
    
    @classmethod
    def analyze_conversation(cls, conversation: Conversation) -> Dict[str, Any]:
        """
        Analyze a conversation using aggregated message-level analysis data
        
        Args:
            conversation: Conversation to analyze
            
        Returns:
            Dictionary containing conversation analysis
        """
        try:
            # Get all messages in the conversation
            messages = conversation.messages.all().order_by('timestamp')
            user_messages = messages.filter(sender_type='user')
            bot_messages = messages.filter(sender_type='bot')
            
            # Get analyzed user messages
            analyzed_user_messages = user_messages.exclude(message_analysis__exact={})
            
            # Basic conversation metadata
            analysis = {
                'conversation_uuid': str(conversation.uuid),
                'analysis_timestamp': timezone.now().isoformat(),
                'analysis_version': 'simple_v1.0',
                
                # Basic metrics
                'message_counts': {
                    'total_messages': messages.count(),
                    'user_messages': user_messages.count(),
                    'bot_messages': bot_messages.count(),
                    'analyzed_user_messages': analyzed_user_messages.count()
                },
                
                # Timing analysis
                'timing_analysis': cls._analyze_timing(messages),
                
                # Issue aggregation from message-level analysis
                'issue_analysis': cls._aggregate_issues(analyzed_user_messages),
                
                # Satisfaction analysis
                'satisfaction_analysis': cls._aggregate_satisfaction(analyzed_user_messages),
                
                # Importance/urgency analysis
                'importance_analysis': cls._aggregate_importance(analyzed_user_messages),
                
                # Documentation opportunities
                'documentation_analysis': cls._aggregate_documentation_potential(analyzed_user_messages),
                
                # FAQ opportunities
                'faq_analysis': cls._aggregate_faq_potential(analyzed_user_messages),
                
                # Conversation summary
                'conversation_summary': cls._generate_summary(conversation, analyzed_user_messages),
                
                # Quality metrics
                'quality_metrics': cls._calculate_quality_metrics(conversation, analyzed_user_messages)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing conversation {conversation.uuid}: {e}")
            return {
                'conversation_uuid': str(conversation.uuid),
                'analysis_timestamp': timezone.now().isoformat(),
                'analysis_version': 'simple_v1.0',
                'error': str(e),
                'status': 'failed'
            }
    
    @classmethod
    def _analyze_timing(cls, messages) -> Dict[str, Any]:
        """Analyze conversation timing patterns"""
        if not messages.exists():
            return {}
        
        first_message = messages.first()
        last_message = messages.last()
        duration = last_message.timestamp - first_message.timestamp
        
        # Calculate average response times for bot messages
        bot_messages = messages.filter(sender_type='bot', response_time__isnull=False)
        avg_response_time = 0
        if bot_messages.exists():
            total_response_time = sum(msg.response_time for msg in bot_messages if msg.response_time)
            avg_response_time = total_response_time / bot_messages.count() if bot_messages.count() > 0 else 0
        
        return {
            'conversation_duration_seconds': duration.total_seconds(),
            'conversation_duration_minutes': duration.total_seconds() / 60,
            'first_message_time': first_message.timestamp.isoformat(),
            'last_message_time': last_message.timestamp.isoformat(),
            'average_bot_response_time': avg_response_time,
            'total_bot_responses': bot_messages.count()
        }
    
    @classmethod
    def _aggregate_issues(cls, analyzed_messages) -> Dict[str, Any]:
        """Aggregate issues from message-level analysis"""
        issue_counts = {}
        total_issues = 0
        issue_details = []
        
        for message in analyzed_messages:
            if message.message_analysis and 'issues_raised' in message.message_analysis:
                for issue in message.message_analysis['issues_raised']:
                    issue_type = issue.get('issue_type', 'Unknown')
                    confidence = issue.get('confidence', 0)
                    
                    if issue_type not in issue_counts:
                        issue_counts[issue_type] = {'count': 0, 'total_confidence': 0, 'messages': []}
                    
                    issue_counts[issue_type]['count'] += 1
                    issue_counts[issue_type]['total_confidence'] += confidence
                    issue_counts[issue_type]['messages'].append({
                        'message_id': str(message.uuid),
                        'confidence': confidence,
                        'content_preview': message.content[:50] + '...' if len(message.content) > 50 else message.content
                    })
                    total_issues += 1
                    
                    issue_details.append({
                        'issue_type': issue_type,
                        'confidence': confidence,
                        'message_id': str(message.uuid),
                        'timestamp': message.timestamp.isoformat()
                    })
        
        # Calculate average confidence for each issue type
        for issue_type, data in issue_counts.items():
            data['average_confidence'] = data['total_confidence'] / data['count'] if data['count'] > 0 else 0
        
        return {
            'total_issues_detected': total_issues,
            'unique_issue_types': len(issue_counts),
            'issue_breakdown': issue_counts,
            'top_issues': sorted(issue_counts.items(), key=lambda x: x[1]['count'], reverse=True)[:5],
            'all_issues': issue_details
        }
    
    @classmethod
    def _aggregate_satisfaction(cls, analyzed_messages) -> Dict[str, Any]:
        """Aggregate satisfaction levels from message-level analysis"""
        satisfaction_counts = {'satisfied': 0, 'dissatisfied': 0, 'neutral': 0, 'unknown': 0}
        satisfaction_scores = []
        confidence_scores = []
        
        for message in analyzed_messages:
            if message.message_analysis and 'satisfaction_level' in message.message_analysis:
                satisfaction_data = message.message_analysis['satisfaction_level']
                level = satisfaction_data.get('level', 'unknown')
                score = satisfaction_data.get('score', 5)
                confidence = satisfaction_data.get('confidence', 0)
                
                satisfaction_counts[level] += 1
                satisfaction_scores.append(score)
                confidence_scores.append(confidence)
        
        total_messages = len(satisfaction_scores)
        avg_satisfaction_score = sum(satisfaction_scores) / total_messages if total_messages > 0 else 5
        avg_confidence = sum(confidence_scores) / total_messages if total_messages > 0 else 0
        
        return {
            'satisfaction_distribution': satisfaction_counts,
            'average_satisfaction_score': avg_satisfaction_score,
            'average_confidence': avg_confidence,
            'total_messages_analyzed': total_messages,
            'satisfaction_percentage': {
                'satisfied': (satisfaction_counts['satisfied'] / total_messages * 100) if total_messages > 0 else 0,
                'dissatisfied': (satisfaction_counts['dissatisfied'] / total_messages * 100) if total_messages > 0 else 0,
                'neutral': (satisfaction_counts['neutral'] / total_messages * 100) if total_messages > 0 else 0
            }
        }
    
    @classmethod
    def _aggregate_importance(cls, analyzed_messages) -> Dict[str, Any]:
        """Aggregate importance/urgency from message-level analysis"""
        importance_counts = {'high': 0, 'medium': 0, 'low': 0}
        urgency_scores = []
        
        for message in analyzed_messages:
            if message.message_analysis and 'importance_level' in message.message_analysis:
                importance_data = message.message_analysis['importance_level']
                level = importance_data.get('level', 'low')
                urgency_score = importance_data.get('urgency_score', 0)
                
                importance_counts[level] += 1
                urgency_scores.append(urgency_score)
        
        total_messages = len(urgency_scores)
        avg_urgency_score = sum(urgency_scores) / total_messages if total_messages > 0 else 0
        
        return {
            'importance_distribution': importance_counts,
            'average_urgency_score': avg_urgency_score,
            'high_importance_percentage': (importance_counts['high'] / total_messages * 100) if total_messages > 0 else 0,
            'urgent_messages_count': importance_counts['high'],
            'requires_immediate_attention': importance_counts['high'] > 0
        }
    
    @classmethod
    def _aggregate_documentation_potential(cls, analyzed_messages) -> Dict[str, Any]:
        """Aggregate documentation improvement opportunities"""
        doc_potential_counts = {'high': 0, 'medium': 0, 'low': 0}
        improvement_areas = []
        
        for message in analyzed_messages:
            if message.message_analysis and 'doc_improvement_potential' in message.message_analysis:
                doc_data = message.message_analysis['doc_improvement_potential']
                potential_level = doc_data.get('potential_level', 'low')
                areas = doc_data.get('improvement_areas', [])
                
                doc_potential_counts[potential_level] += 1
                improvement_areas.extend(areas)
        
        total_messages = len([m for m in analyzed_messages if m.message_analysis and 'doc_improvement_potential' in m.message_analysis])
        
        return {
            'documentation_potential_distribution': doc_potential_counts,
            'high_potential_percentage': (doc_potential_counts['high'] / total_messages * 100) if total_messages > 0 else 0,
            'improvement_opportunities': doc_potential_counts['high'] + doc_potential_counts['medium'],
            'suggested_improvement_areas': list(set(improvement_areas))[:10]  # Top 10 unique areas
        }
    
    @classmethod
    def _aggregate_faq_potential(cls, analyzed_messages) -> Dict[str, Any]:
        """Aggregate FAQ creation opportunities"""
        faq_potential_counts = {'high': 0, 'medium': 0, 'low': 0}
        question_types = {}
        recommended_faqs = []
        
        for message in analyzed_messages:
            if message.message_analysis and 'faq_potential' in message.message_analysis:
                faq_data = message.message_analysis['faq_potential']
                potential_level = faq_data.get('faq_potential', 'low')
                question_type = faq_data.get('question_type', 'other')
                should_add = faq_data.get('should_add_to_faq', False)
                recommended_title = faq_data.get('recommended_faq_title')
                
                faq_potential_counts[potential_level] += 1
                
                if question_type not in question_types:
                    question_types[question_type] = 0
                question_types[question_type] += 1
                
                if should_add and recommended_title:
                    recommended_faqs.append({
                        'title': recommended_title,
                        'question_type': question_type,
                        'message_id': str(message.uuid),
                        'potential_level': potential_level
                    })
        
        total_messages = len([m for m in analyzed_messages if m.message_analysis and 'faq_potential' in m.message_analysis])
        
        return {
            'faq_potential_distribution': faq_potential_counts,
            'high_potential_percentage': (faq_potential_counts['high'] / total_messages * 100) if total_messages > 0 else 0,
            'question_type_breakdown': question_types,
            'recommended_faqs': recommended_faqs,
            'total_faq_opportunities': len(recommended_faqs)
        }
    
    @classmethod
    def _generate_summary(cls, conversation: Conversation, analyzed_messages) -> Dict[str, Any]:
        """Generate a simple conversation summary"""
        # Get the first user message as conversation starter
        first_user_message = conversation.messages.filter(sender_type='user').first()
        last_user_message = conversation.messages.filter(sender_type='user').last()
        
        # Count feedback
        positive_feedback = conversation.messages.filter(feedback='positive').count()
        negative_feedback = conversation.messages.filter(feedback='negative').count()
        
        return {
            'conversation_title': conversation.get_title(),
            'conversation_starter': first_user_message.content[:100] + '...' if first_user_message and len(first_user_message.content) > 100 else (first_user_message.content if first_user_message else 'No user messages'),
            'last_user_message': last_user_message.content[:100] + '...' if last_user_message and len(last_user_message.content) > 100 else (last_user_message.content if last_user_message else 'No user messages'),
            'user_feedback': {
                'positive': positive_feedback,
                'negative': negative_feedback,
                'total': positive_feedback + negative_feedback
            },
            'participant_info': {
                'user': conversation.user.username,
                'user_id': conversation.user.id
            }
        }
    
    @classmethod
    def _calculate_quality_metrics(cls, conversation: Conversation, analyzed_messages) -> Dict[str, Any]:
        """Calculate conversation quality metrics"""
        total_messages = conversation.messages.count()
        user_messages = conversation.messages.filter(sender_type='user').count()
        bot_messages = conversation.messages.filter(sender_type='bot').count()
        
        # Calculate analysis coverage
        analysis_coverage = (analyzed_messages.count() / user_messages * 100) if user_messages > 0 else 0
        
        # Calculate feedback metrics
        positive_feedback = conversation.messages.filter(feedback='positive').count()
        negative_feedback = conversation.messages.filter(feedback='negative').count()
        total_feedback = positive_feedback + negative_feedback
        
        # Engagement metrics
        avg_message_length = 0
        if total_messages > 0:
            total_chars = sum(len(msg.content) for msg in conversation.messages.all())
            avg_message_length = total_chars / total_messages
        
        return {
            'message_analysis_coverage': analysis_coverage,
            'user_engagement_score': min(user_messages / 3, 1.0) * 100,  # Max 100% for 3+ messages
            'feedback_rate': (total_feedback / bot_messages * 100) if bot_messages > 0 else 0,
            'positive_feedback_rate': (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0,
            'average_message_length': avg_message_length,
            'conversation_completeness_score': min(total_messages / 6, 1.0) * 100  # Max 100% for 6+ messages
        }


# Global service instance
simple_conversation_analysis_service = SimpleConversationAnalysisService()