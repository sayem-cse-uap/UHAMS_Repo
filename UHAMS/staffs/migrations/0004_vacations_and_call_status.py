import django.db.models.deletion
from django.db import migrations, models


def approved_flag_to_status(apps, schema_editor):
    VacationRecord = apps.get_model("staffs", "VacationRecord")
    VacationRecord.objects.filter(approved=True).update(status="approved")


def status_to_approved_flag(apps, schema_editor):
    VacationRecord = apps.get_model("staffs", "VacationRecord")
    VacationRecord.objects.filter(status="approved").update(approved=True)


class Migration(migrations.Migration):

    dependencies = [
        ("staffs", "0003_staff_fixes"),
    ]

    operations = [
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
        migrations.RunPython(approved_flag_to_status, status_to_approved_flag),
        migrations.RemoveField(model_name="vacationrecord", name="approved"),
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
