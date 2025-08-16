"""
Analytics views for document usage and business intelligence
"""

from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.cache import cache_page

from .models import DocumentUsage, ConversationAnalysis, AnalyticsSummary
from documents.models import Document


@staff_member_required
@cache_page(60 * 15)  # Cache for 15 minutes
def document_usage_insights(request):
    """
    Comprehensive document usage insights dashboard
    """
    # Date range (last 30 days by default)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Override with request parameters if provided
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    # Base queryset for the date range
    usage_qs = DocumentUsage.objects.filter(referenced_at__range=[start_date, end_date])
    
    # Key Performance Indicators (KPIs)
    kpis = {
        'total_usage': usage_qs.count(),
        'unique_documents': usage_qs.values('document').distinct().count(),
        'unique_users': usage_qs.values('conversation__user').distinct().count(),
        'avg_relevance': usage_qs.aggregate(avg=Avg('relevance_score'))['avg'] or 0,
        'positive_feedback_rate': _calculate_positive_feedback_rate(usage_qs),
        'avg_processing_time': usage_qs.aggregate(avg=Avg('processing_time'))['avg'] or 0,
    }
    
    # Document Performance Analysis
    document_stats = usage_qs.values(
        'document__name',
        'document__category',
        'document__uuid'
    ).annotate(
        usage_count=Count('id'),
        avg_relevance=Avg('relevance_score'),
        avg_effectiveness=Avg('effectiveness_score'),
        positive_feedback=Count('id', filter=Q(user_feedback='positive')),
        negative_feedback=Count('id', filter=Q(user_feedback='negative')),
        unique_users=Count('conversation__user', distinct=True)
    ).order_by('-usage_count')[:15]
    
    # User Intent Trends
    intent_trends = usage_qs.values('user_intent').annotate(
        count=Count('id'),
        avg_relevance=Avg('relevance_score'),
        success_rate=Count('id', filter=Q(user_feedback='positive')) * 100.0 / Count('id')
    ).order_by('-count')
    
    # Most Effective Keywords
    keyword_effectiveness = _analyze_keyword_effectiveness(usage_qs)
    
    # LLM Model Performance Comparison
    model_performance = usage_qs.values('llm_model_used').annotate(
        usage_count=Count('id'),
        avg_relevance=Avg('relevance_score'),
        avg_processing_time=Avg('processing_time'),
        positive_feedback=Count('id', filter=Q(user_feedback='positive')),
        total_feedback=Count('id', filter=~Q(user_feedback__isnull=True))
    ).order_by('-usage_count')
    
    # Calculate satisfaction rate for each model
    for model in model_performance:
        if model['total_feedback'] > 0:
            model['satisfaction_rate'] = (model['positive_feedback'] / model['total_feedback']) * 100
        else:
            model['satisfaction_rate'] = 0
    
    # Content Category Performance
    category_performance = usage_qs.values('context_category').annotate(
        usage_count=Count('id'),
        avg_relevance=Avg('relevance_score'),
        unique_documents=Count('document', distinct=True),
        avg_effectiveness=Avg('effectiveness_score')
    ).order_by('-usage_count')
    
    context = {
        'kpis': kpis,
        'document_stats': document_stats,
        'intent_trends': intent_trends,
        'keyword_effectiveness': keyword_effectiveness,
        'model_performance': model_performance,
        'category_performance': category_performance,
        'start_date': start_date,
        'end_date': end_date,
        'date_range_days': (end_date - start_date).days,
    }
    
    return render(request, 'analytics/document_usage_insights.html', context)


@staff_member_required
def document_usage_api(request):
    """
    JSON API endpoint for document usage data
    """
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    usage_qs = DocumentUsage.objects.filter(referenced_at__range=[start_date, end_date])
    
    # Daily usage data for charts
    daily_data = usage_qs.extra(
        select={'date': 'DATE(referenced_at)'}
    ).values('date').annotate(
        count=Count('id'),
        avg_relevance=Avg('relevance_score')
    ).order_by('date')
    
    # Document usage data
    document_data = usage_qs.values('document__name').annotate(
        count=Count('id'),
        avg_relevance=Avg('relevance_score')
    ).order_by('-count')[:10]
    
    return JsonResponse({
        'daily_usage': list(daily_data),
        'top_documents': list(document_data),
        'total_usage': usage_qs.count(),
        'unique_documents': usage_qs.values('document').distinct().count(),
        'avg_relevance': usage_qs.aggregate(avg=Avg('relevance_score'))['avg'] or 0,
    })


def _calculate_positive_feedback_rate(usage_qs):
    """Calculate percentage of positive feedback"""
    total_feedback = usage_qs.filter(user_feedback__isnull=False).count()
    if total_feedback == 0:
        return 0
    
    positive_feedback = usage_qs.filter(user_feedback='positive').count()
    return round((positive_feedback / total_feedback) * 100, 1)


def _analyze_keyword_effectiveness(usage_qs):
    """Analyze which keywords lead to most effective document usage"""
    keyword_stats = {}
    
    for usage in usage_qs.filter(keywords_matched__isnull=False).select_related('document'):
        for keyword in usage.keywords_matched or []:
            if keyword not in keyword_stats:
                keyword_stats[keyword] = {
                    'count': 0,
                    'total_relevance': 0,
                    'positive_feedback': 0,
                    'total_feedback': 0
                }
            
            stats = keyword_stats[keyword]
            stats['count'] += 1
            stats['total_relevance'] += usage.relevance_score or 0
            
            if usage.user_feedback == 'positive':
                stats['positive_feedback'] += 1
            if usage.user_feedback:
                stats['total_feedback'] += 1
    
    # Calculate effectiveness metrics
    for keyword, stats in keyword_stats.items():
        stats['avg_relevance'] = stats['total_relevance'] / stats['count'] if stats['count'] > 0 else 0
        stats['satisfaction_rate'] = (stats['positive_feedback'] / stats['total_feedback'] * 100) if stats['total_feedback'] > 0 else 0
        stats['effectiveness_score'] = (stats['avg_relevance'] * 0.7 + stats['satisfaction_rate'] / 100 * 0.3) * 100
    
    # Sort by effectiveness and return top 20
    return sorted(
        keyword_stats.items(),
        key=lambda x: x[1]['effectiveness_score'],
        reverse=True
    )[:20]
