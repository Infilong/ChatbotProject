# Manual migration to remove ReferenceDocument table
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0008_adminprompt'),
    ]

    operations = [
        migrations.RunSQL(
            "DROP TABLE IF EXISTS chat_referencedocument;",
            reverse_sql="-- No reverse operation needed"
        ),
    ]