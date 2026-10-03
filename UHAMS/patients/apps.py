from django.apps import AppConfig


class PatientsConfig(AppConfig):
    """Registers the `patients` app with Django (referenced as 'patients' in INSTALLED_APPS)."""
    name = 'patients'
