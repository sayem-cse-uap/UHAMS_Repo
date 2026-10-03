from django.core.management.base import BaseCommand, CommandError

from core.models import User
from staffs.models import StaffProfile


class Command(BaseCommand):
    help = (
        "Set the access level of a staff account (use this to create the FIRST "
        "manager/admin). Creates a StaffProfile if the STAFF user has none."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--level", choices=[c[0] for c in StaffProfile.ACCESS_CHOICES], default="admin")

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"No user named {options['username']!r}.")
        if user.role != User.Role.STAFF:
            raise CommandError(f"{user.username} has the {user.role} account type; only STAFF accounts can be promoted.")

        profile, created = StaffProfile.objects.get_or_create(
            user=user, defaults={"title": "Administrator", "department": "Administration", "role": "admin"}
        )
        profile.access_level = options["level"]
        profile.save(update_fields=["access_level"])
        self.stdout.write(self.style.SUCCESS(
            f"{user.username} is now '{options['level']}'" + (" (staff profile created)." if created else ".")
        ))
