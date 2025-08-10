from django.apps import AppConfig


class ChatbotBackendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot_backend'
    
    def ready(self):
    # Import admin customizations if they exist
        try:
            from . import admin
        except ImportError:
            pass