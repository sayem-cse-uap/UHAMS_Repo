"""
core.security - password checking used by login and "change password".

Why not just call Django's `authenticate()`? This project signs users in with
its own session key instead of Django's built-in login (see core/views.py),
so it needs its own small helper for verifying a password. The helper also
quietly upgrades very old accounts whose password was once stored as plain text.
"""
from django.contrib.auth.hashers import check_password, identify_hasher
from django.utils.crypto import constant_time_compare


def password_matches(user, raw_password):
    """
    Check a raw password against user.password.

    Accounts created before hashing was in place may still hold a plaintext
    password. Those are accepted ONLY when the stored value is not a recognised
    hash, and are re-hashed on the spot. A stored hash can never be used as the
    password itself.

    Returns True/False. Never raises for a wrong password.
    """
    stored = user.password or ""

    # Django marks an account that has no usable password (e.g. created without
    # one) by storing an empty string or a value starting with "!". Nobody can
    # log in to those, so refuse straight away.
    if not stored or stored.startswith("!"):  # empty / unusable password
        return False

    try:
        # identify_hasher() succeeds if `stored` looks like "pbkdf2_sha256$...",
        # i.e. a real Django password hash, and raises ValueError otherwise.
        identify_hasher(stored)
    except ValueError:  # not a hash -> legacy plaintext value
        # The stored value is not a hash, so it must be an old plaintext
        # password. Compare it using constant_time_compare, which takes the
        # same time whether the first or last character differs (this prevents
        # timing attacks that guess a password character by character).
        if constant_time_compare(raw_password, stored):
            # Correct password: replace the plaintext with a proper hash now,
            # so the weak value only has to be accepted once.
            user.set_password(raw_password)
            user.save(update_fields=["password"])
            return True
        return False

    # Normal case: the stored value is a proper hash. check_password() hashes
    # the typed password the same way and compares the two safely.
    return check_password(raw_password, stored)
