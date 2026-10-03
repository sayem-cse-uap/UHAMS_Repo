"""
Custom management command:   python manage.py promote_staff <username> [--level admin]

THE CHICKEN-AND-EGG PROBLEM THIS SOLVES
  Only managers/admins can register staff accounts or change access levels
  (see staffs/views.py), so on a brand-new database nobody is a manager yet.
  This command, run from the server's terminal, makes the FIRST manager/admin.

Any file in `management/commands/` that defines a class called `Command` becomes
a manage.py sub-command named after the file.
"""
from django.core.management.base import BaseCommand, CommandError

from core.models import User
from staffs.models import StaffProfile


class Command(BaseCommand):
    help = (
        "Set the access level of a staff account (use this to create the FIRST "
        "manager/admin). Creates a StaffProfile if the STAFF user has none."
    )

    def add_arguments(self, parser):
        """Declare the command-line arguments."""
        parser.add_argument("username")   # required positional argument
        # --level is optional, limited to the valid access levels, default "admin".
        parser.add_argument("--level", choices=[c[0] for c in StaffProfile.ACCESS_CHOICES], default="admin")

    def handle(self, *args, **options):
        """Runs when the command is executed."""
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            # CommandError prints a clean message and exits with a non-zero code.
            raise CommandError(f"No user named {options['username']!r}.")
        if user.role != User.Role.STAFF:
            raise CommandError(f"{user.username} has the {user.role} account type; only STAFF accounts can be promoted.")

        # get_or_create: reuse the existing profile, or build a minimal one
        # (with the `defaults`) if this STAFF account never had one.
        profile, created = StaffProfile.objects.get_or_create(
            user=user, defaults={"title": "Administrator", "department": "Administration", "role": "admin"}
        )
        profile.access_level = options["level"]
        profile.save(update_fields=["access_level"])
        self.stdout.write(self.style.SUCCESS(
            f"{user.username} is now '{options['level']}'" + (" (staff profile created)." if created else ".")
        ))
