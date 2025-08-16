"""
Django management command to generate analytics summaries
Usage: python manage.py generate_analytics
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from analytics.services import automatic_analytics_service
from analytics.models import AnalyticsSummary
from chat.models import Conversation


class Command(BaseCommand):
    help = 'Generate analytics summaries automatically from conversation analysis data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing summaries',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Generate summary for specific date (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old analytics summaries (older than 1 year)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Analytics Summary Generation'))
        self.stdout.write('=' * 50)
        
        # Check current status
        total_conversations = Conversation.objects.count()
        analyzed_conversations = Conversation.objects.exclude(langextract_analysis__exact={}).count()
        existing_summaries = AnalyticsSummary.objects.count()
        
        self.stdout.write(f'Total Conversations: {total_conversations}')
        self.stdout.write(f'Analyzed Conversations: {analyzed_conversations}')
        self.stdout.write(f'Existing Analytics Summaries: {existing_summaries}')
        self.stdout.write('')
        
        if analyzed_conversations == 0:
            self.stdout.write(self.style.WARNING(
                'No analyzed conversations found. Please run conversation analysis first.'
            ))
            return
        
        # Handle cleanup option
        if options['cleanup']:
            self.stdout.write('Cleaning up old analytics summaries...')
            cleaned_count = automatic_analytics_service.cleanup_old_summaries()
            self.stdout.write(self.style.SUCCESS(f'Cleaned up {cleaned_count} old summaries'))
            self.stdout.write('')
        
        # Handle specific date option
        if options['date']:
            try:
                from datetime import datetime
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                self.stdout.write(f'Generating summary for specific date: {target_date}')
                
                summary = automatic_analytics_service.update_analytics_summary_for_date(target_date)
                if summary:
                    self.stdout.write(self.style.SUCCESS(
                        f'Generated summary for {target_date}: '
                        f'{summary.total_conversations} conversations, '
                        f'{summary.average_satisfaction:.1f} avg satisfaction'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(f'No data found for {target_date}'))
                    
            except ValueError:
                raise CommandError('Invalid date format. Use YYYY-MM-DD')
            return
        
        # Generate missing summaries
        self.stdout.write('Generating missing analytics summaries...')
        missing_count = automatic_analytics_service.generate_missing_summaries()
        
        if missing_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Generated {missing_count} new analytics summaries'))
        else:
            self.stdout.write('All analytics summaries are up to date')
        
        # Show final statistics
        final_summaries = AnalyticsSummary.objects.count()
        self.stdout.write('')
        self.stdout.write(f'Total Analytics Summaries: {final_summaries}')
        
        if final_summaries > 0:
            self.stdout.write('')
            self.stdout.write('Recent Summaries:')
            self.stdout.write('-' * 30)
            
            for summary in AnalyticsSummary.objects.all()[:5]:
                self.stdout.write(
                    f'{summary.date}: {summary.total_conversations} convs, '
                    f'{summary.average_satisfaction:.1f} satisfaction, '
                    f'{summary.positive_conversations}+ {summary.negative_conversations}- {summary.neutral_conversations}neutral'
                )
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Analytics summaries generated! Check the admin at:\n'
            'http://localhost:8000/admin/analytics/analyticssummary/'
        ))
        
        # Test automatic system
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            'Automatic analytics generation is now enabled!\n'
            'New summaries will be created automatically when conversations are analyzed.'
        ))