# -----------------------------------------------------------------------------
# MIGRATION  (staffs/migrations/0003_staff_fixes.py)
#
# What is a migration? Django records every change to the models as a small
# Python file like this one. `python manage.py migrate` runs the files that have
# not been applied yet, in dependency order, and turns them into SQL for the
# database (db.sqlite3). That is how the database tables stay in step with
# models.py.
#
# This one: clean-up of the staff app (hand-written, not auto-generated).
#   1. Data fix: converts the old free-text access_level values to one of the
#      allowed values (unrecognised text becomes 'staff').
#   2. Turns access_level into a field with fixed choices (staff / manager / admin).
#   3. Removes the duplicate staffs.Ambulance table and re-points
#      AmbulanceCall.ambulance at the real ambulances.Ambulance.
# Depends on ambulances 0001 so that the new target table already exists.
# -----------------------------------------------------------------------------
import django.db.models.deletion
from django.db import migrations, models


def normalize_access_levels(apps, schema_editor):
    """Free-text access levels become one of the new choices (unknown -> 'staff')."""
    # Inside a data migration we must use apps.get_model() (the historical
    # version of the model at this point in time), never import the real model.
    StaffProfile = apps.get_model("staffs", "StaffProfile")
    valid = {"staff", "manager", "admin"}   # the new allowed values
    for profile in StaffProfile.objects.all():
        value = (profile.access_level or "").strip().lower()   # e.g. " Manager " -> "manager"
        new_value = value if value in valid else "staff"
        if new_value != profile.access_level:
            profile.access_level = new_value
            profile.save(update_fields=["access_level"])


class Migration(migrations.Migration):

    # Must run after staffs 0002 and after the ambulances table exists.
    dependencies = [
        ("staffs", "0002_alter_staffprofile_options_staffprofile_role_and_more"),
        ("ambulances", "0001_initial"),
    ]

    operations = [
        # Step 1: fix the existing data first, so the stricter field below accepts it.
        # (RunPython.noop = nothing to undo when migrating backwards.)
        migrations.RunPython(normalize_access_levels, migrations.RunPython.noop),
        # Step 2: restrict access_level to the three choices, default "staff", max length 20.
        migrations.AlterField(
            model_name="staffprofile",
            name="access_level",
            field=models.CharField(
                choices=[("staff", "Staff"), ("manager", "Manager"), ("admin", "Administrator")],
                default="staff",
                max_length=20,
            ),
        ),
        # Step 3: staffs.Ambulance duplicated ambulances.Ambulance; calls now use the real one.
        # Drop the old link, delete the duplicate table, then add the new link
        # (ambulance calls that pointed at the old table lose that reference).
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
