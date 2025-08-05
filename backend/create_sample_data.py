#!/usr/bin/env python
import os
import django
from django.conf import settings
from datetime import datetime, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_backend.settings')
django.setup()

from django.contrib.auth.models import User
from chat.models import Conversation, Message, UserSession
from analytics.models import ConversationAnalysis, UserFeedback, AnalyticsSummary
from documents.models import DocumentCategory, CompanyDocument, KnowledgeGap, DocumentFeedback
from authentication.models import UserProfile, UserPreferences

def create_sample_data():
    print("Creating sample data for admin testing...")
    
    # Create test users
    users = []
    for i in range(3):
        username = f'customer{i+1}'
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                email=f'{username}@example.com',
                password='testpass123',
                first_name=f'Customer',
                last_name=f'{i+1}'
            )
            users.append(user)
            print(f"Created user: {username}")
        else:
            users.append(User.objects.get(username=username))
    
    # Update user profiles with sample data
    for i, user in enumerate(users):
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.role = 'customer'
            profile.company = f'Company {i+1}'
            profile.job_title = f'Manager'
            profile.total_conversations = i + 2
            profile.total_messages_sent = (i + 1) * 10
            profile.average_satisfaction = 7.5 + i * 0.5
            profile.last_active = timezone.now() - timedelta(hours=i)
            profile.save()
    
    # Create document categories
    categories = [
        {'name': 'FAQ', 'description': 'Frequently Asked Questions', 'color': '#4CAF50'},
        {'name': 'Policies', 'description': 'Company Policies', 'color': '#2196F3'},
        {'name': 'Tutorials', 'description': 'How-to Guides', 'color': '#FF9800'}
    ]
    
    for cat_data in categories:
        category, created = DocumentCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        if created:
            print(f"Created category: {category.name}")
    
    # Create conversations and messages
    conversations = []
    for i, user in enumerate(users):
        conv = Conversation.objects.create(
            user=user,
            title=f"Support Request #{i+1}",
            total_messages=4,
            satisfaction_score=7.0 + i
        )
        conversations.append(conv)
        
        # Create messages for each conversation
        messages_data = [
            ("user", f"Hi, I need help with feature X. It's not working properly."),
            ("bot", f"Hello! I'd be happy to help you with feature X. Can you describe what specific issue you're experiencing?"),
            ("user", f"When I try to use it, I get an error message saying 'Access denied'."),
            ("bot", f"I see the issue. This is usually related to permissions. Let me help you resolve this.")
        ]
        
        for j, (sender, content) in enumerate(messages_data):
            message = Message.objects.create(
                conversation=conv,
                content=content,
                sender_type=sender,
                response_time=1.2 if sender == 'bot' else None,
                llm_model_used='gpt-4' if sender == 'bot' else None
            )
            
            # Add feedback to bot messages
            if sender == 'bot' and j > 1:
                message.feedback = 'positive' if i % 2 == 0 else 'negative'
                message.save()
        
        print(f"Created conversation for {user.username}")
    
    # Create conversation analyses
    for i, conv in enumerate(conversations):
        analysis = ConversationAnalysis.objects.create(
            conversation=conv,
            sentiment='positive' if i % 2 == 0 else 'negative',
            satisfaction_level=8 - i,
            issues_raised=['permission_error', 'feature_malfunction'],
            urgency_indicators=['not working', 'error message'],
            resolution_status='resolved' if i == 0 else 'pending',
            customer_intent='support',
            key_insights=['User needs permission fix', 'Common error pattern'],
            source_spans=[
                {'text': 'not working properly', 'start': 45, 'end': 65, 'type': 'issue'},
                {'text': 'Access denied', 'start': 120, 'end': 133, 'type': 'error'}
            ],
            confidence_score=0.85 + i * 0.05,
            langextract_model_used='gemini-pro',
            processing_time=2.3
        )
        print(f"Created analysis for conversation {conv.id}")
    
    # Create analytics summary for today
    today = timezone.now().date()
    summary, created = AnalyticsSummary.objects.get_or_create(
        date=today,
        defaults={
            'total_conversations': len(conversations),
            'total_messages': len(conversations) * 4,
            'unique_users': len(users),
            'average_satisfaction': 7.5,
            'positive_conversations': 2,
            'negative_conversations': 1,
            'neutral_conversations': 0,
            'total_issues_raised': 3,
            'resolved_issues': 1,
            'escalated_issues': 0,
            'average_response_time': 1.4,
            'bot_vs_human_ratio': 0.8
        }
    )
    if created:
        print("Created analytics summary for today")
    
    # Create knowledge gaps
    gaps_data = [
        {'query': 'How to reset password when email is not accessible?', 'frequency': 5, 'priority': 'high'},
        {'query': 'Integration with third-party tools documentation', 'frequency': 3, 'priority': 'medium'},
        {'query': 'Billing and payment troubleshooting guide', 'frequency': 7, 'priority': 'critical'}
    ]
    
    for gap_data in gaps_data:
        gap, created = KnowledgeGap.objects.get_or_create(
            query=gap_data['query'],
            defaults={
                'frequency': gap_data['frequency'],
                'priority': gap_data['priority'],
                'status': 'identified'
            }
        )
        if created:
            print(f"Created knowledge gap: {gap.query[:50]}...")
    
    print("\n✅ Sample data created successfully!")
    print("You can now test the admin interface at: http://localhost:8000/admin/")
    print("Login: admin / admin123")
    
    return True

if __name__ == "__main__":
    create_sample_data()