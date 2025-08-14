"""
Message-level analytics API endpoints for detailed chat analysis
"""

import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Conversation, Message

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def message_analytics(request):
    """
    Get detailed message-level analytics for admin dashboard
    Analyzes individual user messages for issues, satisfaction, importance, etc.
    """
    try:
        from core.services.message_analysis_service import message_analysis_service
        
        # Get query parameters
        days = int(request.query_params.get('days', 7))
        conversation_id = request.query_params.get('conversation_id')
        
        # Date filtering
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get conversations to analyze
        conversations_query = Conversation.objects.filter(
            updated_at__gte=start_date,
            messages__sender_type='user'
        ).distinct()
        
        if conversation_id:
            conversations_query = conversations_query.filter(uuid=conversation_id)
        
        conversations = conversations_query[:50]  # Limit to 50 conversations
        
        if not conversations.exists():
            return Response({
                'error': 'No conversations with user messages found for this period',
                'suggestions': [
                    'Try increasing the days parameter',
                    'Check if conversations exist in the database',
                    'Verify conversations have user messages'
                ]
            })
        
        # Analyze all conversations
        analytics_results = []
        summary_stats = {
            'total_conversations': 0,
            'total_user_messages': 0,
            'issues_by_category': {},
            'satisfaction_summary': {'satisfied': 0, 'dissatisfied': 0, 'neutral': 0, 'unknown': 0},
            'importance_summary': {'high': 0, 'medium': 0, 'low': 0},
            'doc_opportunities': 0,
            'faq_candidates': 0
        }
        
        for conversation in conversations:
            # Analyze this conversation's messages
            conversation_analysis = message_analysis_service.analyze_conversation_messages(conversation)
            
            if 'error' not in conversation_analysis:
                analytics_results.append(conversation_analysis)
                summary_stats['total_conversations'] += 1
                summary_stats['total_user_messages'] += conversation_analysis['summary_stats']['total_messages']
                
                # Aggregate issue categories
                for issue_type, count in conversation_analysis['summary_stats']['issues_by_type'].items():
                    summary_stats['issues_by_category'][issue_type] = summary_stats['issues_by_category'].get(issue_type, 0) + count
                
                # Aggregate satisfaction
                for satisfaction_type, count in conversation_analysis['summary_stats']['satisfaction_distribution'].items():
                    summary_stats['satisfaction_summary'][satisfaction_type] += count
                
                # Aggregate importance
                for importance_type, count in conversation_analysis['summary_stats']['importance_distribution'].items():
                    summary_stats['importance_summary'][importance_type] += count
                
                summary_stats['doc_opportunities'] += conversation_analysis['summary_stats']['doc_improvement_opportunities']
                summary_stats['faq_candidates'] += conversation_analysis['summary_stats']['high_faq_potential']
        
        # Generate insights and recommendations
        insights = {
            'top_issues': sorted(summary_stats['issues_by_category'].items(), key=lambda x: x[1], reverse=True)[:5],
            'satisfaction_rate': round(
                (summary_stats['satisfaction_summary']['satisfied'] / max(summary_stats['total_user_messages'], 1)) * 100, 1
            ),
            'high_importance_rate': round(
                (summary_stats['importance_summary']['high'] / max(summary_stats['total_user_messages'], 1)) * 100, 1
            ),
            'doc_improvement_rate': round(
                (summary_stats['doc_opportunities'] / max(summary_stats['total_user_messages'], 1)) * 100, 1
            ),
            'faq_potential_rate': round(
                (summary_stats['faq_candidates'] / max(summary_stats['total_user_messages'], 1)) * 100, 1
            )
        }
        
        # Generate recommendations
        recommendations = []
        if insights['satisfaction_rate'] < 70:
            recommendations.append("Low satisfaction rate detected - review negative feedback and improve response quality")
        if insights['high_importance_rate'] > 30:
            recommendations.append("High percentage of urgent messages - consider improving response times")
        if insights['doc_improvement_rate'] > 20:
            recommendations.append("Many documentation improvement opportunities - update knowledge base")
        if insights['faq_potential_rate'] > 15:
            recommendations.append("Several messages could become FAQs - consider adding to knowledge base")
        
        # Sort conversations by most recent
        analytics_results.sort(key=lambda x: x.get('analysis_timestamp', ''), reverse=True)
        
        return Response({
            'analytics_results': analytics_results,
            'summary_statistics': summary_stats,
            'insights': insights,
            'recommendations': recommendations,
            'analysis_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days_analyzed': days
            },
            'analysis_timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Message analytics error: {e}")
        return Response({
            'error': f'Message analytics failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def analyze_single_conversation(request):
    """
    Analyze a single conversation's messages in detail
    """
    try:
        from core.services.message_analysis_service import message_analysis_service
        
        conversation_uuid = request.data.get('conversation_uuid')
        if not conversation_uuid:
            return Response({
                'error': 'conversation_uuid is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            conversation = Conversation.objects.get(uuid=conversation_uuid)
        except Conversation.DoesNotExist:
            return Response({
                'error': 'Conversation not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Analyze the conversation
        analysis_result = message_analysis_service.analyze_conversation_messages(conversation)
        
        if 'error' in analysis_result:
            return Response(analysis_result, status=status.HTTP_400_BAD_REQUEST)
        
        # Add conversation details
        analysis_result['conversation_details'] = {
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
            'user': conversation.user.username,
            'total_messages': conversation.messages.count()
        }
        
        return Response(analysis_result)
        
    except Exception as e:
        logger.error(f"Single conversation analysis error: {e}")
        return Response({
            'error': f'Analysis failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def message_analysis_summary(request):
    """
    Get a high-level summary of message analysis across all conversations
    """
    try:
        # Get all messages with analysis data
        analyzed_messages = Message.objects.filter(
            sender_type='user',
            message_analysis__isnull=False
        ).exclude(message_analysis__exact={})
        
        if not analyzed_messages.exists():
            return Response({
                'message': 'No analyzed messages found. Run message analysis first.',
                'total_messages': Message.objects.filter(sender_type='user').count(),
                'analyzed_messages': 0
            })
        
        # Aggregate analysis data
        summary = {
            'overview': {
                'total_user_messages': Message.objects.filter(sender_type='user').count(),
                'analyzed_messages': analyzed_messages.count(),
                'analysis_coverage': round(
                    (analyzed_messages.count() / Message.objects.filter(sender_type='user').count()) * 100, 1
                )
            },
            'issue_categories': {},
            'satisfaction_levels': {'satisfied': 0, 'dissatisfied': 0, 'neutral': 0, 'unknown': 0},
            'importance_levels': {'high': 0, 'medium': 0, 'low': 0},
            'doc_improvement': {'high': 0, 'medium': 0, 'low': 0},
            'faq_potential': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        for message in analyzed_messages:
            analysis = message.message_analysis
            
            # Count issues
            for issue in analysis.get('issues_raised', []):
                issue_type = issue['issue_type']
                summary['issue_categories'][issue_type] = summary['issue_categories'].get(issue_type, 0) + 1
            
            # Count satisfaction
            satisfaction = analysis.get('satisfaction_level', {}).get('level', 'unknown')
            summary['satisfaction_levels'][satisfaction] += 1
            
            # Count importance
            importance = analysis.get('importance_level', {}).get('level', 'low')
            summary['importance_levels'][importance] += 1
            
            # Count doc improvement potential
            doc_potential = analysis.get('doc_improvement_potential', {}).get('potential_level', 'low')
            summary['doc_improvement'][doc_potential] += 1
            
            # Count FAQ potential
            faq_potential = analysis.get('faq_potential', {}).get('faq_potential', 'low')
            summary['faq_potential'][faq_potential] += 1
        
        # Sort issue categories by frequency
        summary['top_issues'] = sorted(summary['issue_categories'].items(), key=lambda x: x[1], reverse=True)[:10]
        
        return Response({
            'summary': summary,
            'analysis_timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Message analysis summary error: {e}")
        return Response({
            'error': f'Summary generation failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)