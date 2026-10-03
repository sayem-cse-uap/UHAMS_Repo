"""Who may change what on a staff profile. Used by the manager views and forms.

These are plain helper functions (no database access, no request object) so the
rules are easy to read and reuse in one place. `actor` is the StaffProfile of the
manager doing the editing; `target` is the StaffProfile being edited.

The rules in plain words:
  * Only an administrator may create or edit another administrator.
  * Nobody (not even an administrator) may change their OWN role, salary or
    access level - so you cannot give yourself a raise or promote yourself.
"""
from .models import StaffProfile


def allowed_access_levels(actor):
    """Access levels this manager may hand out. Only admins can create admins.

    Returns a list of (value, label) pairs ready to be used as form choices."""
    if actor.access_level == StaffProfile.ACCESS_ADMIN:
        return list(StaffProfile.ACCESS_CHOICES)
    # A plain manager sees "Staff" and "Manager" but not "Administrator".
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
