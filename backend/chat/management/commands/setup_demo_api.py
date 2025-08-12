"""
Management command to set up demo API configuration for testing
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chat.models import APIConfiguration


class Command(BaseCommand):
    help = 'Set up demo API configuration for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--gemini-key',
            type=str,
            help='Gemini API key',
        )
        parser.add_argument(
            '--openai-key', 
            type=str,
            help='OpenAI API key',
        )
        parser.add_argument(
            '--claude-key',
            type=str,
            help='Claude API key',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up demo API configuration...')

        # Create demo user if not exists
        demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@datapro.solutions',
                'first_name': 'Demo',
                'last_name': 'User',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created demo user: {demo_user.username}')
            )
        else:
            self.stdout.write(f'Demo user already exists: {demo_user.username}')

        # Set up API configurations
        configs_created = 0
        
        if options['gemini_key']:
            config, created = APIConfiguration.objects.get_or_create(
                provider='gemini',
                defaults={
                    'api_key': options['gemini_key'],
                    'model_name': 'gemini-1.5-flash',
                    'is_active': True,
                }
            )
            if created:
                configs_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created Gemini API configuration')
                )
            else:
                # Update existing
                config.api_key = options['gemini_key']
                config.is_active = True
                config.save()
                self.stdout.write(f'Updated Gemini API configuration')
        
        if options['openai_key']:
            config, created = APIConfiguration.objects.get_or_create(
                provider='openai',
                defaults={
                    'api_key': options['openai_key'],
                    'model_name': 'gpt-3.5-turbo',
                    'is_active': True,
                }
            )
            if created:
                configs_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created OpenAI API configuration')
                )
            else:
                # Update existing
                config.api_key = options['openai_key']
                config.is_active = True
                config.save()
                self.stdout.write(f'Updated OpenAI API configuration')
        
        if options['claude_key']:
            config, created = APIConfiguration.objects.get_or_create(
                provider='claude',
                defaults={
                    'api_key': options['claude_key'],
                    'model_name': 'claude-3-sonnet-20240229',
                    'is_active': True,
                }
            )
            if created:
                configs_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created Claude API configuration')
                )
            else:
                # Update existing
                config.api_key = options['claude_key']
                config.is_active = True
                config.save()
                self.stdout.write(f'Updated Claude API configuration')

        if configs_created == 0 and not any([options['gemini_key'], options['openai_key'], options['claude_key']]):
            self.stdout.write(
                self.style.WARNING(
                    'No API keys provided. Use --gemini-key, --openai-key, or --claude-key'
                )
            )
            self.stdout.write('Example: python manage.py setup_demo_api --gemini-key YOUR_KEY_HERE')
        else:
            self.stdout.write(
                self.style.SUCCESS('Demo API setup complete!')
            )