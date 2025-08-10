"""
REST API views for documents application
"""

import logging
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination

from .models import Document

logger = logging.getLogger(__name__)


class DocumentPagination(PageNumberPagination):
    """Pagination for document lists"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class DocumentViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for reading documents
    Provides read-only access to documents with search and filtering
    """
    
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DocumentPagination
    
    def get_queryset(self):
        """Get documents with optional filtering"""
        queryset = Document.objects.filter(is_active=True)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Search in content
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                extracted_text__icontains=search
            )
        
        # Filter by file type
        file_type = self.request.query_params.get('file_type')
        if file_type:
            queryset = queryset.filter(name__iendswith=f'.{file_type}')
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer"""
        # Import here to avoid circular imports
        from .serializers import DocumentSerializer, DocumentListSerializer
        
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get document details"""
        instance = self.get_object()
        
        # Check if user has permission to view this document
        if not self.has_object_permission(request, None, instance):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access document"""
        # For now, all authenticated users can access active documents
        # This can be enhanced with user-specific permissions
        return obj.is_active


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_document(request, document_uuid):
    """
    Download document file
    """
    try:
        document = get_object_or_404(Document, uuid=document_uuid, is_active=True)
        
        # Check permissions (can be enhanced)
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Return file response
        if document.file:
            response = FileResponse(
                document.file.open('rb'),
                as_attachment=True,
                filename=document.name
            )
            return response
        else:
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        logger.error(f"Document download error: {e}")
        return Response(
            {'error': 'Download failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def search_documents(request):
    """
    Advanced document search
    """
    try:
        query = request.data.get('query', '').strip()
        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category_ids = request.data.get('categories', [])
        file_types = request.data.get('file_types', [])
        
        # Build search queryset
        queryset = Document.objects.filter(is_active=True)
        
        # Text search
        queryset = queryset.filter(extracted_text__icontains=query)
        
        # Category filter
        if category_ids:
            # Since category is a CharField, filter by name containing any of the provided categories
            from django.db.models import Q
            category_filter = Q()
            for cat_name in category_ids:
                category_filter |= Q(category__icontains=str(cat_name))
            queryset = queryset.filter(category_filter)
        
        # File type filter
        if file_types:
            file_conditions = []
            for file_type in file_types:
                file_conditions.append(queryset.filter(name__iendswith=f'.{file_type}'))
            
            if file_conditions:
                combined_q = file_conditions[0]
                for condition in file_conditions[1:]:
                    combined_q = combined_q.union(condition)
                queryset = combined_q
        
        # Paginate results
        paginator = DocumentPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        # Serialize results
        from .serializers import DocumentListSerializer
        serializer = DocumentListSerializer(page, many=True)
        
        return paginator.get_paginated_response(serializer.data)
        
    except Exception as e:
        logger.error(f"Document search error: {e}")
        return Response(
            {'error': 'Search failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class CategoryListAPIView(APIView):
    """
    API to list document categories
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all unique document categories"""
        try:
            # Get unique categories from documents
            categories = Document.objects.filter(
                is_active=True,
                category__isnull=False
            ).exclude(category='').values_list('category', flat=True).distinct()
            
            category_data = []
            for category_name in categories:
                doc_count = Document.objects.filter(
                    is_active=True,
                    category=category_name
                ).count()
                
                category_data.append({
                    'name': category_name,
                    'document_count': doc_count
                })
            
            return Response({
                'categories': sorted(category_data, key=lambda x: x['name']),
                'total_count': len(category_data)
            })
            
        except Exception as e:
            logger.error(f"Category list error: {e}")
            return Response(
                {'error': 'Failed to retrieve categories'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def document_stats(request):
    """
    Get document statistics
    """
    try:
        # Basic statistics
        total_documents = Document.objects.filter(is_active=True).count()
        total_categories = DocumentCategory.objects.filter(is_active=True).count()
        
        # File type distribution
        file_types = {}
        documents = Document.objects.filter(is_active=True)
        for doc in documents:
            ext = doc.name.split('.')[-1].lower() if '.' in doc.name else 'unknown'
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # Category distribution
        category_stats = []
        categories = Document.objects.filter(
            is_active=True,
            category__isnull=False
        ).exclude(category='').values_list('category', flat=True).distinct()
        
        for category_name in categories:
            doc_count = Document.objects.filter(
                is_active=True,
                category=category_name
            ).count()
            if doc_count > 0:
                category_stats.append({
                    'category': category_name,
                    'count': doc_count,
                    'percentage': round((doc_count / total_documents * 100), 2) if total_documents > 0 else 0
                })
        
        # Recent uploads (last 7 days)
        from datetime import timedelta
        from django.utils import timezone
        week_ago = timezone.now() - timedelta(days=7)
        recent_uploads = Document.objects.filter(
            is_active=True,
            uploaded_at__gte=week_ago
        ).count()
        
        stats_data = {
            'overview': {
                'total_documents': total_documents,
                'total_categories': total_categories,
                'recent_uploads': recent_uploads
            },
            'file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
            'category_distribution': sorted(category_stats, key=lambda x: x['count'], reverse=True),
            'storage_info': {
                'note': 'Storage information would require file size calculation'
            }
        }
        
        return Response(stats_data)
        
    except Exception as e:
        logger.error(f"Document stats error: {e}")
        return Response(
            {'error': 'Failed to generate statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_document_usage(request):
    """
    Get document usage analytics (admin only)
    """
    try:
        # This would track document access and usage
        # For now, return simulated data
        
        usage_data = {
            'most_accessed_documents': [
                {'name': 'User Manual.pdf', 'access_count': 45, 'last_accessed': '2025-08-10T10:30:00Z'},
                {'name': 'API Documentation.md', 'access_count': 32, 'last_accessed': '2025-08-10T09:15:00Z'},
                {'name': 'FAQ.docx', 'access_count': 28, 'last_accessed': '2025-08-10T11:20:00Z'}
            ],
            'popular_search_terms': [
                {'term': 'login', 'count': 23},
                {'term': 'API key', 'count': 18},
                {'term': 'password reset', 'count': 15}
            ],
            'category_usage': [
                {'category': 'Technical Documentation', 'access_count': 87},
                {'category': 'User Guides', 'access_count': 65},
                {'category': 'Policy Documents', 'access_count': 23}
            ],
            'access_patterns': {
                'peak_hours': [9, 10, 11, 14, 15, 16],
                'peak_days': ['Monday', 'Tuesday', 'Wednesday'],
                'total_access_this_month': 456
            }
        }
        
        return Response(usage_data)
        
    except Exception as e:
        logger.error(f"Document usage analytics error: {e}")
        return Response(
            {'error': 'Failed to generate usage analytics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DocumentHealthCheck(APIView):
    """
    Document service health check
    """
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """Check document service health"""
        try:
            # Test database connection
            document_count = Document.objects.count()
            category_count = DocumentCategory.objects.count()
            
            # Test file system access
            active_docs = Document.objects.filter(is_active=True)[:5]
            accessible_files = 0
            
            for doc in active_docs:
                try:
                    if doc.file and doc.file.storage.exists(doc.file.name):
                        accessible_files += 1
                except:
                    pass
            
            health_data = {
                'status': 'healthy',
                'timestamp': timezone.now().isoformat(),
                'services': {
                    'database': 'connected',
                    'file_storage': 'accessible' if accessible_files > 0 else 'warning'
                },
                'stats': {
                    'total_documents': document_count,
                    'total_categories': category_count,
                    'accessible_files': accessible_files
                }
            }
            
            return Response(health_data)
            
        except Exception as e:
            logger.error(f"Document health check failed: {e}")
            return Response(
                {
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )