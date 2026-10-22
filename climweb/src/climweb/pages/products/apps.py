from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'climweb.pages.products'

    def ready(self):
        from climweb.pages.products import import_progress  # noqa: F401
