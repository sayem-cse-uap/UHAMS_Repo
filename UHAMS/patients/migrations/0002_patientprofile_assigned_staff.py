# -----------------------------------------------------------------------------
# MIGRATION  (patients/migrations/0002_patientprofile_assigned_staff.py)
#
# What is a migration? Django records every change to the models as a small
# Python file like this one. `python manage.py migrate` runs the files that have
# not been applied yet, in dependency order, and turns them into SQL for the
# database (db.sqlite3). That is how the database tables stay in step with
# models.py.
#
# This one: adds PatientProfile.assigned_staff (the staff member responsible for the
# patient). It depends on staffs 0001 because it points at staffs.StaffProfile.
# -----------------------------------------------------------------------------
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_initial"),
        ("staffs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="assigned_staff",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="patients",
                to="staffs.staffprofile",
            ),
        ),
    ]
