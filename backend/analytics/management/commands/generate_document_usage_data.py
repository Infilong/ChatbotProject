"""
Management command to generate sample document usage data for testing analytics
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import models
from chat.models import Conversation, Message
from documents.models import Document
from analytics.models import DocumentUsage


class Command(BaseCommand):
    help = 'Generate sample document usage data for analytics testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', 
            type=int, 
            default=100,
            help='Number of document usage records to create'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(f'Generating {count} document usage records...')
        
        # Get or create test data
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com', 'first_name': 'Test', 'last_name': 'User'}
        )
        
        # Create test documents if they don't exist
        documents = []
        doc_names = [
            'Company Privacy Policy',
            'Data Processing Guidelines', 
            'GDPR Compliance Manual',
            'Customer Support FAQ',
            'Product Technical Specifications',
            'Service Level Agreement',
            'Security Best Practices',
            'API Documentation'
        ]
        
        for name in doc_names:
            doc, created = Document.objects.get_or_create(
                name=name,
                defaults={
                    'category': random.choice(['compliance', 'technical', 'support', 'legal']),
                    'file_type': 'pdf',
                    'extracted_text': f'Sample content for {name}. This document contains important information...',
                    'ai_summary': f'This document covers {name.lower()} related topics and procedures.',
                    'ai_keywords_json': ['policy', 'procedures', 'guidelines', 'compliance'],
                    'is_active': True
                }
            )
            documents.append(doc)
            if created:
                self.stdout.write(f'Created document: {name}')
        
        # Create test conversations and messages
        conversations = []
        for i in range(10):
            conv, created = Conversation.objects.get_or_create(
                user=user,
                title=f'Test Conversation {i+1}',
                defaults={'is_active': True}
            )
            conversations.append(conv)
            
            if created:
                # Add some sample messages to each conversation
                for j in range(random.randint(2, 8)):
                    Message.objects.get_or_create(
                        conversation=conv,
                        content=f'Test message {j+1} in conversation {i+1}',
                        sender_type=random.choice(['user', 'bot']),
                        defaults={'timestamp': timezone.now() - timedelta(hours=random.randint(1, 72))}
                    )
        
        # Generate document usage records
        user_intents = ['compliance', 'services', 'pricing', 'support', 'technical', 'general_inquiry']
        search_queries = [
            'What is our privacy policy?',
            'How do we handle customer data?',
            'GDPR compliance requirements',
            'Data processing guidelines',
            'Security best practices',
            'How to contact support?',
            'Service level agreements',
            'API documentation and specs'
        ]
        
        keywords_pool = [
            ['privacy', 'policy', 'data'],
            ['gdpr', 'compliance', 'regulation'],
            ['security', 'protection', 'best practices'],
            ['support', 'help', 'assistance'],
            ['api', 'documentation', 'technical'],
            ['service', 'level', 'agreement'],
            ['processing', 'guidelines', 'procedures'],
            ['customer', 'data', 'handling']
        ]
        
        created_count = 0
        
        for i in range(count):
            # Select random document and conversation
            document = random.choice(documents)
            conversation = random.choice(conversations)
            messages = list(conversation.messages.all())
            
            if not messages:
                continue
                
            message = random.choice(messages)
            
            # Generate realistic data
            search_query = random.choice(search_queries)
            relevance_score = random.uniform(0.1, 1.0)
            user_intent = random.choice(user_intents)
            keywords_matched = random.choice(keywords_pool)[:random.randint(1, 4)]
            
            # Generate excerpt
            excerpt_used = f'Sample excerpt from {document.name}. This section explains {user_intent} related procedures and guidelines.'
            excerpt_start_pos = random.randint(100, 5000)
            excerpt_length = len(excerpt_used)
            
            # Create usage record with timestamp spread over last 30 days
            referenced_at = timezone.now() - timedelta(days=random.randint(0, 30))
            
            usage, created = DocumentUsage.objects.get_or_create(
                document=document,
                conversation=conversation,
                message=message,
                search_query=search_query,
                defaults={
                    'referenced_at': referenced_at,
                    'relevance_score': relevance_score,
                    'usage_type': random.choice(['excerpt', 'full_context', 'summary']),
                    'excerpt_used': excerpt_used,
                    'excerpt_start_position': excerpt_start_pos,
                    'excerpt_length': excerpt_length,
                    'keywords_matched': keywords_matched,
                    'context_category': document.category,
                    'user_intent': user_intent,
                    'user_feedback': random.choice(['positive', 'negative', None, None]),  # Mostly None
                    'effectiveness_score': random.uniform(40.0, 95.0),
                    'response_helpful': random.choice([True, False, None]),
                    'llm_model_used': random.choice(['gemini-2.5-flash', 'gpt-4', 'claude-3']),
                    'processing_time': random.uniform(0.5, 3.0)
                }
            )
            
            if created:
                # Update document statistics
                document.reference_count += 1
                document.last_referenced = referenced_at
                document.effectiveness_score = min(document.effectiveness_score + 0.1, 10.0)
                document.save(update_fields=['reference_count', 'last_referenced', 'effectiveness_score'])
                
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} document usage records')
        )
        self.stdout.write(f'Total documents: {len(documents)}')
        self.stdout.write(f'Total conversations: {len(conversations)}')
        
        # Show some analytics preview
        self.stdout.write('\n--- Analytics Preview ---')
        self.stdout.write(f'Total usage records: {DocumentUsage.objects.count()}')
        self.stdout.write(f'Unique documents used: {DocumentUsage.objects.values("document").distinct().count()}')
        self.stdout.write(f'Average relevance score: {DocumentUsage.objects.aggregate(avg_relevance=models.Avg("relevance_score"))["avg_relevance"]:.2f}')
        
        # Top documents
        from django.db.models import Count
        top_docs = DocumentUsage.objects.values('document__name').annotate(
            usage_count=Count('id')
        ).order_by('-usage_count')[:5]
        
        self.stdout.write('\nTop 5 most used documents:')
        for doc in top_docs:
            self.stdout.write(f'- {doc["document__name"]}: {doc["usage_count"]} uses')
        
        self.stdout.write(f'\nYou can now view analytics at: http://127.0.0.1:8000/admin/analytics/documentusage/analytics/')