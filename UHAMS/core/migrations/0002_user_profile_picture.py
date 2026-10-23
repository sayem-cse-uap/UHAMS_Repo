# -----------------------------------------------------------------------------
# MIGRATION  (core/migrations/0002_user_profile_picture.py)
#
# What is a migration? Django records every change to the models as a small
# Python file like this one. `python manage.py migrate` runs the files that have
# not been applied yet, in dependency order, and turns them into SQL for the
# database (db.sqlite3). That is how the database tables stay in step with
# models.py.
#
# This one: adds the optional `profile_picture` column to the User table, so every
# user can upload their own picture. Existing users get an empty value, which the
# site displays as the default placeholder avatar until a picture is uploaded
# (the `seed_profile_pictures` command can give the demo users flower pictures).
# -----------------------------------------------------------------------------

import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='profile_picture',
            field=models.ImageField(blank=True, upload_to=core.models.profile_picture_path),
        ),
    ]
