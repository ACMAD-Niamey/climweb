from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'climweb.pages.organisation_pages.staff'

    def ready(self):
        from . import signals  # noqa: F401
