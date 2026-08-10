"""Persistent scheduling helpers for automatic product imports."""

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .import_registry import PRODUCT_IMPORTS_BY_KEY
from .models import ProductImportSchedule


def get_product_import_interval_hours(family_key, fallback=None):
    """Return a saved interval, falling back safely during initial migrations."""
    definition = PRODUCT_IMPORTS_BY_KEY[family_key]
    if fallback is None:
        fallback = getattr(settings, definition["interval_setting"], 24)
    try:
        return ProductImportSchedule.objects.values_list(
            "interval_hours", flat=True
        ).get(product_family=family_key)
    except ProductImportSchedule.DoesNotExist:
        return fallback
    except (OperationalError, ProgrammingError):
        return fallback


def sync_product_import_schedule(family_key, interval_hours):
    """Apply a saved interval to django-celery-beat immediately."""
    definition = PRODUCT_IMPORTS_BY_KEY[family_key]
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=interval_hours,
        period=IntervalSchedule.HOURS,
    )
    periodic_task, _ = PeriodicTask.objects.update_or_create(
        name=definition["periodic_task_name"],
        defaults={
            "task": definition["celery_task"],
            "interval": interval,
            "crontab": None,
            "solar": None,
            "clocked": None,
            "enabled": True,
            "one_off": False,
        },
    )
    return periodic_task
