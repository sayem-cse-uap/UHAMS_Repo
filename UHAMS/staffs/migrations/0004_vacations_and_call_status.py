# -----------------------------------------------------------------------------
# MIGRATION  (staffs/migrations/0004_vacations_and_call_status.py)
#
# What is a migration? Django records every change to the models as a small
# Python file like this one. `python manage.py migrate` runs the files that have
# not been applied yet, in dependency order, and turns them into SQL for the
# database (db.sqlite3). That is how the database tables stay in step with
# models.py.
#
# This one: vacation approval workflow and cancelled calls (hand-written).
#   1. VacationRecord gets `status` (pending/approved/rejected), `reviewed_by` and `reviewed_at`.
#   2. Existing rows are converted: approved=True  ->  status='approved'
#      (and the reverse function converts back if you ever migrate backwards).
#   3. The old yes/no `approved` column is removed.
#   4. AmbulanceCall.status gains a 'cancelled' choice.
# -----------------------------------------------------------------------------
import django.db.models.deletion
from django.db import migrations, models


def approved_flag_to_status(apps, schema_editor):
    # Forward data migration: rows that were approved under the old yes/no flag become status="approved".
    # (Everything else keeps the default status "pending".)
    VacationRecord = apps.get_model("staffs", "VacationRecord")
    VacationRecord.objects.filter(approved=True).update(status="approved")


def status_to_approved_flag(apps, schema_editor):
    # Reverse data migration: used only when migrating BACKWARDS, to restore the old flag.
    VacationRecord = apps.get_model("staffs", "VacationRecord")
    VacationRecord.objects.filter(status="approved").update(approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ("staffs", "0003_staff_fixes"),
    ]

    operations = [
        # Add the new columns first (status, reviewed_by, reviewed_at) ...
        migrations.AddField(
            model_name="vacationrecord",
            name="status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vacationrecord",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="staffs.staffprofile",
            ),
        ),
        migrations.AddField(
            model_name="vacationrecord",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # ... copy the old flag into the new status column ...
        migrations.RunPython(approved_flag_to_status, status_to_approved_flag),
        # ... and only then drop the old column.
        migrations.RemoveField(model_name="vacationrecord", name="approved"),
        # Allow the new "cancelled" status on emergency calls.
        migrations.AlterField(
            model_name="ambulancecall",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("dispatched", "Dispatched"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
