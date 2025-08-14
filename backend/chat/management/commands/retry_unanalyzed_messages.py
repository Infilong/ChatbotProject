"""
Management command to retry analysis for unanalyzed messages
Usage: python manage.py retry_unanalyzed_messages
"""

import asyncio
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from chat.models import Message
from core.services.hybrid_analysis_service import hybrid_analysis_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retry analysis for messages that have no analysis'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of messages to process (default: 50)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be analyzed without actually doing it'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']
        
        self.stdout.write("Searching for unanalyzed user messages...")
        
        # Find user messages that have no analysis or empty analysis
        unanalyzed_messages = Message.objects.filter(
            sender_type='user'
        ).exclude(
            message_analysis__isnull=False
        ).exclude(
            message_analysis={}
        ).order_by('-timestamp')[:limit]
        
        # Also check for messages with empty dict analysis
        empty_analysis_messages = Message.objects.filter(
            sender_type='user',
            message_analysis={}
        ).order_by('-timestamp')[:limit]
        
        # Combine and remove duplicates
        all_unanalyzed = list(unanalyzed_messages) + list(empty_analysis_messages)
        # Remove duplicates based on UUID
        seen_uuids = set()
        unique_messages = []
        for msg in all_unanalyzed:
            if str(msg.uuid) not in seen_uuids:
                unique_messages.append(msg)
                seen_uuids.add(str(msg.uuid))
        
        # Limit to requested number
        messages_to_process = unique_messages[:limit]
        
        if not messages_to_process:
            self.stdout.write(
                self.style.SUCCESS("No unanalyzed messages found!")
            )
            return
        
        self.stdout.write(
            f"Found {len(messages_to_process)} unanalyzed messages"
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
            for msg in messages_to_process:
                self.stdout.write(
                    f"  - {msg.uuid}: \"{msg.content[:50]}...\" "
                    f"({msg.timestamp.strftime('%Y-%m-%d %H:%M')})"
                )
            return
        
        # Process messages
        success_count = 0
        error_count = 0
        
        self.stdout.write("Starting analysis retry process...")
        
        for i, message in enumerate(messages_to_process, 1):
            self.stdout.write(
                f"[{i}/{len(messages_to_process)}] Processing: {message.uuid}"
            )
            
            try:
                # Analyze the message using hybrid approach
                analysis_result = asyncio.run(
                    hybrid_analysis_service.analyze_message_hybrid(message)
                )
                
                if analysis_result and 'error' not in analysis_result:
                    # Add retry information to the analysis
                    analysis_result.update({
                        "manual_retry": True,
                        "retry_timestamp": timezone.now().isoformat(),
                        "retry_command": "retry_unanalyzed_messages"
                    })
                    
                    # Save analysis to message
                    message.message_analysis = analysis_result
                    message.save(update_fields=['message_analysis'])
                    
                    # Log success
                    analysis_source = analysis_result.get('analysis_source', 'Unknown')
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  SUCCESS using {analysis_source}"
                        )
                    )
                    success_count += 1
                else:
                    error_msg = analysis_result.get('error', 'Unknown error') if analysis_result else 'No result'
                    self.stdout.write(
                        self.style.ERROR(
                            f"  FAILED: {error_msg}"
                        )
                    )
                    error_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  EXCEPTION: {str(e)}"
                    )
                )
                error_count += 1
        
        # Summary
        self.stdout.write("")
        self.stdout.write("RETRY ANALYSIS SUMMARY:")
        self.stdout.write(f"  - Total processed: {len(messages_to_process)}")
        self.stdout.write(
            self.style.SUCCESS(f"  - Successful: {success_count}")
        )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f"  - Failed: {error_count}")
            )
        else:
            self.stdout.write(f"  - Failed: {error_count}")
            
        if success_count == len(messages_to_process):
            self.stdout.write(
                self.style.SUCCESS("All messages analyzed successfully!")
            )
        elif success_count > 0:
            self.stdout.write(
                self.style.WARNING(f"{success_count}/{len(messages_to_process)} messages analyzed")
            )
        else:
            self.stdout.write(
                self.style.ERROR("No messages could be analyzed")
            )