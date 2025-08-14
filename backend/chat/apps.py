from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = _('Chat Bot')
    
    def ready(self):
        """
        Import signals when the app is ready
        This ensures automatic analysis is triggered when messages/conversations are saved
        """
        import chat.signals  # noqa
