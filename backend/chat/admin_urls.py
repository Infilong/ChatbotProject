"""
Custom admin URLs for LLM features
"""

from django.urls import path
from . import admin_views

app_name = 'admin_llm'

urlpatterns = [
    # LLM Chat Interface
    path('chat/', admin_views.admin_llm_chat, name='llm_chat'),
    path('chat/api/', admin_views.AdminLLMChatAPI.as_view(), name='llm_chat_api'),
    path('chat/history/api/', admin_views.AdminChatHistoryAPI.as_view(), name='chat_history_api'),
]