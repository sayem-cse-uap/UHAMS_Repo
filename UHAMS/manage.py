#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

This is the entry point for every `python manage.py <command>` call you make
during development, for example:

    python manage.py runserver          # start the development web server
    python manage.py makemigrations     # turn model changes into migration files
    python manage.py migrate            # apply migrations to db.sqlite3
    python manage.py createsuperuser    # create a login for /admin/
    python manage.py promote_staff bob  # custom command (staffs/management/commands)

It does not contain any project logic itself; it only tells Django which
settings module to load and then hands the command line over to Django.
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # Tell Django where our settings live. setdefault() means that if the
    # DJANGO_SETTINGS_MODULE environment variable is already set (for example
    # on a server) we respect it instead of overriding it.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UHAMS.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # The most common reason: Django is not installed in the Python
        # environment you are using (or the virtualenv is not activated).
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    # sys.argv is the full command line, e.g. ['manage.py', 'runserver'].
    execute_from_command_line(sys.argv)


# Only run main() when the file is executed directly, not when imported.
if __name__ == '__main__':
    main()
