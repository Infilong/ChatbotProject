from typing import Dict, Any, Optional, List
from django.db.models import Count, Avg, Q
from django.contrib.auth.models import User
from datetime import datetime, timedelta
from chat.models import Conversation, Message, UserSession
from documents.models import Document


class AnalyticsService:
    """Service for customer analytics and conversation insights"""
    
    @staticmethod
    def get_customer_analytics_context(query: str) -> Dict[str, Any]:
        """Get customer and analytics data based on query content"""
        context_data = {}
        query_lower = query.lower()
        
        # Customer satisfaction analysis
        if any(term in query_lower for term in ['satisfaction', 'feedback', 'rating', 'happy', 'satisfied']):
            satisfaction_stats = Conversation.objects.filter(
                satisfaction_score__isnull=False
            ).aggregate(
                avg_satisfaction=Avg('satisfaction_score'),
                total_rated=Count('id'),
                high_satisfaction=Count('id', filter=Q(satisfaction_score__gte=4.0)),
                low_satisfaction=Count('id', filter=Q(satisfaction_score__lt=3.0))
            )
            
            context_data['satisfaction'] = {
                'average_score': round(satisfaction_stats['avg_satisfaction'] or 0, 2),
                'total_conversations_rated': satisfaction_stats['total_rated'],
                'high_satisfaction_count': satisfaction_stats['high_satisfaction'],
                'low_satisfaction_count': satisfaction_stats['low_satisfaction'],
                'satisfaction_rate': round(
                    (satisfaction_stats['high_satisfaction'] / max(satisfaction_stats['total_rated'], 1)) * 100, 1
                )
            }
        
        # Customer service volume analysis
        if any(term in query_lower for term in ['volume', 'busy', 'traffic', 'usage', 'activity']):
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            
            volume_stats = Conversation.objects.filter(
                started_at__gte=week_ago
            ).aggregate(
                total_conversations=Count('id'),
                avg_messages_per_conv=Avg('message_count'),
                peak_hour_conversations=Count('id', filter=Q(started_at__hour__range=(14, 16)))
            )
            
            context_data['volume'] = {
                'weekly_conversations': volume_stats['total_conversations'],
                'avg_messages_per_conversation': round(volume_stats['avg_messages_per_conv'] or 0, 1),
                'peak_hour_activity': volume_stats['peak_hour_conversations']
            }
        
        # Response time analysis
        if any(term in query_lower for term in ['response', 'time', 'speed', 'quick', 'fast']):
            avg_response_time = Message.objects.filter(
                sender='bot',
                created_at__gte=datetime.now() - timedelta(days=7)
            ).aggregate(
                avg_time=Avg('response_time_seconds')
            )['avg_time']
            
            context_data['response_time'] = {
                'average_response_seconds': round(avg_response_time or 2.1, 1),
                'response_quality': 'Excellent' if (avg_response_time or 2.1) < 3.0 else 'Good'
            }
        
        # Issue categories analysis  
        if any(term in query_lower for term in ['issues', 'problems', 'categories', 'topics']):
            common_issues = Message.objects.filter(
                sender='user',
                created_at__gte=datetime.now() - timedelta(days=30)
            ).values('issue_category').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            context_data['issues'] = {
                'common_categories': [{
                    'category': issue.get('issue_category', 'General'),
                    'count': issue['count']
                } for issue in common_issues]
            }
        
        # Document effectiveness analysis
        if any(term in query_lower for term in ['documents', 'knowledge', 'help', 'information']):
            doc_stats = Document.objects.filter(is_active=True).aggregate(
                total_docs=Count('id'),
                avg_effectiveness=Avg('effectiveness_score'),
                most_referenced=Count('reference_count')
            )
            
            context_data['documents'] = {
                'total_active_documents': doc_stats['total_docs'],
                'average_effectiveness': round(doc_stats['avg_effectiveness'] or 0.0, 2),
                'total_references': doc_stats['most_referenced'] or 0
            }
        
        return context_data
    
    @staticmethod
    def get_conversation_metrics() -> Dict[str, Any]:
        """Get overall conversation metrics"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        metrics = {
            'daily_conversations': Conversation.objects.filter(started_at__date=today).count(),
            'weekly_conversations': Conversation.objects.filter(started_at__gte=week_ago).count(),
            'monthly_conversations': Conversation.objects.filter(started_at__gte=month_ago).count(),
            'total_active_users': UserSession.objects.filter(
                last_activity__gte=datetime.now() - timedelta(hours=24)
            ).count()
        }
        
        return metrics
    
    @staticmethod
    def get_document_analytics() -> Dict[str, Any]:
        """Get document usage analytics"""
        return {
            'total_documents': Document.objects.filter(is_active=True).count(),
            'most_referenced': Document.objects.order_by('-reference_count').first(),
            'least_referenced': Document.objects.filter(reference_count=0).count(),
            'avg_file_size': Document.objects.aggregate(Avg('file_size'))['file_size__avg'] or 0
        }
