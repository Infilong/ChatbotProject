# Update DocumentUsage to reference new Document model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0003_update_document_reference'),
        ('documents', '0004_new_simple_document_system'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentusage',
            name='document',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_stats', to='documents.document', verbose_name='Document'),
        ),
    ]