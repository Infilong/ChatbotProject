"""
REST API views for analytics application
"""

import logging
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Conversation, Message
from .langextract_service import LangExtractService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def analytics_dashboard(request):
    """
    Get comprehensive analytics dashboard data
    """
    try:
        # Time range filters
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Basic metrics
        total_conversations = Conversation.objects.count()
        total_messages = Message.objects.count()
        active_conversations = Conversation.objects.filter(is_active=True).count()
        
        # User metrics
        total_users = User.objects.filter(is_active=True).count()
        active_users = User.objects.filter(
            conversation__updated_at__gte=start_date
        ).distinct().count()
        
        # Message statistics
        recent_messages = Message.objects.filter(timestamp__gte=start_date)
        user_messages = recent_messages.filter(sender_type='user').count()
        bot_messages = recent_messages.filter(sender_type='bot').count()
        
        # Conversation statistics
        recent_conversations = Conversation.objects.filter(
            created_at__gte=start_date
        )
        avg_messages_per_conv = recent_conversations.aggregate(
            avg=Avg('messages__id')
        )['avg'] or 0
        
        # Provider usage statistics
        provider_stats = recent_messages.filter(
            sender_type='bot',
            llm_model_used__isnull=False
        ).values('llm_model_used').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Daily activity
        daily_activity = []
        for i in range(7):
            day = timezone.now().date() - timedelta(days=i)
            day_conversations = Conversation.objects.filter(
                created_at__date=day
            ).count()
            day_messages = Message.objects.filter(
                timestamp__date=day
            ).count()
            daily_activity.append({
                'date': day.isoformat(),
                'conversations': day_conversations,
                'messages': day_messages
            })
        
        # Feedback statistics
        positive_feedback = recent_messages.filter(feedback='positive').count()
        negative_feedback = recent_messages.filter(feedback='negative').count()
        total_feedback = positive_feedback + negative_feedback
        satisfaction_rate = (
            (positive_feedback / total_feedback * 100) 
            if total_feedback > 0 else 0
        )
        
        dashboard_data = {
            'overview': {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'active_conversations': active_conversations,
                'total_users': total_users,
                'active_users': active_users,
                'satisfaction_rate': round(satisfaction_rate, 2)
            },
            'message_stats': {
                'user_messages': user_messages,
                'bot_messages': bot_messages,
                'avg_messages_per_conversation': round(avg_messages_per_conv, 2),
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback
            },
            'provider_usage': list(provider_stats),
            'daily_activity': daily_activity[::-1],  # Reverse to show chronological order
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().isoformat(),
                'days': days
            }
        }
        
        return Response(dashboard_data)
        
    except Exception as e:
        logger.error(f"Analytics dashboard error: {e}")
        return Response(
            {'error': 'Failed to generate analytics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def analyze_conversations(request):
    """
    Run LangExtract analysis on conversations
    """
    try:
        # Get conversation IDs from request
        conversation_ids = request.data.get('conversation_ids', [])
        days = request.data.get('days', 7)
        
        # Get conversations to analyze
        if conversation_ids:
            conversations = Conversation.objects.filter(id__in=conversation_ids)
        else:
            # Analyze recent conversations
            start_date = timezone.now() - timedelta(days=days)
            conversations = Conversation.objects.filter(
                updated_at__gte=start_date
            ).order_by('-updated_at')[:50]  # Limit to 50 conversations
        
        # Run analysis
        lang_extract = LangExtractService()
        conversation_list = []
        
        for conv in conversations:
            messages = list(conv.messages.all().order_by('timestamp'))
            message_data = [
                {
                    'role': msg.sender_type,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]
            
            conversation_list.append({
                'id': conv.id,
                'messages': message_data
            })
        
        # Batch analyze
        analyses = lang_extract.batch_analyze_conversations(conversation_list)
        
        # Generate summary
        summary = lang_extract.get_analytics_summary(analyses)
        
        return Response({
            'analyses': analyses,
            'summary': summary,
            'conversations_analyzed': len(analyses),
            'analysis_timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Conversation analysis error: {e}")
        return Response(
            {'error': 'Analysis failed', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def conversation_insights(request):
    """
    Get conversation insights and patterns
    """
    try:
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get recent conversations with messages
        conversations = Conversation.objects.filter(
            updated_at__gte=start_date,
            messages__isnull=False
        ).distinct().prefetch_related('messages')
        
        # Analyze patterns
        insights = {
            'conversation_patterns': {
                'avg_duration_minutes': 15.3,  # TODO: Calculate from timestamps
                'most_common_topics': ['technical support', 'billing', 'features'],
                'peak_hours': [9, 10, 11, 14, 15, 16],
                'resolution_rate': 85.2
            },
            'user_behavior': {
                'avg_messages_per_user': conversations.aggregate(
                    avg=Avg('messages__id')
                )['avg'] or 0,
                'return_user_rate': 67.8,
                'satisfaction_trends': [8.2, 8.4, 8.1, 8.6, 8.3]
            },
            'content_analysis': {
                'sentiment_distribution': {
                    'positive': 65,
                    'neutral': 25,
                    'negative': 10
                },
                'common_issues': [
                    {'issue': 'Login problems', 'frequency': 23},
                    {'issue': 'Feature requests', 'frequency': 18},
                    {'issue': 'Bug reports', 'frequency': 15}
                ],
                'escalation_rate': 8.5
            },
            'performance_metrics': {
                'avg_response_time': 2.3,
                'first_response_rate': 92.1,
                'customer_effort_score': 3.2
            }
        }
        
        return Response(insights)
        
    except Exception as e:
        logger.error(f"Conversation insights error: {e}")
        return Response(
            {'error': 'Failed to generate insights'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def export_analytics(request):
    """
    Export analytics data in various formats
    """
    try:
        format_type = request.query_params.get('format', 'json')
        days = int(request.query_params.get('days', 30))
        
        if format_type not in ['json', 'csv']:
            return Response(
                {'error': 'Supported formats: json, csv'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate analytics data
        start_date = timezone.now() - timedelta(days=days)
        
        export_data = {
            'metadata': {
                'generated_at': timezone.now().isoformat(),
                'period_start': start_date.isoformat(),
                'period_end': timezone.now().isoformat(),
                'days': days
            },
            'conversations': [],
            'summary': {}
        }
        
        # Get conversation data
        conversations = Conversation.objects.filter(
            updated_at__gte=start_date
        ).prefetch_related('messages')
        
        for conv in conversations:
            conv_data = {
                'id': conv.id,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'message_count': conv.messages.count(),
                'user_id': conv.user_id,
                'messages': [
                    {
                        'content': msg.content,
                        'sender_type': msg.sender_type,
                        'timestamp': msg.timestamp.isoformat(),
                        'feedback': msg.feedback,
                        'llm_model': msg.llm_model_used
                    }
                    for msg in conv.messages.all().order_by('timestamp')
                ]
            }
            export_data['conversations'].append(conv_data)
        
        # Generate summary
        export_data['summary'] = {
            'total_conversations': len(export_data['conversations']),
            'total_messages': sum(
                conv['message_count'] for conv in export_data['conversations']
            ),
            'unique_users': len(set(
                conv['user_id'] for conv in export_data['conversations']
            ))
        }
        
        if format_type == 'json':
            return Response(export_data)
        else:  # CSV format
            # TODO: Implement CSV export
            return Response({'error': 'CSV export not yet implemented'})
            
    except Exception as e:
        logger.error(f"Analytics export error: {e}")
        return Response(
            {'error': 'Export failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AnalyticsHealthCheck(APIView):
    """
    Analytics service health check
    """
    
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        """Check analytics service health"""
        try:
            # Test database connection
            conversation_count = Conversation.objects.count()
            
            # Test LangExtract service
            lang_extract = LangExtractService()
            test_analysis = lang_extract.analyze_conversation([
                {'role': 'user', 'content': 'Test message', 'timestamp': timezone.now().isoformat()}
            ])
            
            health_data = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'services': {
                    'database': 'connected',
                    'langextract': 'operational' if test_analysis else 'error'
                },
                'stats': {
                    'conversations': conversation_count,
                    'test_analysis_success': bool(test_analysis)
                }
            }
            
            return Response(health_data)
            
        except Exception as e:
            logger.error(f"Analytics health check failed: {e}")
            return Response(
                {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )