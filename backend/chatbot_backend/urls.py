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
from django.http import HttpResponse
from django.conf.urls.i18n import i18n_patterns

def test_view(request):
    return HttpResponse("Django server is working! Go to <a href='/admin/'>/admin/</a>")

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('', test_view),  # Test view at root
    path('admin/', admin.site.urls),
]
