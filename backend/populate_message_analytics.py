"""
Script to populate message-level analytics data for existing conversations
This will analyze each user message for detailed insights
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from chat.models import Conversation, Message
from core.services.message_analysis_service import message_analysis_service


def populate_message_analytics():
    """Populate message-level analytics for all conversations"""
    print("=== Populating Message-Level Analytics ===")
    
    # Get all conversations with user messages
    conversations = Conversation.objects.filter(
        messages__sender_type='user'
    ).distinct()
    
    if not conversations.exists():
        print("No conversations with user messages found!")
        return
    
    print(f"Found {conversations.count()} conversations to analyze")
    
    total_analyzed = 0
    total_messages = 0
    error_count = 0
    
    for conversation in conversations:
        print(f"\nAnalyzing: {conversation.title}")
        
        try:
            # Analyze this conversation's messages
            analysis_result = message_analysis_service.analyze_conversation_messages(conversation)
            
            if 'error' not in analysis_result:
                msg_count = analysis_result['summary_stats']['total_messages']
                total_analyzed += 1
                total_messages += msg_count
                
                # Show key insights
                stats = analysis_result['summary_stats']
                print(f"  [+] Analyzed {msg_count} user messages")
                print(f"      Issues by type: {dict(list(stats['issues_by_type'].items())[:3])}")
                print(f"      Satisfaction: {stats['satisfaction_distribution']}")
                print(f"      Importance: {stats['importance_distribution']}")
                print(f"      Doc opportunities: {stats['doc_improvement_opportunities']}")
                print(f"      FAQ potential: {stats['high_faq_potential']}")
                
            else:
                print(f"  [-] Error: {analysis_result['error']}")
                error_count += 1
                
        except Exception as e:
            print(f"  [-] Exception: {e}")
            error_count += 1
    
    print(f"\n=== Results ===")
    print(f"Total conversations: {conversations.count()}")
    print(f"Successfully analyzed: {total_analyzed}")
    print(f"Total user messages analyzed: {total_messages}")
    print(f"Errors: {error_count}")
    
    # Show database stats
    analyzed_messages = Message.objects.filter(
        sender_type='user',
        message_analysis__isnull=False
    ).exclude(message_analysis__exact={}).count()
    
    total_user_messages = Message.objects.filter(sender_type='user').count()
    coverage = (analyzed_messages / total_user_messages * 100) if total_user_messages > 0 else 0
    
    print(f"\n=== Database State ===")
    print(f"Total user messages: {total_user_messages}")
    print(f"Messages with analysis: {analyzed_messages}")
    print(f"Analysis coverage: {coverage:.1f}%")
    
    print(f"\n[+] Message analytics populated!")
    print(f"   API endpoints available:")
    print(f"   - GET /api/chat/analytics/messages/ - Get detailed analytics")
    print(f"   - GET /api/chat/analytics/summary/ - Get summary statistics")
    print(f"   - POST /api/chat/analytics/conversation/ - Analyze specific conversation")


def test_message_analytics_api():
    """Test the message analytics API endpoint"""
    print("\n=== Testing Message Analytics API ===")
    
    try:
        from chat.message_analytics_api import message_analytics
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        from rest_framework.test import force_authenticate
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/api/chat/analytics/messages/?days=7')
        
        # Get admin user for authentication
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        
        force_authenticate(request, user=admin_user)
        
        # Test the API
        response = message_analytics(request)
        print(f"API Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"Summary Statistics:")
            print(f"  Conversations analyzed: {data['summary_statistics']['total_conversations']}")
            print(f"  User messages analyzed: {data['summary_statistics']['total_user_messages']}")
            print(f"  Top issues: {data['summary_statistics']['issues_by_category']}")
            print(f"  Satisfaction summary: {data['summary_statistics']['satisfaction_summary']}")
            print(f"  Insights: {data['insights']}")
            print(f"  Recommendations: {data['recommendations']}")
        else:
            print(f"API Error: {response.data}")
            
    except Exception as e:
        print(f"API test failed: {e}")


def show_sample_message_analysis():
    """Show sample analysis for a user message"""
    print("\n=== Sample Message Analysis ===")
    
    # Get a sample user message with analysis
    sample_message = Message.objects.filter(
        sender_type='user',
        message_analysis__isnull=False
    ).exclude(message_analysis__exact={}).first()
    
    if sample_message:
        print(f"Message: {sample_message.content}")
        print(f"Analysis: {sample_message.message_analysis}")
        
        analysis = sample_message.message_analysis
        
        print(f"\nDetailed Analysis:")
        print(f"  Issues Raised: {analysis.get('issues_raised', [])}")
        print(f"  Satisfaction: {analysis.get('satisfaction_level', {})}")
        print(f"  Importance: {analysis.get('importance_level', {})}")
        print(f"  Doc Potential: {analysis.get('doc_improvement_potential', {})}")
        print(f"  FAQ Potential: {analysis.get('faq_potential', {})}")
    else:
        print("No analyzed messages found. Run populate_message_analytics() first.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Populate message-level analytics')
    parser.add_argument('--test-api', action='store_true', help='Test the analytics API')
    parser.add_argument('--sample', action='store_true', help='Show sample analysis')
    args = parser.parse_args()
    
    if args.test_api:
        test_message_analytics_api()
    elif args.sample:
        show_sample_message_analysis()
    else:
        populate_message_analytics()