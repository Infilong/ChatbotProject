#!/usr/bin/env python
"""
Check API configuration status
"""

import os
import sys
import django

# Setup Django
sys.path.append('backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')

try:
    django.setup()
    
    from chat.models import APIConfiguration
    
    print("🔍 Checking API Configurations...")
    print("=" * 50)
    
    configs = APIConfiguration.objects.all()
    
    if not configs.exists():
        print("❌ No API configurations found")
        print("\n💡 To add Gemini API key:")
        print("1. Go to: http://localhost:8000/admin/")
        print("2. Find 'Api configurations' section") 
        print("3. Click 'Add Api configuration'")
        print("4. Fill in:")
        print("   - Provider: Google Gemini")
        print("   - Model name: gemini-pro")
        print("   - API Key: [Your API key]")
        print("   - Is active: ✓ Checked")
    else:
        print(f"✅ Found {configs.count()} API configuration(s):")
        
        for config in configs:
            key_preview = f"{config.api_key[:10]}..." if config.api_key else "None"
            active_status = "✅ Active" if config.is_active else "❌ Inactive"
            
            print(f"\n📋 {config.get_provider_display()}")
            print(f"   Provider: {config.provider}")
            print(f"   Model: {config.model_name}")
            print(f"   API Key: {key_preview}")
            print(f"   Status: {active_status}")
            
        print(f"\n🎯 Your admin chat should now work with real LLM!")
        print("   Switch to the provider you configured and test it.")
    
    print("\n" + "=" * 50)
    
except Exception as e:
    print(f"Error: {e}")
    print("Make sure Django server is stopped before running this script.")