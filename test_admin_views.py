#!/usr/bin/env python
"""
Test admin LLM views
"""

import os
import sys
import django

# Setup Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_admin_views():
    """Test admin LLM views"""
    
    client = Client()
    
    print("🧪 Testing Admin LLM Views...")
    print("=" * 50)
    
    # Create test user if needed
    try:
        user = User.objects.get(username='admin')
        print("✅ Admin user exists")
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        print("✅ Created admin user")
    
    # Login
    login_success = client.login(username='admin', password='admin123')
    print(f"✅ Login successful: {login_success}")
    
    # Test URLs
    urls_to_test = [
        '/admin/',
        '/admin/llm/chat/',
        '/admin/llm/knowledge-test/',
    ]
    
    for url in urls_to_test:
        try:
            response = client.get(url)
            status = "✅" if response.status_code == 200 else f"❌ ({response.status_code})"
            print(f"{status} {url}")
            
            if response.status_code != 200:
                print(f"   Error: {response.content.decode()[:200]}...")
                
        except Exception as e:
            print(f"❌ {url} - Exception: {str(e)[:100]}...")
    
    print("\n" + "=" * 50)
    print("🎯 URLs to access:")
    print("   Admin Home: http://localhost:8000/admin/")
    print("   LLM Chat: http://localhost:8000/admin/llm/chat/")
    print("   Knowledge Test: http://localhost:8000/admin/llm/knowledge-test/")

if __name__ == "__main__":
    test_admin_views()