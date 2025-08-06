from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from .models import DocumentCategory, CompanyDocument, DocumentVersion, KnowledgeGap, DocumentFeedback


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name_display', 'color_display', 'document_count', 'description_display', 'created_at_display']
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
    
    def name_display(self, obj):
        return obj.name
    name_display.short_description = _('Name')
    name_display.admin_order_field = 'name'
    
    def description_display(self, obj):
        return obj.description
    description_display.short_description = _('Description')
    description_display.admin_order_field = 'description'
    
    def created_at_display(self, obj):
        return obj.created_at
    created_at_display.short_description = _('Created At')
    created_at_display.admin_order_field = 'created_at'


@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title_display', 'category_display', 'version_display', 'file_size_display', 'usage_count_display', 'effectiveness_score_display', 'is_active_display', 'created_at_display']
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
    
    def title_display(self, obj):
        return obj.title
    title_display.short_description = _('Title')
    title_display.admin_order_field = 'title'
    
    def category_display(self, obj):
        return obj.category
    category_display.short_description = _('Category')
    category_display.admin_order_field = 'category'
    
    def version_display(self, obj):
        return obj.version
    version_display.short_description = _('Version')
    version_display.admin_order_field = 'version'
    
    def usage_count_display(self, obj):
        return obj.usage_count
    usage_count_display.short_description = _('Usage Count')
    usage_count_display.admin_order_field = 'usage_count'
    
    def effectiveness_score_display(self, obj):
        return f"{obj.effectiveness_score:.1f}" if obj.effectiveness_score else "-"
    effectiveness_score_display.short_description = _('Effectiveness Score')
    effectiveness_score_display.admin_order_field = 'effectiveness_score'
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.short_description = _('Is Active')
    is_active_display.admin_order_field = 'is_active'
    is_active_display.boolean = True
    
    def created_at_display(self, obj):
        return obj.created_at
    created_at_display.short_description = _('Created At')
    created_at_display.admin_order_field = 'created_at'


@admin.register(KnowledgeGap)
class KnowledgeGapAdmin(admin.ModelAdmin):
    list_display = ['query_preview', 'frequency_display', 'priority_display', 'status_display', 'category_display', 'assigned_to_display', 'last_encountered_display']
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
    
    def frequency_display(self, obj):
        return obj.frequency
    frequency_display.short_description = _('Frequency')
    frequency_display.admin_order_field = 'frequency'
    
    def priority_display(self, obj):
        return obj.get_priority_display()
    priority_display.short_description = _('Priority')
    priority_display.admin_order_field = 'priority'
    
    def status_display(self, obj):
        return obj.get_status_display()
    status_display.short_description = _('Status')
    status_display.admin_order_field = 'status'
    
    def category_display(self, obj):
        return obj.category
    category_display.short_description = _('Category')
    category_display.admin_order_field = 'category'
    
    def assigned_to_display(self, obj):
        return obj.assigned_to if obj.assigned_to else "-"
    assigned_to_display.short_description = _('Assigned To')
    assigned_to_display.admin_order_field = 'assigned_to'
    
    def last_encountered_display(self, obj):
        return obj.last_encountered
    last_encountered_display.short_description = _('Last Encountered')
    last_encountered_display.admin_order_field = 'last_encountered'


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
