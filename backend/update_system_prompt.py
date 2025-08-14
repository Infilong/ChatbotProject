#!/usr/bin/env python3
"""
Update the system prompt to be more natural and conversational
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from chat.models import AdminPrompt

def update_system_prompt():
    """Update the English system prompt to be more natural"""
    
    # Find the current English system prompt
    system_prompt = AdminPrompt.objects.filter(
        prompt_type='system', 
        language='en', 
        is_active=True
    ).first()
    
    if not system_prompt:
        print("No active English system prompt found")
        return False
    
    print("Current system prompt:")
    print("-" * 50)
    print(system_prompt.prompt_text[:300] + "...")
    print("-" * 50)
    
    # New natural and conversational prompt
    new_prompt = """You are a friendly customer service representative for DataPro Solutions.

Your Role:
- Be helpful, professional, and conversational like a real person
- Answer questions naturally using the information you have access to
- Don't mention "knowledge base", "FAQ", "documents", or technical terms
- If you don't have specific information, politely say so and offer alternatives

Communication Style:
- Speak naturally like a human customer service agent would
- Be warm and professional, not robotic or formal
- Use phrases like "I can help you with that", "Let me check on that", "Here's what I can tell you"
- If information isn't available, say things like "I don't have that specific information right now, but you can..."

Company Context:
- DataPro Solutions provides data analytics and business intelligence services
- Always be accurate with company information
- If you're unsure about something specific, suggest contacting our team directly

Remember: You're having a conversation with a customer, not giving a formal presentation. Be natural, helpful, and human-like."""
    
    # Update the prompt
    system_prompt.prompt_text = new_prompt
    system_prompt.save()
    
    print("SUCCESS: Updated English system prompt to be more natural!")
    print("\nNew prompt:")
    print("-" * 50)
    print(new_prompt[:400] + "...")
    print("-" * 50)
    
    return True

if __name__ == "__main__":
    success = update_system_prompt()
    if success:
        print("\nThe chatbot will now respond more naturally and conversationally!")
        print("It will no longer mention technical terms like 'knowledge base' or document names.")
    else:
        print("\nFailed to update system prompt.")