# Migration to replace old document system with AI-powered SmartDocument system
from django.db import migrations, models
import django.db.models.deletion
import documents.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('documents', '0002_alter_companydocument_options_and_more'),
    ]

    operations = [
        # First, drop all old document tables to clean slate
        migrations.RunSQL(
            "DROP TABLE IF EXISTS documents_documentversion;",
            reverse_sql="-- No reverse operation needed"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS documents_knowledgegap_conversations;",
            reverse_sql="-- No reverse operation needed"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS documents_knowledgegap;",
            reverse_sql="-- No reverse operation needed"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS documents_companydocument;",
            reverse_sql="-- No reverse operation needed"
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS documents_documentcategory;",
            reverse_sql="-- No reverse operation needed"
        ),
        
        # Create new SmartDocument model
        migrations.CreateModel(
            name='SmartDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_filename', models.CharField(max_length=255, verbose_name='Original Filename')),
                ('title', models.CharField(help_text='AI-generated title, you can edit it', max_length=200, verbose_name='Title')),
                ('description', models.TextField(blank=True, help_text='AI-generated description, you can edit it', verbose_name='Description')),
                ('file', models.FileField(help_text='Upload PDF, DOCX, TXT, MD, JSON, CSV, XLSX, RTF, HTML (Max: 100MB)', upload_to='smart_documents/%Y/%m/', validators=[documents.models.validate_document_file], verbose_name='Document File')),
                ('status', models.CharField(choices=[('uploading', 'Uploading'), ('processing', 'AI Processing'), ('ready', 'Ready'), ('error', 'Processing Error'), ('archived', 'Archived')], default='uploading', max_length=20, verbose_name='Processing Status')),
                ('ai_category', models.CharField(blank=True, help_text='Automatically detected category', max_length=100, verbose_name='AI Category')),
                ('category_confidence', models.CharField(choices=[('high', 'High Confidence'), ('medium', 'Medium Confidence'), ('low', 'Low Confidence'), ('manual', 'Manually Set')], default='medium', max_length=20, verbose_name='Category Confidence')),
                ('ai_keywords', models.JSONField(default=list, help_text='Automatically extracted keywords', verbose_name='AI Keywords')),
                ('ai_tags', models.JSONField(default=list, help_text='Smart tags for organization', verbose_name='AI Tags')),
                ('ai_summary', models.TextField(blank=True, help_text='Automatically generated summary', verbose_name='AI Summary')),
                ('extracted_content', models.TextField(blank=True, help_text='Full text extracted from document', verbose_name='Extracted Content')),
                ('key_information', models.JSONField(default=dict, help_text='Structured key information extracted by AI', verbose_name='Key Information')),
                ('document_type', models.CharField(blank=True, help_text='AI-detected document type', max_length=50, verbose_name='Document Type')),
                ('detected_language', models.CharField(default='en', max_length=10, verbose_name='Detected Language')),
                ('admin_category', models.CharField(blank=True, help_text='Override AI category if needed', max_length=100, verbose_name='Admin Category Override')),
                ('admin_keywords', models.JSONField(default=list, help_text='Additional keywords added by admin', verbose_name='Admin Keywords')),
                ('admin_notes', models.TextField(blank=True, help_text='Internal notes about this document', verbose_name='Admin Notes')),
                ('priority', models.IntegerField(default=5, help_text='Priority level 1-10 (higher = more important)', verbose_name='Priority')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('is_featured', models.BooleanField(default=False, verbose_name='Is Featured')),
                ('file_size', models.BigIntegerField(blank=True, null=True, verbose_name='File Size')),
                ('file_hash', models.CharField(blank=True, max_length=64, verbose_name='File Hash')),
                ('view_count', models.IntegerField(default=0, verbose_name='View Count')),
                ('reference_count', models.IntegerField(default=0, verbose_name='Reference Count')),
                ('last_accessed', models.DateTimeField(blank=True, null=True, verbose_name='Last Accessed')),
                ('effectiveness_score', models.FloatField(default=0.0, verbose_name='Effectiveness Score')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('processed_at', models.DateTimeField(blank=True, null=True, verbose_name='Processed At')),
                ('ai_processing_log', models.JSONField(default=dict, help_text='Log of AI processing steps and results', verbose_name='AI Processing Log')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_smart_documents', to=settings.AUTH_USER_MODEL, verbose_name='Uploaded By')),
            ],
            options={
                'verbose_name': 'Smart Document',
                'verbose_name_plural': 'Smart Documents',
                'ordering': ['-priority', '-created_at'],
            },
        ),
        
        # Create DocumentProcessingQueue model
        migrations.CreateModel(
            name='DocumentProcessingQueue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20, verbose_name='Task Status')),
                ('priority', models.IntegerField(default=5, verbose_name='Processing Priority')),
                ('retry_count', models.IntegerField(default=0, verbose_name='Retry Count')),
                ('error_message', models.TextField(blank=True, verbose_name='Error Message')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='Started At')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed At')),
                ('document', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='processing_task', to='documents.smartdocument', verbose_name='Document')),
            ],
            options={
                'verbose_name': 'Document Processing Task',
                'verbose_name_plural': 'Document Processing Tasks',
                'ordering': ['-priority', 'created_at'],
            },
        ),
        
        # Update DocumentFeedback to work with SmartDocument
        migrations.AlterField(
            model_name='documentfeedback',
            name='document',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='documents.smartdocument', verbose_name='Document'),
        ),
        migrations.AlterField(
            model_name='documentfeedback',
            name='feedback_type',
            field=models.CharField(choices=[('helpful', 'Helpful'), ('not_helpful', 'Not Helpful'), ('outdated', 'Outdated'), ('inaccurate', 'Inaccurate'), ('well_categorized', 'Well Categorized'), ('poorly_categorized', 'Poorly Categorized')], max_length=20, verbose_name='Feedback Type'),
        ),
        migrations.AlterField(
            model_name='documentfeedback',
            name='rating',
            field=models.IntegerField(blank=True, help_text='Rating from 1-5', null=True, verbose_name='Rating'),
        ),
        migrations.AlterField(
            model_name='documentfeedback',
            name='search_query',
            field=models.CharField(blank=True, help_text='Query that led to this document', max_length=200, verbose_name='Search Query'),
        ),
        migrations.AlterUniqueTogether(
            name='documentfeedback',
            unique_together={('document', 'user', 'feedback_type')},
        ),
        
        # Add database indexes for performance
        migrations.AddIndex(
            model_name='smartdocument',
            index=models.Index(fields=['status'], name='documents_s_status_b88bbb_idx'),
        ),
        migrations.AddIndex(
            model_name='smartdocument',
            index=models.Index(fields=['ai_category'], name='documents_s_ai_cate_876a46_idx'),
        ),
        migrations.AddIndex(
            model_name='smartdocument',
            index=models.Index(fields=['document_type'], name='documents_s_documen_5ace69_idx'),
        ),
        migrations.AddIndex(
            model_name='smartdocument',
            index=models.Index(fields=['is_active', 'priority'], name='documents_s_is_acti_5d367b_idx'),
        ),
    ]