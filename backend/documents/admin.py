from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse, path
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from django.contrib.admin.views.decorators import staff_member_required
from django import forms
from django.core.exceptions import ValidationError
import os
import mimetypes
import uuid
from .models import Document, DocumentationImprovement, calculate_file_hash


class DocumentAdminForm(forms.ModelForm):
    """Custom form for Document admin with friendly duplicate checking"""
    
    class Meta:
        model = Document
        fields = '__all__'
    
    def clean_file(self):
        """Check for duplicate files and show friendly error message"""
        file = self.cleaned_data.get('file')
        if not file:
            return file
        
        # Calculate hash for the uploaded file
        file_hash = calculate_file_hash(file)
        
        if file_hash:
            # Check for existing documents with the same hash
            existing_query = Document.objects.filter(file_hash=file_hash).exclude(file_hash='')
            
            # Exclude current document if editing
            if self.instance and self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            existing_doc = existing_query.first()
            if existing_doc:
                raise ValidationError(
                    _('A file with identical content already exists: "%(name)s". '
                      'Please choose a different file or update the existing document instead.'),
                    params={'name': existing_doc.name}
                )
        
        return file


class DocumentManagementAdmin(admin.AdminSite):
    """Custom admin site for document management"""
    site_header = _('Document Management')
    site_title = _('Documents')
    index_title = _('Document Management System')

