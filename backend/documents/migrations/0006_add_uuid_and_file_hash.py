# Add UUID and file hash fields for better security and duplicate detection
import uuid
from django.db import migrations, models


def generate_uuids(apps, schema_editor):
    """Generate UUIDs for existing documents"""
    Document = apps.get_model('documents', 'Document')
    for doc in Document.objects.all():
        doc.uuid = uuid.uuid4()
        doc.save()


def reverse_uuids(apps, schema_editor):
    """Reverse operation - nothing needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0005_remove_ai_metadata_field'),
    ]

    operations = [
        # Add UUID field without unique constraint first
        migrations.AddField(
            model_name='document',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, verbose_name='Document UUID'),
        ),
        
        # Add file hash field
        migrations.AddField(
            model_name='document',
            name='file_hash',
            field=models.CharField(blank=True, editable=False, help_text='SHA-256 hash for duplicate detection', max_length=64, verbose_name='File Hash'),
        ),
        
        # Generate UUIDs for existing documents
        migrations.RunPython(generate_uuids, reverse_uuids),
        
        # Now add unique constraint to UUID
        migrations.AlterField(
            model_name='document',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Document UUID'),
        ),
        
        # Note: file_hash unique constraint will be added later after files are saved
        # For now, keep it non-unique to allow empty values
    ]