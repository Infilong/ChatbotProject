"""
URL patterns for chat application REST API endpoints
Comprehensive API coverage for frontend integration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, admin_views as views

app_name = 'chat'

# Create router and register ViewSets
router = DefaultRouter()
router.register(r'conversations', api_views.ConversationViewSet, basename='conversation')
router.register(r'messages', api_views.MessageViewSet, basename='message')
router.register(r'sessions', api_views.UserSessionViewSet, basename='session')

urlpatterns = [
    # Include router URLs
    path('api/', include(router.urls)),
    
    # Direct LLM chat endpoint
    path('api/chat/', api_views.LLMChatAPIView.as_view(), name='llm-chat'),
    
    # Search and utility endpoints
    path('api/search/', api_views.conversation_search, name='conversation-search'),
    path('api/bulk-messages/', api_views.bulk_message_create, name='bulk-message-create'),
    path('api/health/', api_views.health_check, name='health-check'),
    
    # Legacy admin views (keep for backward compatibility)
    # Note: Admin views are accessible through Django admin interface
]