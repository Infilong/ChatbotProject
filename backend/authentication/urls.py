"""
URL patterns for authentication application API endpoints
"""

from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # User registration and authentication
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    
    # User profile management
    path('profile/', views.ProfileAPIView.as_view(), name='profile'),
]