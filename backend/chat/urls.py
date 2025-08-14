"""
URL patterns for chat application REST API endpoints
Comprehensive API coverage for frontend integration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, admin_views, views, message_analytics_api

app_name = 'chat'

# Create router and register ViewSets with UUID-based lookup
router = DefaultRouter()
router.register(r'conversations', api_views.ConversationViewSet, basename='conversation')
router.register(r'messages', api_views.MessageViewSet, basename='message')
router.register(r'sessions', api_views.UserSessionViewSet, basename='session')

urlpatterns = [
    # Include router URLs - these become /api/chat/api/conversations/, etc.
    path('api/', include(router.urls)),
    
    # Secure JWT-authenticated chat endpoints
    path('secure/', views.ChatAPIView.as_view(), name='secure-chat'),
    path('history/', views.ConversationHistoryAPIView.as_view(), name='conversation-history'),
    path('history/<uuid:conversation_id>/', views.ConversationHistoryAPIView.as_view(), name='conversation-detail'),
    
    # Direct LLM chat endpoint - this becomes /api/chat/
    path('', api_views.LLMChatAPIView.as_view(), name='llm-chat'),
    
    # Search and utility endpoints
    path('search/', api_views.conversation_search, name='conversation-search'),
    path('bulk-messages/', api_views.bulk_message_create, name='bulk-message-create'),
    path('health/', api_views.health_check, name='health-check'),
    
    # Automatic analysis endpoints
    path('analysis/status/', api_views.automatic_analysis_status, name='analysis-status'),
    path('analysis/trigger/', api_views.trigger_automatic_analysis, name='trigger-analysis'),
    
    # Message-level analytics endpoints
    path('analytics/messages/', message_analytics_api.message_analytics, name='message-analytics'),
    path('analytics/conversation/', message_analytics_api.analyze_single_conversation, name='analyze-conversation'),
    path('analytics/summary/', message_analytics_api.message_analysis_summary, name='message-summary'),
    
    # Admin progress tracking endpoints
    path('admin/langextract-progress/', views.langextract_progress, name='langextract-progress'),
    path('admin/clear-langextract-progress/', views.clear_langextract_progress, name='clear-langextract-progress'),
    
    # Legacy admin views (keep for backward compatibility)
    # Note: Admin views are accessible through Django admin interface
]