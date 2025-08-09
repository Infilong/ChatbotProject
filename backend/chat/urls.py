"""
URL patterns for chat application API endpoints
"""

from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Chat API endpoints
    path('conversations/', views.ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:conversation_id>/messages/', views.MessageListCreateView.as_view(), name='message-list'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message-detail'),
    path('messages/<int:pk>/feedback/', views.MessageFeedbackView.as_view(), name='message-feedback'),
    
    # LLM API management
    path('llm/configs/', views.APIConfigurationListView.as_view(), name='llm-config-list'),
    path('llm/test/', views.LLMTestView.as_view(), name='llm-test'),
    path('llm/chat/', views.LLMChatView.as_view(), name='llm-chat'),
    
    # System prompts
    path('prompts/', views.AdminPromptListView.as_view(), name='prompt-list'),
    path('prompts/<int:pk>/', views.AdminPromptDetailView.as_view(), name='prompt-detail'),
    
    # User sessions
    path('sessions/', views.UserSessionListView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', views.UserSessionDetailView.as_view(), name='session-detail'),
]