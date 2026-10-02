import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('drivers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ambulance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ambulance_id', models.CharField(max_length=50, unique=True)),
                ('registration_number', models.CharField(max_length=50, unique=True)),
                ('model_name', models.CharField(blank=True, max_length=100)),
                ('vehicle_type', models.CharField(choices=[('BASIC', 'Basic Life Support (BLS)'), ('ADVANCED', 'Advanced Life Support (ALS)'), ('ICU', 'Mobile ICU'), ('NEONATAL', 'Neonatal'), ('TRANSPORT', 'Patient Transport')], default='BASIC', max_length=20)),
                ('capacity', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('status', models.CharField(choices=[('AVAILABLE', 'Available'), ('ON_TRIP', 'On Trip'), ('MAINTENANCE', 'Under Maintenance'), ('OFFLINE', 'Offline')], default='AVAILABLE', max_length=20)),
                ('equipment_notes', models.TextField(blank=True)),
                ('last_service_date', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('driver', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ambulance', to='drivers.driverprofile')),
            ],
            options={
                'ordering': ['ambulance_id'],
            },
        ),
    ]
