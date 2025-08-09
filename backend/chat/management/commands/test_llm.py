"""
Management command to test LLM API configurations
"""

import asyncio
from django.core.management.base import BaseCommand
from chat.llm_services import LLMManager
from chat.models import APIConfiguration


class Command(BaseCommand):
    help = 'Test LLM API configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            help='Test specific provider (openai, gemini, claude)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Test all active configurations',
        )

    def handle(self, *args, **options):
        if options['all']:
            self.test_all_providers()
        elif options['provider']:
            asyncio.run(self.test_provider(options['provider']))
        else:
            self.stdout.write(
                self.style.WARNING('Please specify --provider or --all')
            )

    def test_all_providers(self):
        """Test all active API configurations"""
        configs = APIConfiguration.objects.filter(is_active=True)
        
        if not configs.exists():
            self.stdout.write(
                self.style.ERROR('No active API configurations found')
            )
            return

        self.stdout.write(f'Testing {configs.count()} active configurations...\n')
        
        for config in configs:
            self.stdout.write(f'Testing {config.provider}...')
            result = asyncio.run(LLMManager.test_configuration(config.provider))
            
            if result['status'] == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {config.provider} ({result['model']}) - "
                        f"Response time: {result['response_time']:.2f}s"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ {config.provider} - Error: {result['error']}"
                    )
                )
            self.stdout.write('')

    async def test_provider(self, provider):
        """Test specific provider"""
        self.stdout.write(f'Testing {provider}...')
        
        try:
            result = await LLMManager.test_configuration(provider)
            
            if result['status'] == 'success':
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {provider} configuration is working!\n"
                        f"Model: {result['model']}\n"
                        f"Response time: {result['response_time']:.2f}s\n"
                        f"Test response: {result['response']}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ {provider} configuration failed!\n"
                        f"Error: {result['error']}"
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Test failed: {str(e)}")
            )