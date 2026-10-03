# -----------------------------------------------------------------------------
# MIGRATION  (appointments/migrations/0004_appointment_reason.py)
#
# What is a migration? Django records every change to the models as a small
# Python file like this one. `python manage.py migrate` runs the files that have
# not been applied yet, in dependency order, and turns them into SQL for the
# database (db.sqlite3). That is how the database tables stay in step with
# models.py.
#
# This one: adds Appointment.reason, the patient's free-text reason for the visit.
# -----------------------------------------------------------------------------
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
