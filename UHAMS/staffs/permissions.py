"""Who may change what on a staff profile. Used by the manager views and forms."""
from .models import StaffProfile


def allowed_access_levels(actor):
    """Access levels this manager may hand out. Only admins can create admins."""
    if actor.access_level == StaffProfile.ACCESS_ADMIN:
        return list(StaffProfile.ACCESS_CHOICES)
    return [c for c in StaffProfile.ACCESS_CHOICES if c[0] != StaffProfile.ACCESS_ADMIN]


def can_manage_staff(actor, target):
    """A non-admin manager may not modify an administrator's profile at all."""
    return not (
        target.access_level == StaffProfile.ACCESS_ADMIN
        and actor.access_level != StaffProfile.ACCESS_ADMIN
    )


def can_edit_sensitive(actor, target):
    """Role, salary and access level: never your own, so nobody can raise their
    own pay or promote themselves."""
    return actor.pk != target.pk and can_manage_staff(actor, target)
