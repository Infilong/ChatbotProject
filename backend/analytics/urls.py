"""
URL patterns for analytics application API endpoints
"""

from django.urls import path
from . import api_views

app_name = 'analytics'

urlpatterns = [
    # Analytics dashboard
    path('api/dashboard/', api_views.analytics_dashboard, name='dashboard'),
    
    # Conversation analysis
    path('api/analyze/', api_views.analyze_conversations, name='analyze-conversations'),
    path('api/insights/', api_views.conversation_insights, name='conversation-insights'),
    
    # Data export
    path('api/export/', api_views.export_analytics, name='export-analytics'),
    
    # Health check
    path('api/health/', api_views.AnalyticsHealthCheck.as_view(), name='health-check'),
]