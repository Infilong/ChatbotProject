"""
URL patterns for chat application REST API endpoints
Comprehensive API coverage for frontend integration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, admin_views, views

app_name = 'chat'

# Create router and register ViewSets
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
    
    # Direct LLM chat endpoint - this becomes /api/chat/chat/
    path('chat/', api_views.LLMChatAPIView.as_view(), name='llm-chat'),
    
    # Search and utility endpoints
    path('search/', api_views.conversation_search, name='conversation-search'),
    path('bulk-messages/', api_views.bulk_message_create, name='bulk-message-create'),
    path('health/', api_views.health_check, name='health-check'),
    
    # Admin progress tracking endpoints
    path('admin/langextract-progress/', views.langextract_progress, name='langextract-progress'),
    path('admin/clear-langextract-progress/', views.clear_langextract_progress, name='clear-langextract-progress'),
    
    # Legacy admin views (keep for backward compatibility)
    # Note: Admin views are accessible through Django admin interface
]