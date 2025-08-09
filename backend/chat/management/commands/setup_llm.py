"""
Management command to set up initial LLM API configurations and prompts
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from chat.models import APIConfiguration, AdminPrompt


class Command(BaseCommand):
    help = 'Set up initial LLM API configurations and system prompts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-configs',
            action='store_true',
            help='Create default API configurations (inactive)',
        )
        parser.add_argument(
            '--create-prompts',
            action='store_true',
            help='Create default system prompts',
        )

    def handle(self, *args, **options):
        if options['create_configs']:
            self.create_api_configurations()
        
        if options['create_prompts']:
            self.create_default_prompts()
        
        if not options['create_configs'] and not options['create_prompts']:
            self.stdout.write(
                self.style.WARNING(
                    'Please specify --create-configs and/or --create-prompts'
                )
            )

    def create_api_configurations(self):
        """Create default API configurations"""
        self.stdout.write('Creating default API configurations...')
        
        configs = [
            {
                'provider': 'openai',
                'model_name': 'gpt-4',
                'api_key': 'your-openai-api-key-here',
            },
            {
                'provider': 'gemini',
                'model_name': 'gemini-pro',
                'api_key': 'your-gemini-api-key-here',
            },
            {
                'provider': 'claude',
                'model_name': 'claude-3-sonnet-20240229',
                'api_key': 'your-claude-api-key-here',
            },
        ]
        
        created_count = 0
        for config_data in configs:
            config, created = APIConfiguration.objects.get_or_create(
                provider=config_data['provider'],
                defaults={
                    'model_name': config_data['model_name'],
                    'api_key': config_data['api_key'],
                    'is_active': False,  # Inactive by default until API keys are set
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {config_data['provider']} configuration"
                    )
                )
            else:
                self.stdout.write(
                    f"{config_data['provider']} configuration already exists"
                )
        
        if created_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n📝 {created_count} configurations created but are INACTIVE.\n"
                    "Update API keys in Django admin and set is_active=True to enable them."
                )
            )

    def create_default_prompts(self):
        """Create default system prompts"""
        self.stdout.write('Creating default system prompts...')
        
        # Get admin user for created_by field
        admin_user = User.objects.filter(is_superuser=True).first()
        
        prompts = [
            # English prompts
            {
                'name': 'Default System Prompt',
                'prompt_type': 'system',
                'language': 'en',
                'is_default': True,
                'prompt_text': """You are a helpful AI assistant for DataPro Solutions' customer support system.

Key Guidelines:
- Provide accurate, helpful, and professional responses
- Maintain a friendly and empathetic tone
- If you cannot answer a question completely, acknowledge this and suggest escalating to human support
- Keep responses concise but comprehensive
- Focus on solving the customer's problem
- Ask clarifying questions when needed

Company Context:
- DataPro Solutions provides data analytics and business intelligence services
- We help companies make data-driven decisions
- Our main products include analytics dashboards, reporting tools, and data integration services

If a question is outside your knowledge or requires human judgment, respond with: "I'd be happy to connect you with one of our human support specialists who can provide more detailed assistance with this specific issue."
""",
                'description': 'Main system prompt for general customer support interactions'
            },
            {
                'name': 'Greeting Prompt',
                'prompt_type': 'greeting',
                'language': 'en',
                'is_default': True,
                'prompt_text': """Hello! Welcome to DataPro Solutions support. I'm your AI assistant, here to help you with your questions about our analytics and business intelligence services.

How can I assist you today?""",
                'description': 'Initial greeting message for new conversations'
            },
            {
                'name': 'Error Handling',
                'prompt_type': 'error',
                'language': 'en',
                'is_default': True,
                'prompt_text': """I apologize, but I encountered an issue processing your request. Let me try to help in a different way.

Could you please rephrase your question or provide a bit more detail about what you're looking for? If the issue persists, I'll connect you with a human support specialist right away.""",
                'description': 'Response when technical errors occur'
            },
            {
                'name': 'Escalation Prompt',
                'prompt_type': 'escalation',
                'language': 'en',
                'is_default': True,
                'prompt_text': """I understand this requires specialized attention. Let me connect you with one of our human support specialists who can provide detailed assistance with your specific situation.

They'll be able to access your account details and provide personalized solutions. Please hold on while I transfer you.""",
                'description': 'Used when escalating to human support'
            },
            
            # Japanese prompts
            {
                'name': 'デフォルトシステムプロンプト',
                'prompt_type': 'system',
                'language': 'ja',
                'is_default': True,
                'prompt_text': """あなたは DataPro Solutions のカスタマーサポートシステムの親切な AI アシスタントです。

重要なガイドライン:
- 正確で役に立つ、プロフェッショナルな回答を提供してください
- 親しみやすく共感的な口調を保ってください
- 質問に完全に答えられない場合は、それを認めて人間のサポートへのエスカレーションを提案してください
- 回答は簡潔でありながら包括的にしてください
- 顧客の問題解決に焦点を当ててください
- 必要に応じて確認質問をしてください

会社の背景:
- DataPro Solutions はデータ分析とビジネスインテリジェンスサービスを提供しています
- 企業がデータ駆動型の意思決定を行うお手伝いをしています
- 主な製品には分析ダッシュボード、レポートツール、データ統合サービスが含まれます

質問があなたの知識範囲外であるか人間の判断が必要な場合は、「この特定の問題についてより詳細な支援を提供できる人間のサポート専門家におつなぎいたします」と回答してください。
""",
                'description': '一般的なカスタマーサポート対話用のメインシステムプロンプト'
            },
            {
                'name': '挨拶プロンプト',
                'prompt_type': 'greeting',
                'language': 'ja',
                'is_default': True,
                'prompt_text': """こんにちは！DataPro Solutions サポートへようこそ。私はあなたの AI アシスタントです。分析とビジネスインテリジェンスサービスに関するご質問をお手伝いいたします。

本日はどのようなご用件でしょうか？""",
                'description': '新しい会話の初期挨拶メッセージ'
            },
        ]
        
        created_count = 0
        for prompt_data in prompts:
            prompt, created = AdminPrompt.objects.get_or_create(
                name=prompt_data['name'],
                prompt_type=prompt_data['prompt_type'],
                language=prompt_data['language'],
                defaults={
                    'prompt_text': prompt_data['prompt_text'],
                    'description': prompt_data['description'],
                    'is_default': prompt_data['is_default'],
                    'is_active': True,
                    'created_by': admin_user,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created prompt: {prompt_data['name']} ({prompt_data['language']})"
                    )
                )
            else:
                self.stdout.write(
                    f"Prompt already exists: {prompt_data['name']} ({prompt_data['language']})"
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ {created_count} default prompts created successfully!"
            )
        )