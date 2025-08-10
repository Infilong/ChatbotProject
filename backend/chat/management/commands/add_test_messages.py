"""
Django management command to add test messages to conversations for LangExtract testing
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chat.models import Conversation, Message


class Command(BaseCommand):
    help = 'Add test messages to existing conversations for LangExtract analysis testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--conversation-id',
            type=int,
            help='Specific conversation ID to add messages to',
        )
        parser.add_argument(
            '--create-sample',
            action='store_true',
            help='Create a new conversation with sample messages',
        )
    
    def handle(self, *args, **options):
        if options['create_sample']:
            self.create_sample_conversation()
        elif options['conversation_id']:
            self.add_messages_to_conversation(options['conversation_id'])
        else:
            self.add_messages_to_all_empty_conversations()
    
    def create_sample_conversation(self):
        """Create a new conversation with comprehensive test messages"""
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
        )
        
        # Create conversation
        conversation = Conversation.objects.create(
            user=admin_user,
            title="Sample LangExtract Test Conversation"
        )
        
        # Add comprehensive test messages for LangExtract analysis
        test_messages = [
            # User starts with a problem
            {
                'content': "Hi, I'm having trouble with my account login. It keeps saying my password is incorrect, but I know it's right. This is really frustrating!",
                'sender_type': 'user'
            },
            # Bot responds helpfully
            {
                'content': "I understand your frustration, and I'm here to help you resolve this login issue. Let me guide you through some troubleshooting steps. First, could you try resetting your password?",
                'sender_type': 'bot'
            },
            # User provides more context
            {
                'content': "I tried that already, but the reset email never arrived. I checked my spam folder too. This is urgent because I need to access my account for work tomorrow.",
                'sender_type': 'user'
            },
            # Bot offers escalation
            {
                'content': "I see this is urgent for your work needs. Since the password reset isn't working, I'll escalate this to our technical team immediately. They can unlock your account manually. You should receive a call within the next hour.",
                'sender_type': 'bot'
            },
            # User expresses satisfaction
            {
                'content': "Thank you so much! That's exactly what I needed. The quick escalation really helps. I appreciate your excellent customer service.",
                'sender_type': 'user'
            },
            # Bot concludes positively
            {
                'content': "You're very welcome! I'm glad I could help resolve this quickly. Our technical team will take great care of you. Is there anything else I can assist you with today?",
                'sender_type': 'bot'
            },
            # User confirms resolution
            {
                'content': "No, that covers everything. Thanks again for the great help!",
                'sender_type': 'user'
            }
        ]
        
        for i, msg_data in enumerate(test_messages):
            Message.objects.create(
                conversation=conversation,
                content=msg_data['content'],
                sender_type=msg_data['sender_type']
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Created sample conversation ID {conversation.id} with {len(test_messages)} messages'
            )
        )
        return conversation.id
    
    def add_messages_to_conversation(self, conversation_id):
        """Add test messages to a specific conversation"""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            
            # Check if conversation already has messages
            existing_messages = conversation.messages.count()
            if existing_messages > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️ Conversation {conversation_id} already has {existing_messages} messages'
                    )
                )
                return
            
            # Add simple test messages
            test_messages = [
                {
                    'content': "Hello, I need help with my account please.",
                    'sender_type': 'user'
                },
                {
                    'content': "Of course! I'd be happy to help you with your account. What specific issue are you experiencing?",
                    'sender_type': 'bot'
                },
                {
                    'content': "I can't log in and I'm getting error messages. This is quite frustrating.",
                    'sender_type': 'user'
                },
                {
                    'content': "I understand your frustration. Let me help you resolve this login issue step by step.",
                    'sender_type': 'bot'
                },
                {
                    'content': "Thank you for your help! That solved my problem perfectly.",
                    'sender_type': 'user'
                }
            ]
            
            for msg_data in test_messages:
                Message.objects.create(
                    conversation=conversation,
                    content=msg_data['content'],
                    sender_type=msg_data['sender_type']
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Added {len(test_messages)} test messages to conversation {conversation_id}'
                )
            )
            
        except Conversation.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ Conversation {conversation_id} not found')
            )
    
    def add_messages_to_all_empty_conversations(self):
        """Add test messages to all conversations without messages"""
        empty_conversations = Conversation.objects.filter(messages__isnull=True).distinct()
        
        if not empty_conversations.exists():
            self.stdout.write(
                self.style.WARNING('⚠️ No empty conversations found')
            )
            return
        
        for conversation in empty_conversations:
            self.add_messages_to_conversation(conversation.id)
            
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Processed {empty_conversations.count()} empty conversations'
            )
        )