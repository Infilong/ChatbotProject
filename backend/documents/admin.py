from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import DocumentCategory, CompanyDocument, DocumentVersion, KnowledgeGap, DocumentFeedback


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'document_count', 'description', 'created_at']
    search_fields = ['name', 'description']
    list_per_page = 25
    ordering = ['name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; background-color: {}; border-radius: 3px; margin-right: 5px;"></span>{}',
            obj.color, obj.color
        )
    color_display.short_description = _('Color')
    
    def document_count(self, obj):
        count = obj.documents.count()
        if count > 0:
            url = f'/admin/documents/companydocument/?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} documents</a>', url, count)
        return _('0 documents')
    document_count.short_description = _('Documents')


@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'version', 'file_size_display', 'usage_count', 'effectiveness_score', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at', 'updated_at', 'effectiveness_score']
    search_fields = ['title', 'description', 'content_text', 'keywords']
    readonly_fields = ['created_at', 'updated_at', 'file_size', 'usage_count', 'last_referenced']
    list_per_page = 25
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        (_('Document Information'), {
            'fields': ('title', 'description', 'category', 'version', 'is_active')
        }),
        (_('File Upload'), {
            'fields': ('file', 'file_size')
        }),
        (_('AI Content Processing'), {
            'fields': ('content_text', 'content_summary', 'keywords'),
            'classes': ('collapse',)
        }),
        (_('Analytics'), {
            'fields': ('usage_count', 'effectiveness_score', 'last_referenced'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return _("Unknown")
    file_size_display.short_description = _('File Size')
    file_size_display.admin_order_field = 'file_size'


@admin.register(KnowledgeGap)
class KnowledgeGapAdmin(admin.ModelAdmin):
    list_display = ['query_preview', 'frequency', 'priority', 'status', 'category', 'assigned_to', 'last_encountered']
    list_filter = ['priority', 'status', 'category', 'first_identified', 'last_encountered']
    search_fields = ['query', 'resolution_notes']
    list_per_page = 25
    date_hierarchy = 'last_encountered'
    ordering = ['-frequency', '-last_encountered']
    
    fieldsets = (
        (_('Gap Information'), {
            'fields': ('query', 'frequency', 'category', 'priority', 'status')
        }),
        (_('Assignment'), {
            'fields': ('assigned_to', 'resolution_notes', 'resolved_at')
        }),
        (_('Timeline'), {
            'fields': ('first_identified', 'last_encountered'),
            'classes': ('collapse',)
        }),
        (_('Related Data'), {
            'fields': ('conversations',),
            'classes': ('collapse',)
        })
    )
    
    def query_preview(self, obj):
        return obj.query[:80] + "..." if len(obj.query) > 80 else obj.query
    query_preview.short_description = _('Query')
    query_preview.admin_order_field = 'query'


@admin.register(DocumentFeedback)
class DocumentFeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'document_link', 'user_link', 'feedback_display', 'rating', 'search_query', 'created_at']
    list_filter = ['feedback_type', 'rating', 'created_at']
    search_fields = ['document__title', 'user__username', 'comment', 'search_query']
    readonly_fields = ['created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def document_link(self, obj):
        url = reverse('admin:documents_companydocument_change', args=[obj.document.id])
        return format_html('<a href="{}">{}</a>', url, obj.document.title[:30])
    document_link.short_description = _('Document')
    
    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = _('User')
    
    def feedback_display(self, obj):
        colors = {
            'helpful': 'green',
            'not_helpful': 'red',
            'outdated': 'orange',
            'unclear': 'purple'
        }
        icons = {
            'helpful': '👍',
            'not_helpful': '👎',
            'outdated': '⏰',
            'unclear': '❓'
        }
        color = colors.get(obj.feedback_type, 'black')
        icon = icons.get(obj.feedback_type, '')
        return format_html('<span style="color: {};">{} {}</span>', color, icon, obj.feedback_type.replace('_', ' ').title())
    feedback_display.short_description = _('Feedback')


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['id', 'document_link', 'version_number', 'created_by', 'created_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['document__title', 'version_number', 'change_notes']
    readonly_fields = ['created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def document_link(self, obj):
        url = reverse('admin:documents_companydocument_change', args=[obj.document.id])
        return format_html('<a href="{}">{}</a>', url, obj.document.title)
    document_link.short_description = _('Document')
