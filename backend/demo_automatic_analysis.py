"""
Demo script for automatic conversation analysis system
Demonstrates how the system automatically analyzes conversations in the database
"""

import os
import sys
import django
import asyncio
import json
from datetime import timedelta
from django.utils import timezone
from asgiref.sync import sync_to_async

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from chat.models import Conversation, Message
from core.services.automatic_analysis_service import automatic_analysis_service


def create_demo_conversation(user):
    """Create a demo conversation with realistic customer service interaction"""
    conversation = Conversation.objects.create(
        user=user,
        title='Customer Support - Password Reset Issue'
    )
    
    # Create realistic conversation messages
    messages_data = [
        ('user', 'Hi, I\'m having trouble resetting my password. The reset email never arrives.'),
        ('bot', 'I\'m sorry to hear you\'re having trouble with the password reset. Let me help you with that. Can you confirm the email address associated with your account?'),
        ('user', 'Yes, it\'s john.doe@company.com. I checked my spam folder but nothing is there.'),
        ('bot', 'Thank you for confirming. I can see your account in our system. Let me check if there are any delivery issues with that email domain. Please give me a moment.'),
        ('user', 'Okay, thank you. This is quite urgent as I need to access my account for a client presentation tomorrow.'),
        ('bot', 'I understand the urgency and I want to help resolve this quickly. I\'ve just sent a new password reset email to your address. If you don\'t receive it within 5 minutes, I can assist you with an alternative method.'),
        ('user', 'Great! I just received the email and was able to reset my password successfully. Thank you for your quick help!'),
        ('bot', 'Wonderful! I\'m glad we could resolve this quickly for you. Is there anything else I can help you with today?'),
        ('user', 'No, that\'s everything. Thanks again for the excellent support!')
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
        ('user', 'I was charged $99 twice last month and when I called, they said it would be resolved in 3-5 business days. That was 2 weeks ago!'),
        ('bot', 'I see the duplicate charge for $99 on your account from last month. You\'re absolutely right that this should have been resolved already. I\'m escalating this to our billing department with high priority right now.'),
        ('user', 'At this point I\'m seriously considering switching to a competitor. This is terrible customer service.'),
        ('bot', 'I completely understand your frustration and I don\'t want to lose you as a customer. I\'ve just processed an immediate refund of $99 to your account, and our billing manager will contact you personally within the next hour to ensure this never happens again.'),
        ('user', 'Okay, I appreciate that you\'re taking this seriously now. I\'ll wait for the manager\'s call.'),
        ('bot', 'Thank you for giving us another chance to make this right. You should receive an email confirmation of the refund within 10 minutes, and our billing manager Sarah will call you directly.')
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


def create_technical_conversation(user):
    """Create a technical conversation"""
    conversation = Conversation.objects.create(
        user=user,
        title='Technical Support - API Integration'
    )
    
    messages_data = [
        ('user', 'I\'m having issues integrating your REST API with our system. Getting 403 errors on all endpoints.'),
        ('bot', 'I\'d be happy to help with the API integration issues. 403 errors typically indicate authentication problems. Are you including your API key in the Authorization header?'),
        ('user', 'Yes, I\'m using Bearer token authentication with the API key from my dashboard.'),
        ('bot', 'Let me check a few things. Can you confirm you\'re using the production API endpoint (api.example.com) and not the sandbox endpoint?'),
        ('user', 'Oh wait, I think I might be using the wrong endpoint. Let me check... yes, I was using the sandbox URL. Let me try the production endpoint.'),
        ('bot', 'That\'s likely the issue! The sandbox and production environments have separate authentication systems. Try the production endpoint and let me know if you still encounter issues.'),
        ('user', 'Perfect! That fixed it. All my API calls are working now. Thank you for catching that.'),
        ('bot', 'Excellent! I\'m glad we could resolve that quickly. For future reference, make sure to use the production endpoint for live integrations. Is there anything else I can help you with?')
    ]
    
    base_time = timezone.now() - timedelta(minutes=30)  # 30 minutes ago
    for i, (sender_type, content) in enumerate(messages_data):
        Message.objects.create(
            conversation=conversation,
            content=content,
            sender_type=sender_type,
            timestamp=base_time + timedelta(minutes=i * 2)
        )
    
    return conversation


async def demo_automatic_analysis():
    """Demonstrate the automatic analysis system"""
    print("*** Demo: Automatic Conversation Analysis System ***")
    print("=" * 60)
    
    # Get or create demo user
    @sync_to_async
    def get_or_create_user():
        return User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Demo',
                'last_name': 'User'
            }
        )
    
    user, created = await get_or_create_user()
    
    if created:
        print(f"[+] Created demo user: {user.username}")
    else:
        print(f"[+] Using existing demo user: {user.username}")
    
    # Create demo conversations
    print("\n[*] Creating demo conversations...")
    
    @sync_to_async
    def create_conversations():
        conv1 = create_demo_conversation(user)
        conv2 = create_frustrated_customer_conversation(user)
        conv3 = create_technical_conversation(user)
        return [conv1, conv2, conv3]
    
    conversations = await create_conversations()
    
    for i, conv in enumerate(conversations, 1):
        print(f"   {i}. {conv.title} ({conv.messages.count()} messages)")
    
    # Analyze each conversation
    print("\n[*] Running automatic analysis on conversations...")
    
    for i, conversation in enumerate(conversations, 1):
        print(f"\n--- Analyzing Conversation {i}: {conversation.title} ---")
        
        try:
            # Trigger analysis
            result = await automatic_analysis_service.trigger_analysis_if_needed(conversation)
            
            if result:
                print("[+] Analysis completed successfully!")
                
                # Display key insights
                if 'customer_insights' in result:
                    insights = result['customer_insights']
                    if 'sentiment_analysis' in insights:
                        sentiment = insights['sentiment_analysis']
                        print(f"   Sentiment: {sentiment.get('overall_sentiment', 'N/A')}")
                        print(f"   Satisfaction Score: {sentiment.get('satisfaction_score', 'N/A')}/10")
                    
                    if 'urgency_assessment' in insights:
                        urgency = insights['urgency_assessment']
                        print(f"   Urgency Level: {urgency.get('urgency_level', 'N/A')}")
                        print(f"   Escalation Recommended: {urgency.get('escalation_recommended', 'N/A')}")
                
                if 'conversation_patterns' in result:
                    patterns = result['conversation_patterns']
                    if 'conversation_flow' in patterns:
                        flow = patterns['conversation_flow']
                        print(f"   Conversation Type: {flow.get('conversation_type', 'N/A')}")
                        print(f"   Resolution Status: {flow.get('resolution_status', 'N/A')}")
                
                # Check if fallback analysis was used
                fallback_used = any(
                    result.get(key, {}).get('fallback_analysis', False) 
                    for key in ['conversation_patterns', 'customer_insights', 'unknown_patterns']
                )
                if fallback_used:
                    print("   [!] Note: Fallback analysis used (LangExtract unavailable)")
                
            else:
                print("[*] Analysis skipped (conversation doesn't meet criteria)")
                
        except Exception as e:
            print(f"[-] Analysis failed: {e}")
    
    # Demonstrate batch analysis
    print(f"\n[*] Running batch analysis on all pending conversations...")
    
    try:
        batch_results = await automatic_analysis_service.analyze_pending_conversations()
        
        print("[*] Batch Analysis Results:")
        print(f"   Total Conversations: {batch_results['total_conversations']}")
        print(f"   Successfully Analyzed: {batch_results['analyzed_count']}")
        print(f"   Skipped: {batch_results['skipped_count']}")
        print(f"   Errors: {batch_results['error_count']}")
        
        if batch_results['analysis_results']:
            print("\n[*] Individual Results:")
            for result in batch_results['analysis_results']:
                status = "[+]" if result['status'] == 'success' else "[-]"
                print(f"   {status} {result['conversation_id'][:8]}... - {result['status']}")
                
    except Exception as e:
        print(f"[-] Batch analysis failed: {e}")
    
    # Show database state
    print(f"\n[*] Database State Summary:")
    
    @sync_to_async
    def get_db_stats():
        total_conversations = Conversation.objects.count()
        analyzed_conversations = Conversation.objects.exclude(langextract_analysis__exact={}).count()
        analyzed_conv = Conversation.objects.exclude(langextract_analysis__exact={}).first()
        return total_conversations, analyzed_conversations, analyzed_conv
    
    total_conversations, analyzed_conversations, analyzed_conv = await get_db_stats()
    
    print(f"   Total Conversations: {total_conversations}")
    print(f"   Analyzed Conversations: {analyzed_conversations}")
    print(f"   Analysis Coverage: {(analyzed_conversations/total_conversations*100):.1f}%" if total_conversations > 0 else "   Analysis Coverage: 0%")
    
    # Show sample analysis data
    if analyzed_conv and analyzed_conv.langextract_analysis:
        print(f"\n[*] Sample Analysis Data Structure:")
        analysis_keys = list(analyzed_conv.langextract_analysis.keys())
        for key in analysis_keys[:5]:  # Show first 5 keys
            print(f"   - {key}")
        if len(analysis_keys) > 5:
            print(f"   ... and {len(analysis_keys) - 5} more fields")
    
    print(f"\n[+] Demo completed! Check Django admin to view detailed analysis results.")
    print(f"   Admin URL: http://localhost:8000/admin/")
    print(f"   Navigate to: Chat > Conversations to see analyzed conversations")


def cleanup_demo_data():
    """Clean up demo data"""
    print("\n[*] Cleaning up demo data...")
    
    # Delete demo conversations
    demo_conversations = Conversation.objects.filter(
        title__in=[
            'Customer Support - Password Reset Issue',
            'Billing Issue - Duplicate Charges', 
            'Technical Support - API Integration'
        ]
    )
    count = demo_conversations.count()
    demo_conversations.delete()
    
    # Delete demo user if no other conversations
    try:
        demo_user = User.objects.get(username='demo_user')
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
        asyncio.run(demo_automatic_analysis())