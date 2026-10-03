import django.db.models.deletion
from django.db import migrations, models


def normalize_access_levels(apps, schema_editor):
    """Free-text access levels become one of the new choices (unknown -> 'staff')."""
    StaffProfile = apps.get_model("staffs", "StaffProfile")
    valid = {"staff", "manager", "admin"}
    for profile in StaffProfile.objects.all():
        value = (profile.access_level or "").strip().lower()
        new_value = value if value in valid else "staff"
        if new_value != profile.access_level:
            profile.access_level = new_value
            profile.save(update_fields=["access_level"])


class Migration(migrations.Migration):

    dependencies = [
        ("staffs", "0002_alter_staffprofile_options_staffprofile_role_and_more"),
        ("ambulances", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_access_levels, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="staffprofile",
            name="access_level",
            field=models.CharField(
                choices=[("staff", "Staff"), ("manager", "Manager"), ("admin", "Administrator")],
                default="staff",
                max_length=20,
            ),
        ),
        # staffs.Ambulance duplicated ambulances.Ambulance; calls now use the real one.
        migrations.RemoveField(model_name="ambulancecall", name="ambulance"),
        migrations.DeleteModel(name="Ambulance"),
        migrations.AddField(
            model_name="ambulancecall",
            name="ambulance",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="calls",
                to="ambulances.ambulance",
            ),
        ),
    ]
