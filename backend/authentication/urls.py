"""
URL patterns for authentication application API endpoints
"""

from django.urls import path
from . import api_views

app_name = 'authentication'

urlpatterns = [
    # User registration and authentication
    path('register/', api_views.RegisterAPIView.as_view(), name='register'),
    path('login/', api_views.LoginAPIView.as_view(), name='login'),
    path('logout/', api_views.LogoutAPIView.as_view(), name='logout'),
    
    # User profile management
    path('profile/', api_views.UserProfileAPIView.as_view(), name='profile'),
    
    # Token validation and management
    path('validate-token/', api_views.validate_token, name='validate_token'),
    path('change-password/', api_views.change_password, name='change_password'),
    path('status/', api_views.auth_status, name='auth_status'),
    path('health/', api_views.AuthHealthCheck.as_view(), name='health'),
]