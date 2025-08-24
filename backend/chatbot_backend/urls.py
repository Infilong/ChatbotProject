"""
URL configuration for chatbot_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse
from django.conf.urls.i18n import i18n_patterns
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
import json

def test_view(request):
    return HttpResponse("Django server is working! Go to <a href='/admin/'>/admin/</a>")

@csrf_exempt
@login_required
def timezone_detect_view(request):
    """API endpoint for timezone detection - handled by middleware."""
    # This view should never be reached as middleware intercepts the request
    return JsonResponse({
        'success': False,
        'error': 'Timezone detection should be handled by middleware'
    })

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', test_view),  # Test view at root
    path('admin/llm/', include('chat.admin_urls')),  # Custom admin URLs before main admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/timezone/detect/', timezone_detect_view, name='timezone_detect'),
    path('api/chat/', include('chat.urls')),
    path('api/documents/', include('documents.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/auth/', include('authentication.urls')),
    
    # JWT Authentication endpoints (for future use)
    path('api/jwt/login/', TokenObtainPairView.as_view(), name='jwt_login'),
    path('api/jwt/refresh/', TokenRefreshView.as_view(), name='jwt_token_refresh'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