# Create custom admin site instance
document_admin_site = DocumentManagementAdmin(name='documents')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Simple document management interface with file operations"""
    
    form = DocumentAdminForm
    
    # Use UUID instead of pk in admin URLs
    def get_object(self, request, object_id, from_field=None):
        """Override to get objects by UUID instead of pk"""
        # Ensure object_id is a string
        object_id_str = str(object_id)
        
        try:
            # First try to parse as UUID string
            uuid_obj = uuid.UUID(object_id_str)
            return self.get_queryset(request).get(uuid=uuid_obj)
        except (ValueError, TypeError):
            # If UUID parsing fails, try as regular pk (for backward compatibility)
            try:
                return self.get_queryset(request).get(pk=object_id_str)
            except (ValueError, Document.DoesNotExist):
                return None
        except Document.DoesNotExist:
            return None
    
    def response_change(self, request, obj):
        """Override to redirect using UUID instead of pk"""
        response = super().response_change(request, obj)
        if hasattr(response, 'url') and response.url:
            # Replace pk-based URLs with UUID-based URLs
            import re
            # Pattern to match /admin/documents/document/[number]/ 
            pattern = r'/admin/documents/document/\d+/'
            replacement = f'/admin/documents/document/{str(obj.uuid)}/'
            response.url = re.sub(pattern, replacement, response.url)
        return response
    
    def response_add(self, request, obj, post_url_continue=None):
        """Override to use UUID in add response redirects"""
        if post_url_continue is None:
            post_url_continue = f'../{str(obj.uuid)}/change/'
        return super().response_add(request, obj, post_url_continue)
    
    def get_absolute_url(self, obj):
        """Get the absolute admin URL for this object using UUID"""
        return f'/admin/documents/document/{str(obj.uuid)}/change/'
    
    list_display = [
        'name_display',
        'file_type_display',
        'file_size_display',
        'category_display',
        'is_active_display',
        'uploaded_by_display',
        'created_at_display',
        'file_actions',
    ]
    
    list_filter = [
        'file_type',
        'category',
        'is_active',
        'created_at',
        'uploaded_by',
    ]
    
    search_fields = [
        'name',
        'original_filename',
        'description',
        'tags',
        'category',
    ]
    
    readonly_fields = [
        'uuid',
        'original_filename',
        'file_size',
        'file_type',
        'file_hash',
        'uploaded_by',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = [
        (_('Document Information'), {
            'fields': [
                'name',
                'description',
                'file',
            ]
        }),
        (_('Organization'), {
            'fields': [
                'category',
                'tags',
                'is_active',
            ]
        }),
        (_('File Metadata'), {
            'fields': [
                'uuid',
                ('original_filename', 'file_type'),
                'file_size',
                'file_hash',
            ],
            'classes': ['collapse']
        }),
        (_('Audit Information'), {
            'fields': [
                'uploaded_by',
                ('created_at', 'updated_at'),
            ],
            'classes': ['collapse']
        }),
    ]
    
    ordering = ['-created_at']
    
    def save_model(self, request, obj, form, change):
        """Automatically set uploaded_by to current user when creating new documents"""
        if not change:  # Only for new objects
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Custom UUID-based URLs for file operations
            path('download/<uuid:document_uuid>/', self.admin_site.admin_view(self.download_file), name='documents_download'),
            path('open/<uuid:document_uuid>/', self.admin_site.admin_view(self.open_file), name='documents_open'),
            path('info/<uuid:document_uuid>/', self.admin_site.admin_view(self.show_file_info), name='documents_info'),
            
            # Override default admin URLs to use UUID as string instead of pk
            path('<str:object_id>/change/', self.admin_site.admin_view(self.change_view), name='documents_document_change'),
            path('<str:object_id>/delete/', self.admin_site.admin_view(self.delete_view), name='documents_document_delete'),
            path('<str:object_id>/history/', self.admin_site.admin_view(self.history_view), name='documents_document_history'),
        ]
        return custom_urls + urls
    
    
    def download_file(self, request, document_uuid):
        """Download document file"""
        document = get_object_or_404(Document, uuid=document_uuid)
        
        if not document.file:
            messages.error(request, _('File not found'))
            return redirect('admin:documents_document_changelist')
        
        file_path = document.file.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(file_path)[0])
                response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
                return response
        else:
            messages.error(request, _('File not found on server'))
            return redirect('admin:documents_document_changelist')
    
    def open_file(self, request, document_uuid):
        """Open/preview document file"""
        document = get_object_or_404(Document, uuid=document_uuid)
        
        if not document.file:
            messages.error(request, _('File not found'))
            return redirect('admin:documents_document_changelist')
        
        file_path = document.file.path
        if not os.path.exists(file_path):
            messages.error(request, _('File not found on server'))
            return redirect('admin:documents_document_changelist')
        
        # Get file extension to determine how to preview
        file_ext = document.file_type.lower()
        
        # For viewable files, serve them inline
        if file_ext in ['pdf', 'txt', 'md', 'html', 'htm', 'json', 'csv']:
            with open(file_path, 'rb') as fh:
                content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                response = HttpResponse(fh.read(), content_type=content_type)
                # Use inline disposition for preview instead of attachment
                response['Content-Disposition'] = f'inline; filename="{document.original_filename}"'
                return response
        
        # For non-previewable files, show info page instead of direct download
        return self.show_file_info(request, document_uuid)
    
    def show_file_info(self, request, document_uuid):
        """Show file information for non-previewable files"""
        document = get_object_or_404(Document, uuid=document_uuid)
        
        context = {
            'document': document,
            'title': f'File Info: {document.name}',
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request, document),
        }
        
        return TemplateResponse(request, 'admin/documents/file_info.html', context)
    
    # Custom display methods
    def name_display(self, obj):
        """Display name with link to UUID-based edit page"""
        name = obj.name or _('Untitled')
        edit_url = reverse('admin:documents_document_change', args=[str(obj.uuid)])
        return format_html('<a href="{}">{}</a>', edit_url, name)
    name_display.short_description = _('Name')
    name_display.admin_order_field = 'name'
    
    def file_type_display(self, obj):
        if obj.file_type:
            return format_html('<code style="background: #f5f5f5; padding: 2px 4px;">{}</code>', obj.file_type)
        return '-'
    file_type_display.short_description = _('Type')
    
    def file_size_display(self, obj):
        return obj.get_file_size_display()
    file_size_display.short_description = _('Size')
    file_size_display.admin_order_field = 'file_size'
    
    def category_display(self, obj):
        return obj.category or _('Uncategorized')
    category_display.short_description = _('Category')
    category_display.admin_order_field = 'category'
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.short_description = _('Active')
    is_active_display.admin_order_field = 'is_active'
    is_active_display.boolean = True
    
    def uploaded_by_display(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.username
        return _('Unknown')
    uploaded_by_display.short_description = _('Uploaded By')
    uploaded_by_display.admin_order_field = 'uploaded_by'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = _('Created')
    created_at_display.admin_order_field = 'created_at'
    
    def file_actions(self, obj):
        """File action buttons"""
        download_url = reverse('admin:documents_download', args=[str(obj.uuid)])
        open_url = reverse('admin:documents_open', args=[str(obj.uuid)])
        
        return format_html(
            '<a href="{}" class="button" title="{}">{}</a> '
            '<a href="{}" class="button" title="{}">{}</a>',
            download_url, _('Download'), '📥',
            open_url, _('Open'), '👁'
        )
    file_actions.short_description = _('Actions')
    
    # Custom actions
    actions = ['activate_documents', 'deactivate_documents', 'bulk_categorize']
    
    def activate_documents(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, _('Selected documents activated.'))
    activate_documents.short_description = _('Activate selected documents')
    
    def deactivate_documents(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, _('Selected documents deactivated.'))
    deactivate_documents.short_description = _('Deactivate selected documents')
    
    def bulk_categorize(self, request, queryset):
        # This would show a form to set category for multiple documents
        self.message_user(request, _('Bulk categorization feature coming soon.'))
    bulk_categorize.short_description = _('Bulk categorize selected documents')


@admin.register(DocumentationImprovement)
class DocumentationImprovementAdmin(admin.ModelAdmin):
    """Admin interface for Documentation & FAQ Improvements"""
    
    # Use UUID instead of pk in admin URLs
    def get_object(self, request, object_id, from_field=None):
        """Override to get objects by UUID instead of pk"""
        object_id_str = str(object_id)
        
        try:
            # First try to parse as UUID string
            uuid_obj = uuid.UUID(object_id_str)
            return self.get_queryset(request).get(uuid=uuid_obj)
        except (ValueError, TypeError):
            # If UUID parsing fails, try as regular pk (for backward compatibility)
            try:
                return self.get_queryset(request).get(pk=object_id_str)
            except (ValueError, DocumentationImprovement.DoesNotExist):
                return None
        except DocumentationImprovement.DoesNotExist:
            return None
    
    def response_change(self, request, obj):
        """Override to redirect using UUID instead of pk"""
        response = super().response_change(request, obj)
        if hasattr(response, 'url') and response.url:
            # Replace pk-based URLs with UUID-based URLs
            import re
            # Pattern to match /admin/documents/documentationimprovement/[number]/
            pattern = r'/admin/documents/documentationimprovement/\d+/'
            replacement = f'/admin/documents/documentationimprovement/{str(obj.uuid)}/'
            response.url = re.sub(pattern, replacement, response.url)
        return response
    
    def response_add(self, request, obj, post_url_continue=None):
        """Override to use UUID in add response redirects"""
        if post_url_continue is None:
            post_url_continue = f'../{str(obj.uuid)}/change/'
        return super().response_add(request, obj, post_url_continue)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Override default admin URLs to use UUID as string instead of pk
            path('<str:object_id>/change/', self.admin_site.admin_view(self.change_view), name='documents_documentationimprovement_change'),
            path('<str:object_id>/delete/', self.admin_site.admin_view(self.delete_view), name='documents_documentationimprovement_delete'),
            path('<str:object_id>/history/', self.admin_site.admin_view(self.history_view), name='documents_documentationimprovement_history'),
        ]
        return custom_urls + urls
    
    # List display with proper methods to avoid "-------" selector issues
    list_display = [
        'conversation_title_display',
        'issues_detected_display', 
        'priority_display',
        'category_display',
        'satisfaction_level_display',
        'created_at_display',
        'analysis_status_display'
    ]
    
    list_filter = [
        'priority',
        'category', 
        'satisfaction_level',
        'analysis_completed',
        'created_at'
    ]
    
    search_fields = [
        'conversation_title',
        'issues_detected',
        'category',
        'langextract_analysis_summary'
    ]
    
    readonly_fields = [
        'uuid',
        'conversation',
        'conversation_title',
        'created_at',
        'updated_at',
        'langextract_full_analysis_display'
    ]
    
    fieldsets = [
        (_('Conversation Information'), {
            'fields': [
                'conversation',
                'conversation_title',
            ]
        }),
        (_('Analysis Results'), {
            'fields': [
                'issues_detected',
                'priority',
                'category',
                'satisfaction_level',
            ]
        }),
        (_('LangExtract Analysis'), {
            'fields': [
                'langextract_analysis_summary',
                'langextract_full_analysis_display',
                'analysis_completed',
                'analysis_error',
            ],
            'classes': ['collapse']
        }),
        (_('System Information'), {
            'fields': [
                'uuid',
                ('created_at', 'updated_at'),
            ],
            'classes': ['collapse']
        }),
    ]
    
    ordering = ['-created_at']
    
    # Custom display methods to prevent "-------" selector issues
    def conversation_title_display(self, obj):
        """Display conversation title as clickable link to conversation"""
        title = obj.conversation_title or f'Conversation {obj.conversation.id}'
        # Link to the conversation admin page using the conversation's primary key
        conversation_url = f'/admin/chat/conversation/{obj.conversation.id}/change/'
        return format_html('<a href="{}" target="_blank" title="{}">{}</a>', 
                          conversation_url, _('View conversation'), title)
    conversation_title_display.short_description = _('Conversation Title')
    conversation_title_display.admin_order_field = 'conversation_title'
    
    def issues_detected_display(self, obj):
        """Display truncated issues with tooltip for full text"""
        if not obj.issues_detected:
            return _('No issues detected')
        
        preview = obj.issues_detected[:80] + "..." if len(obj.issues_detected) > 80 else obj.issues_detected
        return format_html('<span title="{}">{}</span>', obj.issues_detected, preview)
    issues_detected_display.short_description = _('Issues Detected')
    issues_detected_display.admin_order_field = 'issues_detected'
    
    def priority_display(self, obj):
        """Display priority with color coding"""
        color_class = obj.get_priority_display_color()
        priority_text = obj.get_priority_display()
        return format_html('<span class="{}">{}</span>', color_class, priority_text)
    priority_display.short_description = _('Priority')
    priority_display.admin_order_field = 'priority'
    
    def category_display(self, obj):
        """Display category"""
        return obj.category or _('Uncategorized')
    category_display.short_description = _('Category')
    category_display.admin_order_field = 'category'
    
    def satisfaction_level_display(self, obj):
        """Display satisfaction level with color coding"""
        if not obj.satisfaction_level:
            return _('Not rated')
        
        color_class = obj.get_satisfaction_display_color()
        satisfaction_text = obj.get_satisfaction_level_display()
        stars = '★' * obj.satisfaction_level + '☆' * (5 - obj.satisfaction_level)
        return format_html('<span class="{}" title="{}">{} ({})</span>', 
                          color_class, satisfaction_text, stars, obj.satisfaction_level)
    satisfaction_level_display.short_description = _('Satisfaction Level')
    satisfaction_level_display.admin_order_field = 'satisfaction_level'
    
    def created_at_display(self, obj):
        """Display creation date and time in local timezone"""
        # Use timezone-aware display to avoid async issues
        from django.utils import timezone
        local_time = timezone.localtime(obj.created_at)
        return local_time.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = _('Date & Time')
    created_at_display.admin_order_field = 'created_at'
    
    def analysis_status_display(self, obj):
        """Display analysis completion status"""
        if obj.analysis_error:
            return format_html('<span class="text-danger" title="{}">{}</span>', 
                              obj.analysis_error, _('Error'))
        elif obj.analysis_completed:
            return format_html('<span class="text-success">{}</span>', _('Completed'))
        else:
            return format_html('<span class="text-warning">{}</span>', _('Pending'))
    analysis_status_display.short_description = _('Analysis Status')
    analysis_status_display.admin_order_field = 'analysis_completed'
    
    def langextract_full_analysis_display(self, obj):
        """Display full analysis with show/hide toggle"""
        if not obj.langextract_full_analysis:
            return _('No full analysis available')
        
        import json
        try:
            formatted_json = json.dumps(obj.langextract_full_analysis, indent=2, ensure_ascii=False)
            return format_html(
                '<div>'
                '<button type="button" onclick="toggleAnalysis(this)" class="button">{}</button>'
                '<pre style="display:none; max-height:300px; overflow:auto; background:#f8f8f8; padding:10px; margin-top:10px;">{}</pre>'
                '</div>'
                '<script>'
                'function toggleAnalysis(btn) {{'
                '  var pre = btn.nextElementSibling;'
                '  if (pre.style.display === "none") {{'
                '    pre.style.display = "block";'
                '    btn.textContent = "{}";'
                '  }} else {{'
                '    pre.style.display = "none";'
                '    btn.textContent = "{}";'
                '  }}'
                '}}'
                '</script>',
                _('Show Full Analysis'),
                formatted_json,
                _('Hide Full Analysis'),
                _('Show Full Analysis')
            )
        except (json.JSONDecodeError, TypeError):
            return _('Invalid analysis data')
    langextract_full_analysis_display.short_description = _('Full Analysis')
    
    # Custom actions
    actions = ['mark_analysis_completed', 'reset_analysis', 'bulk_set_priority']
    
    def mark_analysis_completed(self, request, queryset):
        """Mark selected items as analysis completed"""
        updated = queryset.update(analysis_completed=True, analysis_error='')
        self.message_user(request, _('%(count)d items marked as analysis completed.') % {'count': updated})
    mark_analysis_completed.short_description = _('Mark analysis as completed')
    
    def reset_analysis(self, request, queryset):
        """Reset analysis status for selected items"""
        updated = queryset.update(analysis_completed=False, analysis_error='')
        self.message_user(request, _('%(count)d items reset for re-analysis.') % {'count': updated})
    reset_analysis.short_description = _('Reset analysis status')
    
    def bulk_set_priority(self, request, queryset):
        """Bulk set priority for selected items"""
        # This would show a form to set priority for multiple items
        self.message_user(request, _('Bulk priority setting feature coming soon.'))
    bulk_set_priority.short_description = _('Bulk set priority')
    

