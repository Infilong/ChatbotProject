"""
WebSocket routing configuration for chat application
"""

from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # User chat WebSocket
    path('ws/chat/', consumers.ChatConsumer.as_asgi()),
    
    # Admin monitoring WebSocket
    path('ws/admin/chat/', consumers.AdminChatConsumer.as_asgi()),
]