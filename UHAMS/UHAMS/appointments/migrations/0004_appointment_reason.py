from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0003_appointment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='reason',
            field=models.TextField(blank=True, default=''),
        ),
    ]
