from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AiHelperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_helper'
    verbose_name = _('AI Helper')