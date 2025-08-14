"""
Management command to analyze conversations with LangExtract
"""

import asyncio
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Conversation
from core.services.automatic_analysis_service import automatic_analysis_service


class Command(BaseCommand):
    help = 'Analyze conversations using LangExtract automatic analysis service'

    def add_arguments(self, parser):
        parser.add_argument(
            '--conversation-id',
            type=str,
            help='Analyze specific conversation by UUID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force analysis even if already analyzed',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Analyze all pending conversations',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be analyzed without actually running analysis',
        )

    def handle(self, *args, **options):
        """Main command handler"""
        try:
            if options['conversation_id']:
                self._analyze_single_conversation(options)
            elif options['all']:
                self._analyze_all_conversations(options)
            else:
                self._show_analysis_status()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running analysis command: {e}')
            )

    def _analyze_single_conversation(self, options):
        """Analyze a single conversation"""
        conversation_id = options['conversation_id']
        force = options['force']
        dry_run = options['dry_run']
        
        try:
            conversation = Conversation.objects.get(uuid=conversation_id)
            
            if dry_run:
                self.stdout.write(f"Would analyze conversation: {conversation_id}")
                self.stdout.write(f"  Messages: {conversation.total_messages}")
                self.stdout.write(f"  Has analysis: {bool(conversation.langextract_analysis)}")
                return
            
            if conversation.langextract_analysis and not force:
                self.stdout.write(
                    self.style.WARNING(f'Conversation {conversation_id} already analyzed. Use --force to re-analyze.')
                )
                return
            
            self.stdout.write(f'Analyzing conversation {conversation_id}...')
            
            # Run analysis
            if force:
                result = asyncio.run(automatic_analysis_service.force_analysis(conversation_id))
            else:
                result = asyncio.run(automatic_analysis_service.trigger_analysis_if_needed(conversation))
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully analyzed conversation {conversation_id}')
                )
                
                # Show summary
                if 'customer_insights' in result:
                    insights = result['customer_insights']
                    if 'sentiment_analysis' in insights:
                        sentiment = insights['sentiment_analysis'].get('overall_sentiment', 'unknown')
                        satisfaction = insights['sentiment_analysis'].get('satisfaction_score', 'unknown')
                        self.stdout.write(f"  Sentiment: {sentiment}")
                        self.stdout.write(f"  Satisfaction: {satisfaction}")
                
            else:
                self.stdout.write(
                    self.style.WARNING(f'No analysis performed for conversation {conversation_id}')
                )
                
        except Conversation.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Conversation {conversation_id} not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error analyzing conversation {conversation_id}: {e}')
            )

    def _analyze_all_conversations(self, options):
        """Analyze all pending conversations"""
        dry_run = options['dry_run']
        force = options['force']
        
        try:
            if force:
                # Get all conversations
                conversations = Conversation.objects.all()
                count = conversations.count()
            else:
                # Get only unanalyzed conversations
                conversations = Conversation.objects.filter(langextract_analysis__isnull=True)
                count = conversations.count()
            
            if dry_run:
                self.stdout.write(f"Would analyze {count} conversations")
                for conv in conversations[:10]:  # Show first 10
                    self.stdout.write(f"  {conv.uuid}: {conv.total_messages} messages")
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more")
                return
            
            if count == 0:
                self.stdout.write(self.style.SUCCESS('No conversations need analysis'))
                return
            
            self.stdout.write(f'Analyzing {count} conversations...')
            
            # Run batch analysis
            result = asyncio.run(automatic_analysis_service.analyze_pending_conversations())
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Batch analysis completed: {result['analyzed_count']} analyzed, "
                    f"{result['skipped_count']} skipped, {result['error_count']} errors"
                )
            )
            
            # Show errors if any
            if result['error_count'] > 0:
                self.stdout.write(self.style.WARNING('Errors occurred during analysis:'))
                for analysis_result in result['analysis_results']:
                    if analysis_result['status'] == 'error':
                        self.stdout.write(f"  {analysis_result['conversation_id']}: {analysis_result['error']}")
                        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error in batch analysis: {e}')
            )

    def _show_analysis_status(self):
        """Show current analysis status"""
        try:
            total_conversations = Conversation.objects.count()
            analyzed_conversations = Conversation.objects.filter(
                langextract_analysis__isnull=False
            ).count()
            pending_conversations = total_conversations - analyzed_conversations
            
            self.stdout.write("LangExtract Analysis Status:")
            self.stdout.write(f"  Total conversations: {total_conversations}")
            self.stdout.write(f"  Analyzed: {analyzed_conversations}")
            self.stdout.write(f"  Pending: {pending_conversations}")
            
            if pending_conversations > 0:
                self.stdout.write(
                    f"\nRun 'python manage.py analyze_conversations --all' to analyze pending conversations"
                )
            
            # Show recent activity
            recent_analyzed = Conversation.objects.filter(
                langextract_analysis__isnull=False,
                updated_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()
            
            if recent_analyzed > 0:
                self.stdout.write(f"  Analyzed in last 24h: {recent_analyzed}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error showing status: {e}')
            )