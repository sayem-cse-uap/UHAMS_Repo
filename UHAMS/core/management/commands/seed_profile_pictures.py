"""
python manage.py seed_profile_pictures [--force]

Gives every demo user a different flower or plant as their profile picture.

  * The pictures are drawn by _flower_art.py and written to MEDIA_ROOT/profile_pictures/seed/
    (only if they are not there yet).
  * Users are taken in id order and each gets the next picture (see plant_for_position), so the
    first 51 users all have a different one.
  * Users who already have a picture - e.g. one they uploaded themselves - are left alone,
    unless you pass --force.

It is safe to run more than once.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import User
from . import _flower_art as art

SEED_DIR = 'profile_pictures/seed'


class Command(BaseCommand):
    help = "Assign a different flower/plant picture to every user (users with a picture are skipped)."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help="also replace pictures that users already have")

    def handle(self, *args, **options):
        folder = Path(settings.MEDIA_ROOT) / SEED_DIR
        folder.mkdir(parents=True, exist_ok=True)

        assigned = skipped = 0
        for position, user in enumerate(User.objects.order_by('id')):
            if user.profile_picture and not options['force']:
                skipped += 1
                continue
            index = art.plant_for_position(position)
            name = art.filename(index)
            if not (folder / name).exists():
                art.render(index).save(folder / name, optimize=True)
            user.profile_picture = f'{SEED_DIR}/{name}'
            user.save(update_fields=['profile_picture'])
            assigned += 1
            self.stdout.write(f"  {user.username:<20} {art.PLANTS[index]['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"Done: {assigned} picture(s) assigned, {skipped} user(s) already had one."))
