from django.contrib.auth.hashers import check_password, identify_hasher
from django.utils.crypto import constant_time_compare


def password_matches(user, raw_password):
    """
    Check a raw password against user.password.

    Accounts created before hashing was in place may still hold a plaintext
    password. Those are accepted ONLY when the stored value is not a recognised
    hash, and are re-hashed on the spot. A stored hash can never be used as the
    password itself.
    """
    stored = user.password or ""
    if not stored or stored.startswith("!"):  # empty / unusable password
        return False
    try:
        identify_hasher(stored)
    except ValueError:  # not a hash -> legacy plaintext value
        if constant_time_compare(raw_password, stored):
            user.set_password(raw_password)
            user.save(update_fields=["password"])
            return True
        return False
    return check_password(raw_password, stored)
