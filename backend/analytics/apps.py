from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = _('Chat Analytics')
    
    def ready(self):
        """Analytics signals removed per user request"""
        pass
