"""
URL patterns for chat application REST API endpoints
Comprehensive API coverage for frontend integration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, admin_views, views, message_analytics_api, session_api

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
    
    # TEST ENDPOINT - Remove after debugging
    path('debug-test/', api_views.LLMChatAPIView.as_view(), name='debug-test'),
    path('test-debug/', api_views.test_debug_endpoint, name='test-debug'),
    
    # Search and utility endpoints
    path('search/', api_views.conversation_search, name='conversation-search'),
    path('bulk-messages/', api_views.bulk_message_create, name='bulk-message-create'),
    path('health/', api_views.health_check, name='health-check'),
    
    # Customer Session Management endpoints (frontend integration)
    path('sessions/start/', session_api.start_session, name='session-start'),
    path('sessions/update/', session_api.update_session, name='session-update'),
    path('sessions/end/', session_api.end_session, name='session-end'),
    path('sessions/status/', session_api.session_status, name='session-status'),
    path('sessions/history/', session_api.session_history, name='session-history'),
    path('sessions/cleanup/', session_api.cleanup_expired_sessions, name='session-cleanup'),
    
    # Automatic analysis endpoints
    path('analysis/status/', api_views.automatic_analysis_status, name='analysis-status'),
    path('analysis/trigger/', api_views.trigger_automatic_analysis, name='trigger-analysis'),
    path('analysis/message-status/', api_views.message_analysis_status, name='message-analysis-status'),
    
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