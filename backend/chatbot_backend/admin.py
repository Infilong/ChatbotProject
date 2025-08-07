from django.contrib import admin
from ai_helper.admin import AIHelperAdminMixin


class CustomAdminSite(AIHelperAdminMixin, admin.AdminSite):
    """Custom admin site with AI Helper integration"""
    pass


# Replace the default admin site
admin.site.__class__ = CustomAdminSite