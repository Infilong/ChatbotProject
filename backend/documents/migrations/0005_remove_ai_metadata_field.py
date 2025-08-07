# Remove ai_metadata field from Document model
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_new_simple_document_system'),
    ]

    operations = [
        # Only remove the ai_metadata field from the existing Document model
        migrations.RemoveField(
            model_name='document',
            name='ai_metadata',
        ),
        
        # Drop the AI helper log table if it exists
        migrations.RunSQL(
            "DROP TABLE IF EXISTS documents_aidochelperlog;",
            reverse_sql="-- No reverse operation needed"
        ),
    ]