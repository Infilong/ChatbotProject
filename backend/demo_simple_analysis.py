"""
Simple synchronous demo script for automatic conversation analysis system
Demonstrates how the system automatically analyzes conversations in the database
"""

import os
import sys
import django
import json
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from chat.models import Conversation, Message


def create_demo_conversation(user):
    """Create a demo conversation with realistic customer service interaction"""
    conversation = Conversation.objects.create(
        user=user,
        title='Customer Support - Password Reset Issue'
    )
    
    # Create realistic conversation messages
    messages_data = [
        ('user', 'Hi, I need help with my account settings'),
        ('bot', 'Hello! I\'d be happy to help you with your account settings. What specific issue are you experiencing?'),
        ('user', 'I can\'t change my password. The form keeps giving me an error'),
        ('bot', 'I understand the password change form is giving you errors. Let me help you troubleshoot this. What error message are you seeing exactly?'),
        ('user', 'It says "Password must contain at least 8 characters" but mine has 12 characters'),
        ('bot', 'That\'s strange. Let me check a few things. Does your password contain a mix of uppercase, lowercase, numbers, and special characters?'),
        ('user', 'Yes, it has all of those. This is quite urgent as I need to access my account for a client presentation tomorrow.'),
        ('bot', 'I understand the urgency and I want to help resolve this quickly. I\'ve just sent a new password reset email to your address. If you don\'t receive it within 5 minutes, I can assist you with an alternative method.'),
        ('user', 'Great! I just received the email and was able to reset my password successfully. Thank you for your quick help!')
    ]
    
    # Create messages with realistic timestamps
    base_time = timezone.now() - timedelta(hours=2)  # 2 hours ago
    for i, (sender_type, content) in enumerate(messages_data):
        Message.objects.create(
            conversation=conversation,
            content=content,
            sender_type=sender_type,
            timestamp=base_time + timedelta(minutes=i * 2)  # 2 minutes between messages
        )
    
    return conversation


def create_frustrated_customer_conversation(user):
    """Create a conversation with a frustrated customer"""
    conversation = Conversation.objects.create(
        user=user,
        title='Billing Issue - Duplicate Charges'
    )
    
    messages_data = [
        ('user', 'This is the THIRD time I\'m contacting support about duplicate charges on my account!'),
        ('bot', 'I sincerely apologize for the inconvenience with the duplicate charges. I understand how frustrating this must be, especially having to contact us multiple times. Let me review your account immediately.'),
        ('user', 'I was charged twice for the same service and when I called, they said it would be resolved in 3-5 business days. That was 2 weeks ago!'),
        ('bot', 'I see the duplicate charge for $99 on your account from last month. You\'re absolutely right that this should have been resolved already. I\'m escalating this to our billing department with high priority right now.'),
        ('user', 'At this point I\'m seriously considering switching to a competitor. This is terrible customer service.'),
        ('bot', 'I completely understand your frustration and I don\'t want to lose you as a customer. I\'ve just processed an immediate refund of $99 to your account, and our billing manager will contact you personally within the next hour to ensure this never happens again.'),
        ('user', 'Okay, I appreciate that you\'re taking this seriously now. I\'ll wait for the manager\'s call.')
    ]
    
    base_time = timezone.now() - timedelta(hours=1)  # 1 hour ago
    for i, (sender_type, content) in enumerate(messages_data):
        Message.objects.create(
            conversation=conversation,
            content=content,
            sender_type=sender_type,
            timestamp=base_time + timedelta(minutes=i * 3)  # 3 minutes between messages
        )
    
    return conversation


