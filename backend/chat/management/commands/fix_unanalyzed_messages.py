"""
Django management command to analyze any unanalyzed user messages
Usage: python manage.py fix_unanalyzed_messages
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from chat.models import Message
from core.services.message_analysis_service import message_analysis_service


class Command(BaseCommand):
    help = 'Analyze any unanalyzed user messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be analyzed without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of messages to process (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        # Find unanalyzed user messages
        unanalyzed_messages = Message.objects.filter(
            sender_type='user',
            message_analysis__exact={}
        )[:limit]
        
        total_count = unanalyzed_messages.count()
        
        if total_count == 0:
            self.stdout.write(
                self.style.SUCCESS('[+] All user messages are already analyzed!')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'Found {total_count} unanalyzed user messages')
        )
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('DRY RUN - No changes will be made'))
            for message in unanalyzed_messages:
                self.stdout.write(f'  Would analyze: {message.uuid} - "{message.content[:50]}..."')
            return
        
        # Process messages
        fixed_count = 0
        error_count = 0
        
        for message in unanalyzed_messages:
            try:
                self.stdout.write(f'Analyzing: {message.content[:60]}...', ending='')
                
                with transaction.atomic():
                    # Analyze the message
                    analysis_result = message_analysis_service.analyze_user_message(message)
                    
                    if analysis_result and 'error' not in analysis_result:
                        # Save analysis
                        message.message_analysis = analysis_result
                        message.save(update_fields=['message_analysis'])
                        fixed_count += 1
                        self.stdout.write(self.style.SUCCESS(' [+]'))
                    else:
                        error_count += 1
                        error_msg = analysis_result.get('error', 'Unknown error') if analysis_result else 'No result'
                        self.stdout.write(self.style.ERROR(f' [-] ({error_msg})'))
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f' [-] (Exception: {e})'))
        
        # Show results
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'[+] Fixed: {fixed_count} messages'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'[-] Errors: {error_count} messages'))
        
        # Show final coverage
        total_user_messages = Message.objects.filter(sender_type='user').count()
        analyzed_messages = Message.objects.filter(sender_type='user').exclude(message_analysis__exact={}).count()
        coverage = (analyzed_messages / total_user_messages * 100) if total_user_messages > 0 else 0
        
        self.stdout.write('')
        self.stdout.write(f'Final coverage: {analyzed_messages}/{total_user_messages} ({coverage:.1f}%)')
        
        if coverage == 100:
            self.stdout.write(self.style.SUCCESS('[!] 100% analysis coverage achieved!'))
        else:
            remaining = total_user_messages - analyzed_messages
            self.stdout.write(self.style.WARNING(f'[!] {remaining} messages still need analysis'))