"""
URL patterns for authentication application API endpoints
"""

from django.urls import path
from . import api_views

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('login/', api_views.LoginAPIView.as_view(), name='login'),
    path('logout/', api_views.LogoutAPIView.as_view(), name='logout'),
    path('status/', api_views.auth_status, name='status'),
    path('validate/', api_views.validate_token, name='validate-token'),
    
    # User profile management
    path('profile/', api_views.UserProfileAPIView.as_view(), name='profile'),
    path('change-password/', api_views.change_password, name='change-password'),
    
    # Health check
    path('health/', api_views.AuthHealthCheck.as_view(), name='health-check'),
]