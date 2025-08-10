"""
URL patterns for documents application API endpoints
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

app_name = 'documents'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'documents', api_views.DocumentViewSet, basename='document')

urlpatterns = [
    # Include router URLs
    path('api/', include(router.urls)),
    
    # Document operations
    path('api/download/<uuid:document_uuid>/', api_views.download_document, name='download'),
    path('api/search/', api_views.search_documents, name='search'),
    path('api/stats/', api_views.document_stats, name='stats'),
    
    # Categories
    path('api/categories/', api_views.CategoryListAPIView.as_view(), name='categories'),
    
    # Admin analytics
    path('api/admin/usage/', api_views.admin_document_usage, name='admin-usage'),
    
    # Health check
    path('api/health/', api_views.DocumentHealthCheck.as_view(), name='health-check'),
]