def demo_automatic_analysis():
    """Demonstrate the automatic analysis system"""
    print("*** Demo: Automatic Conversation Analysis System ***")
    print("=" * 60)
    
    # Get or create demo user
    user, created = User.objects.get_or_create(
        username='demo_user_simple',
        defaults={
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'User'
        }
    )
    
    if created:
        print(f"[+] Created demo user: {user.username}")
    else:
        print(f"[+] Using existing demo user: {user.username}")
    
    # Create demo conversations
    print("\n[*] Creating demo conversations...")
    conv1 = create_demo_conversation(user)
    conv2 = create_frustrated_customer_conversation(user)
    
    conversations = [conv1, conv2]
    for i, conv in enumerate(conversations, 1):
        msg_count = conv.messages.count()
        print(f"   {i}. {conv.title} ({msg_count} messages)")
    
    # Wait for automatic analysis to trigger
    print("\n[*] Waiting for automatic analysis to trigger...")
    print("    (Note: Messages were created with timestamps that should trigger analysis)")
    
    # Check if analysis was triggered by the signals
    print("\n[*] Checking for analysis results...")
    
    for i, conversation in enumerate(conversations, 1):
        print(f"\n--- Conversation {i}: {conversation.title} ---")
        
        # Refresh from database to get any updates
        conversation.refresh_from_db()
        
        if conversation.langextract_analysis:
            print("[+] Analysis found in database!")
            
            # Display key insights from the analysis
            analysis = conversation.langextract_analysis
            
            if 'customer_insights' in analysis:
                insights = analysis['customer_insights']
                if 'sentiment_analysis' in insights:
                    sentiment = insights['sentiment_analysis']
                    print(f"   Sentiment: {sentiment.get('overall_sentiment', 'N/A')}")
                    print(f"   Satisfaction Score: {sentiment.get('satisfaction_score', 'N/A')}/10")
                
                if 'urgency_assessment' in insights:
                    urgency = insights['urgency_assessment']
                    print(f"   Urgency Level: {urgency.get('urgency_level', 'N/A')}")
                    print(f"   Escalation Recommended: {urgency.get('escalation_recommended', 'N/A')}")
            
            if 'conversation_patterns' in analysis:
                patterns = analysis['conversation_patterns']
                if 'conversation_flow' in patterns:
                    flow = patterns['conversation_flow']
                    print(f"   Conversation Type: {flow.get('conversation_type', 'N/A')}")
                    print(f"   Resolution Status: {flow.get('resolution_status', 'N/A')}")
            
            # Check if fallback analysis was used
            fallback_used = any(
                analysis.get(key, {}).get('fallback_analysis', False) 
                for key in ['conversation_patterns', 'customer_insights', 'unknown_patterns']
            )
            if fallback_used:
                print("   [!] Note: Fallback analysis used (LangExtract unavailable)")
            
            # Show metadata
            if 'metadata' in analysis:
                metadata = analysis['metadata']
                if 'automatic_analysis' in metadata:
                    print(f"   [*] Automatically analyzed: {metadata['automatic_analysis']}")
                if 'analysis_triggered_at' in metadata:
                    print(f"   [*] Analysis time: {metadata['analysis_triggered_at']}")
        else:
            print("[*] No analysis found yet")
            print("    This may be because:")
            print("    - Conversation is too recent (analysis waits for inactivity)")
            print("    - Not enough messages yet")
            print("    - Analysis is still processing in background")
    
    # Show overall database state
    print(f"\n[*] Database State Summary:")
    total_conversations = Conversation.objects.count()
    analyzed_conversations = Conversation.objects.exclude(langextract_analysis__exact={}).count()
    print(f"   Total Conversations: {total_conversations}")
    print(f"   Analyzed Conversations: {analyzed_conversations}")
    print(f"   Analysis Coverage: {(analyzed_conversations/total_conversations*100):.1f}%" if total_conversations > 0 else "   Analysis Coverage: 0%")
    
    # Show how to manually trigger analysis
    print(f"\n[*] Manual Analysis Testing:")
    print("   To manually trigger analysis, you can:")
    print("   1. Update message timestamps to be older:")
    
    # Make one conversation older to trigger analysis
    if conversations:
        old_conv = conversations[0]
        old_time = timezone.now() - timedelta(minutes=10)  # 10 minutes ago
        
        print(f"      Making conversation '{old_conv.title}' older...")
        for msg in old_conv.messages.all():
            msg.timestamp = old_time
            msg.save()
        
        print("   2. Check if analysis triggers automatically")
        print("   3. Or use Django management command to force analysis")
    
    # Show sample analysis structure if available
    analyzed_conv = Conversation.objects.exclude(langextract_analysis__exact={}).first()
    if analyzed_conv and analyzed_conv.langextract_analysis:
        print(f"\n[*] Sample Analysis Data Structure:")
        analysis_keys = list(analyzed_conv.langextract_analysis.keys())
        for key in analysis_keys[:5]:  # Show first 5 keys
            print(f"   - {key}")
        if len(analysis_keys) > 5:
            print(f"   ... and {len(analysis_keys) - 5} more fields")
    
    print(f"\n[+] Demo completed!")
    print(f"   Check Django admin to view detailed analysis results:")
    print(f"   Admin URL: http://localhost:8000/admin/")
    print(f"   Navigate to: Chat > Conversations")
    print(f"\n   The automatic analysis system will:")
    print(f"   - Monitor new messages as they're created")
    print(f"   - Automatically analyze conversations when they become inactive")
    print(f"   - Store structured insights in the database")
    print(f"   - Support both LangExtract and fallback analysis methods")


def cleanup_demo_data():
    """Clean up demo data"""
    print("\n[*] Cleaning up demo data...")
    
    # Delete demo conversations
    demo_conversations = Conversation.objects.filter(
        title__in=[
            'Customer Support - Password Reset Issue',
            'Billing Issue - Duplicate Charges'
        ]
    )
    count = demo_conversations.count()
    demo_conversations.delete()
    
    # Delete demo user if no other conversations
    try:
        demo_user = User.objects.get(username='demo_user_simple')
        if demo_user.conversations.count() == 0:
            demo_user.delete()
            print(f"   Deleted demo user and {count} conversations")
        else:
            print(f"   Deleted {count} demo conversations (user has other data)")
    except User.DoesNotExist:
        print(f"   Deleted {count} conversations")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Demo automatic conversation analysis')
    parser.add_argument('--cleanup', action='store_true', help='Clean up demo data instead of running demo')
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_demo_data()
    else:
        # Run the demo
        demo_automatic_analysis()