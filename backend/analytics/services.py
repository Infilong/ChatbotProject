"""
Automatic Analytics Summary Service
Generates daily analytics summaries automatically when conversations are analyzed
"""

import logging
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db import transaction

from chat.models import Conversation, Message
from .models import AnalyticsSummary, ConversationAnalysis
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class AutomaticAnalyticsSummaryService:
    """Service to automatically generate and update analytics summaries"""
    
    def __init__(self):
        self.logger = logger
    
    def extract_metrics_from_conversation(self, conversation):
        """Extract metrics from conversation's langextract_analysis"""
        if not conversation.langextract_analysis:
            return None
            
        analysis = conversation.langextract_analysis
        
        # Extract sentiment
        sentiment_data = analysis.get('customer_insights', {}).get('sentiment_analysis', {})
        sentiment = sentiment_data.get('overall_sentiment', 'neutral')
        satisfaction_score = sentiment_data.get('satisfaction_score', 6.0)
        
        # Extract urgency and resolution
        urgency_data = analysis.get('customer_insights', {}).get('urgency_assessment', {})
        urgency_level = urgency_data.get('urgency_level', 'medium')
        escalation_recommended = urgency_data.get('escalation_recommended', False)
        
        # Extract conversation type and resolution
        patterns_data = analysis.get('conversation_patterns', {}).get('conversation_flow', {})
        resolution_status = patterns_data.get('resolution_status', 'ongoing')
        
        # Extract issue categories
        issue_data = analysis.get('customer_insights', {}).get('issue_extraction', {})
        issue_categories = issue_data.get('issue_categories', [])
        
        return {
            'sentiment': sentiment,
            'satisfaction_score': satisfaction_score,
            'urgency_level': urgency_level,
            'escalation_recommended': escalation_recommended,
            'resolution_status': resolution_status,
            'issue_categories': issue_categories,
            'analysis_date': conversation.updated_at.date()
        }
    
    def update_analytics_summary_for_date(self, target_date):
        """Create or update AnalyticsSummary for a specific date"""
        self.logger.info(f"Updating analytics summary for {target_date}")
        
        try:
            with transaction.atomic():
                # Get conversations for this date
                conversations = Conversation.objects.filter(
                    updated_at__date=target_date
                ).exclude(langextract_analysis__exact={})
                
                if not conversations.exists():
                    self.logger.debug(f"No analyzed conversations found for {target_date}")
                    return None
                
                # Initialize metrics
                total_conversations = conversations.count()
                total_messages = 0
                unique_users = conversations.values('user').distinct().count()
                
                # Sentiment counters
                positive_count = 0
                negative_count = 0
                neutral_count = 0
                
                # Satisfaction scores
                satisfaction_scores = []
                
                # Issue counters
                total_issues = 0
                resolved_count = 0
                escalated_count = 0
                
                # Process each conversation
                for conversation in conversations:
                    # Count messages
                    msg_count = conversation.messages.count()
                    total_messages += msg_count
                    
                    # Extract analysis metrics
                    metrics = self.extract_metrics_from_conversation(conversation)
                    if not metrics:
                        continue
                        
                    # Count sentiment
                    sentiment = metrics['sentiment']
                    if sentiment in ['positive', 'very_positive']:
                        positive_count += 1
                    elif sentiment in ['negative', 'very_negative']:
                        negative_count += 1
                    else:
                        neutral_count += 1
                    
                    # Collect satisfaction scores
                    if metrics['satisfaction_score']:
                        satisfaction_scores.append(float(metrics['satisfaction_score']))
                    
                    # Count issues
                    if metrics['issue_categories']:
                        total_issues += len(metrics['issue_categories'])
                    
                    # Count resolution status
                    if metrics['resolution_status'] == 'resolved':
                        resolved_count += 1
                    elif metrics['resolution_status'] == 'escalated' or metrics['escalation_recommended']:
                        escalated_count += 1
                
                # Calculate averages
                average_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0.0
                
                # Calculate response time from bot messages
                bot_messages = Message.objects.filter(
                    conversation__in=conversations,
                    sender_type='bot',
                    response_time__isnull=False
                )
                average_response_time = bot_messages.aggregate(Avg('response_time'))['response_time__avg'] or 0.0
                
                # Calculate bot vs human ratio
                total_messages_count = Message.objects.filter(conversation__in=conversations).count()
                bot_messages_count = Message.objects.filter(
                    conversation__in=conversations,
                    sender_type='bot'
                ).count()
                bot_vs_human_ratio = bot_messages_count / total_messages_count if total_messages_count > 0 else 0.0
                
                # Create or update AnalyticsSummary
                summary, created = AnalyticsSummary.objects.update_or_create(
                    date=target_date,
                    defaults={
                        'total_conversations': total_conversations,
                        'total_messages': total_messages,
                        'unique_users': unique_users,
                        'average_satisfaction': round(average_satisfaction, 1),
                        'positive_conversations': positive_count,
                        'negative_conversations': negative_count,
                        'neutral_conversations': neutral_count,
                        'total_issues_raised': total_issues,
                        'resolved_issues': resolved_count,
                        'escalated_issues': escalated_count,
                        'average_response_time': round(average_response_time, 2),
                        'bot_vs_human_ratio': round(bot_vs_human_ratio, 2),
                    }
                )
                
                action = "Created" if created else "Updated"
                self.logger.info(f"{action} analytics summary for {target_date}: "
                               f"{total_conversations} conversations, "
                               f"{average_satisfaction:.1f} avg satisfaction")
                
                return summary
                
        except Exception as e:
            self.logger.error(f"Error updating analytics summary for {target_date}: {e}")
            return None
    
    def trigger_summary_update(self, conversation):
        """Trigger analytics summary update when a conversation is analyzed"""
        if not conversation.langextract_analysis:
            self.logger.debug(f"Conversation {conversation.uuid} has no analysis data")
            return None
        
        # Update summary for the conversation's date
        analysis_date = conversation.updated_at.date()
        summary = self.update_analytics_summary_for_date(analysis_date)
        
        # Also update today's summary if different
        today = timezone.now().date()
        if analysis_date != today:
            self.update_analytics_summary_for_date(today)
        
        return summary
    
    def generate_missing_summaries(self):
        """Generate analytics summaries for all dates with analyzed conversations"""
        self.logger.info("Generating missing analytics summaries")
        
        # Get all unique dates with analyzed conversations
        analyzed_conversations = Conversation.objects.exclude(langextract_analysis__exact={})
        
        if not analyzed_conversations.exists():
            self.logger.info("No analyzed conversations found")
            return 0
        
        # Get date range
        dates_with_conversations = analyzed_conversations.values_list('updated_at__date', flat=True).distinct()
        unique_dates = sorted(set(dates_with_conversations))
        
        summaries_created = 0
        
        for target_date in unique_dates:
            try:
                # Check if summary already exists
                if not AnalyticsSummary.objects.filter(date=target_date).exists():
                    summary = self.update_analytics_summary_for_date(target_date)
                    if summary:
                        summaries_created += 1
                else:
                    self.logger.debug(f"Summary already exists for {target_date}")
            except Exception as e:
                self.logger.error(f"Error creating summary for {target_date}: {e}")
        
        self.logger.info(f"Generated {summaries_created} missing analytics summaries")
        return summaries_created
    
    def cleanup_old_summaries(self, days_to_keep=365):
        """Remove analytics summaries older than specified days"""
        cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
        
        old_summaries = AnalyticsSummary.objects.filter(date__lt=cutoff_date)
        count = old_summaries.count()
        
        if count > 0:
            old_summaries.delete()
            self.logger.info(f"Cleaned up {count} old analytics summaries (older than {cutoff_date})")
        
        return count


# Global instance for easy access
automatic_analytics_service = AutomaticAnalyticsSummaryService()