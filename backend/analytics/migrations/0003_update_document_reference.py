# Update DocumentUsage to reference SmartDocument instead of CompanyDocument
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_alter_analyticssummary_options_and_more'),
        ('documents', '0003_new_document_system'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentusage',
            name='document',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_stats', to='documents.smartdocument', verbose_name='Document'),
        ),
    ]