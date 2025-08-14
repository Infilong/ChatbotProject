"""
Script to generate AnalyticsSummary records from conversation analysis data
This will populate the analytics dashboard with proper metrics
"""

import os
import sys
import django
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from chat.models import Conversation, Message
from analytics.models import AnalyticsSummary, ConversationAnalysis
from django.contrib.auth.models import User


def extract_metrics_from_conversation(conversation):
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


def create_analytics_summary_for_date(target_date):
    """Create AnalyticsSummary for a specific date"""
    print(f"Generating analytics summary for {target_date}")
    
    # Get conversations for this date
    conversations = Conversation.objects.filter(
        updated_at__date=target_date
    ).exclude(langextract_analysis__exact={})
    
    if not conversations.exists():
        print(f"  No analyzed conversations found for {target_date}")
        return None
    
    print(f"  Found {conversations.count()} analyzed conversations")
    
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
        metrics = extract_metrics_from_conversation(conversation)
        if not metrics:
            continue
            
        # Count sentiment
        sentiment = metrics['sentiment']
        if sentiment == 'positive':
            positive_count += 1
        elif sentiment == 'negative':
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
    average_response_time = 2.5  # Default placeholder
    bot_vs_human_ratio = 0.9  # Placeholder - mostly bot responses
    
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
            'average_response_time': average_response_time,
            'bot_vs_human_ratio': bot_vs_human_ratio,
        }
    )
    
    action = "Created" if created else "Updated"
    print(f"  {action} summary: {total_conversations} convs, {average_satisfaction:.1f} avg satisfaction")
    
    return summary


def generate_analytics_summaries():
    """Generate analytics summaries for all dates with analyzed conversations"""
    print("=== Generating Analytics Summaries ===")
    
    # Get all unique dates with analyzed conversations
    analyzed_conversations = Conversation.objects.exclude(langextract_analysis__exact={})
    
    if not analyzed_conversations.exists():
        print("No analyzed conversations found!")
        return
    
    # Get date range
    dates_with_conversations = analyzed_conversations.values_list('updated_at__date', flat=True).distinct()
    unique_dates = sorted(set(dates_with_conversations))
    
    print(f"Found conversations on {len(unique_dates)} different dates")
    
    summaries_created = 0
    
    for target_date in unique_dates:
        try:
            summary = create_analytics_summary_for_date(target_date)
            if summary:
                summaries_created += 1
        except Exception as e:
            print(f"  Error creating summary for {target_date}: {e}")
    
    # Also create summary for today if we have any conversations
    today = timezone.now().date()
    if today not in unique_dates:
        recent_conversations = Conversation.objects.filter(
            updated_at__date=today
        ).exclude(langextract_analysis__exact={})
        
        if recent_conversations.exists():
            try:
                summary = create_analytics_summary_for_date(today)
                if summary:
                    summaries_created += 1
            except Exception as e:
                print(f"  Error creating summary for today: {e}")
    
    print(f"\n=== Results ===")
    print(f"Analytics summaries created/updated: {summaries_created}")
    
    # Show final statistics
    total_summaries = AnalyticsSummary.objects.count()
    print(f"Total AnalyticsSummary records: {total_summaries}")
    
    if total_summaries > 0:
        print(f"\n=== Recent Summaries ===")
        for summary in AnalyticsSummary.objects.all()[:3]:
            print(f"{summary.date}: {summary.total_conversations} convs, "
                  f"{summary.average_satisfaction:.1f} satisfaction, "
                  f"{summary.positive_conversations}+ {summary.negative_conversations}- {summary.neutral_conversations}neutral")
    
    print(f"\n[+] Analytics summaries generated! Check the Django admin at:")
    print(f"  http://localhost:8000/admin/analytics/analyticssummary/")


if __name__ == '__main__':
    generate_analytics_summaries()