"""Persistent scheduling helpers for automatic product imports."""

import json

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from .import_registry import get_product_import_definition
from .models import ProductImportSchedule


def get_product_import_interval_hours(family_key, fallback=None):
    """Return a saved interval, falling back safely during initial migrations."""
    definition = get_product_import_definition(family_key)
    if definition is None:
        raise KeyError(family_key)
    if fallback is None:
        fallback = (
            definition.get("default_interval_hours", 24)
            if definition.get("is_configured")
            else getattr(settings, definition["interval_setting"], 24)
        )
    try:
        return ProductImportSchedule.objects.values_list(
            "interval_hours", flat=True
        ).get(product_family=family_key)
    except ProductImportSchedule.DoesNotExist:
        return fallback
    except (OperationalError, ProgrammingError):
        return fallback


def get_product_import_enabled(family_key, fallback=None):
    """Return a dashboard override or the deployment-level default."""
    definition = get_product_import_definition(family_key)
    if definition is None:
        raise KeyError(family_key)
    if fallback is None:
        fallback = (
            definition.get("default_enabled", False)
            if definition.get("is_configured")
            else getattr(settings, definition["enabled_setting"], False)
        )
    try:
        enabled_override = ProductImportSchedule.objects.values_list(
            "enabled_override", flat=True
        ).get(product_family=family_key)
    except ProductImportSchedule.DoesNotExist:
        return fallback
    except (OperationalError, ProgrammingError):
        return fallback
    return fallback if enabled_override is None else enabled_override


def sync_product_import_schedule(family_key, interval_hours, enabled=None):
    """Apply a saved interval to django-celery-beat immediately."""
    definition = get_product_import_definition(family_key)
    if definition is None:
        raise KeyError(family_key)
    if enabled is None:
        enabled = get_product_import_enabled(family_key)
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=interval_hours,
        period=IntervalSchedule.HOURS,
    )
    periodic_task, _ = PeriodicTask.objects.update_or_create(
        name=definition["periodic_task_name"],
        defaults={
            "task": definition["celery_task"],
            "args": json.dumps([family_key]) if definition.get("is_configured") else "[]",
            "interval": interval,
            "crontab": None,
            "solar": None,
            "clocked": None,
            "enabled": enabled,
            "one_off": False,
        },
    )
    return periodic_task
