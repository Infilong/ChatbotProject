"""
Django management command to fix missing analysis source labels
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from chat.models import Message, Conversation
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix missing analysis source labels in existing message and conversation analyses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Update all analyses, even those that already have source labels',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.SUCCESS('=== FIXING ANALYSIS SOURCE LABELS ==='))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Fix message-level analysis
        self.fix_message_analysis(dry_run, force)
        
        # Fix conversation-level analysis
        self.fix_conversation_analysis(dry_run, force)
        
        self.stdout.write(self.style.SUCCESS('Analysis source labeling complete!'))

    def fix_message_analysis(self, dry_run, force):
        """Fix message-level analysis source labels"""
        self.stdout.write('\n=== FIXING MESSAGE ANALYSIS SOURCES ===')
        
        # Get messages with analysis but missing source labels
        if force:
            messages_to_fix = Message.objects.filter(
                sender_type='user'
            ).exclude(message_analysis={})
        else:
            messages_to_fix = Message.objects.filter(
                sender_type='user'
            ).exclude(message_analysis={}).exclude(
                message_analysis__has_key='analysis_source'
            )
        
        total_count = messages_to_fix.count()
        self.stdout.write(f'Found {total_count} messages needing source labels')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('No messages need fixing'))
            return
        
        updated_count = 0
        
        for message in messages_to_fix:
            analysis = message.message_analysis
            
            # Determine the original analysis source based on structure
            source_label = self._determine_message_analysis_source(analysis)
            
            if dry_run:
                self.stdout.write(f'Would update message {str(message.uuid)[:8]}: {source_label}')
            else:
                # Update the analysis with source labeling
                analysis.update({
                    'analysis_source': source_label,
                    'analysis_method': 'keyword_based',
                    'analysis_version': 'local_v1.0_legacy',
                    'retroactive_labeling': True
                })
                
                with transaction.atomic():
                    message.message_analysis = analysis
                    message.save(update_fields=['message_analysis'])
                
                updated_count += 1
                
                if updated_count % 10 == 0:
                    self.stdout.write(f'Updated {updated_count}/{total_count} messages...')
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} message analyses'))

    def fix_conversation_analysis(self, dry_run, force):
        """Fix conversation-level analysis source labels"""
        self.stdout.write('\n=== FIXING CONVERSATION ANALYSIS SOURCES ===')
        
        # Get conversations with analysis but missing source labels
        if force:
            conversations_to_fix = Conversation.objects.exclude(langextract_analysis={})
        else:
            conversations_to_fix = Conversation.objects.exclude(langextract_analysis={}).exclude(
                langextract_analysis__has_key='analysis_source'
            )
        
        total_count = conversations_to_fix.count()
        self.stdout.write(f'Found {total_count} conversations needing source labels')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('No conversations need fixing'))
            return
        
        updated_count = 0
        
        for conversation in conversations_to_fix:
            analysis = conversation.langextract_analysis
            
            # Determine the original analysis source
            source_label = self._determine_conversation_analysis_source(analysis)
            
            if dry_run:
                self.stdout.write(f'Would update conversation {str(conversation.uuid)[:8]}: {source_label}')
            else:
                # Update the analysis with source labeling
                analysis.update({
                    'analysis_source': source_label,
                    'analysis_method': 'local_conversation_aggregation',
                    'analysis_version': 'simple_v1.0_legacy',
                    'retroactive_labeling': True,
                    'api_available': False
                })
                
                with transaction.atomic():
                    conversation.langextract_analysis = analysis
                    conversation.save(update_fields=['langextract_analysis'])
                
                updated_count += 1
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} conversation analyses'))

    def _determine_message_analysis_source(self, analysis):
        """Determine the source of message analysis based on structure"""
        
        # Check if it looks like LLM analysis
        if any(key in analysis for key in ['llm_analyzed', 'llm_model', 'api_available']):
            llm_model = analysis.get('llm_model', 'gemini-pro')
            return f'LLM ({llm_model})'
        
        # Check if it has hybrid system markers
        if 'analysis_source' in analysis:
            return analysis['analysis_source']
        
        # Check if it looks like enhanced local analysis
        importance_level = analysis.get('importance_level', {})
        if 'service_issues' in importance_level.get('indicators', {}):
            return 'Local Analysis (Enhanced)'
        
        # Default to basic local analysis
        return 'Local Analysis (Legacy)'

    def _determine_conversation_analysis_source(self, analysis):
        """Determine the source of conversation analysis based on structure"""
        
        # Check if it looks like LLM analysis
        if any(key in analysis for key in ['conversation_patterns', 'customer_insights', 'unknown_patterns']):
            return 'LLM (LangExtract)'
        
        # Check if it has hybrid system markers
        if 'analysis_source' in analysis:
            return analysis['analysis_source']
        
        # Check version to determine source
        version = analysis.get('analysis_version', '')
        if 'langextract' in version:
            return 'LLM (LangExtract)'
        elif 'simple' in version:
            return 'Local Analysis (Simple)'
        
        # Default to local analysis
        return 'Local Analysis (Legacy)'