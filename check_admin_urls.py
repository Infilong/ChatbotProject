#!/usr/bin/env python
"""
Check if admin LLM URLs are working
"""

import os
import sys
import django
import requests
from django.core.management import execute_from_command_line

# Setup Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')

def check_urls():
    """Check if the admin URLs are accessible"""
    
    base_url = "http://localhost:8000"
    
    urls_to_check = [
        "/admin/",
        "/admin/llm-chat/", 
        "/admin/knowledge-base-test/",
        "/admin/llm-chat/api/",
        "/admin/knowledge-search/api/",
        "/admin/document-stats/api/"
    ]
    
    print("🔍 Checking Admin LLM URLs...")
    print("=" * 50)
    
    for url in urls_to_check:
        full_url = base_url + url
        try:
            response = requests.get(full_url, timeout=5)
            status = "✅" if response.status_code in [200, 302, 403] else "❌"
            print(f"{status} {url} - Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {url} - Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("📋 Instructions to access LLM features:")
    print("1. Go to: http://localhost:8000/admin/")
    print("2. Login with: admin / admin123")
    print("3. Look for LLM Features section on the home page")
    print("4. Or access directly:")
    print("   - LLM Chat: http://localhost:8000/admin/llm-chat/")
    print("   - Knowledge Test: http://localhost:8000/admin/knowledge-base-test/")

if __name__ == "__main__":
    check_urls()