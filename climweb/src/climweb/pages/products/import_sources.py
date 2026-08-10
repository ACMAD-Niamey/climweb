"""Helpers for resolving and inspecting configurable product sources."""

from django.db import OperationalError, ProgrammingError

from .import_registry import PRODUCT_IMPORTS_BY_KEY
from .models import ProductImportSourceConfig


def get_product_import_source_values(family_key):
    definition = PRODUCT_IMPORTS_BY_KEY[family_key]
    values = dict(definition.get("source_defaults", {}))
    try:
        config = ProductImportSourceConfig.objects.get(product_family=family_key)
    except ProductImportSourceConfig.DoesNotExist:
        return values
    except (OperationalError, ProgrammingError):
        return values

    for field in (
        "source_type",
        "source_url",
        "source_system",
        "allowed_extensions",
        "filename_pattern",
        "date_format",
        "history_url_pattern",
        "request_headers",
    ):
        values[field] = getattr(config, field)
    return values


def inspect_product_import_source(family_key, values, include_history=False):
    if family_key != "rainfall":
        raise ValueError("Source inspection is not yet available for this importer")

    from .management.commands.import_acmad_daily_rainfall import Command

    command = Command()
    command.source_values = values
    issues, archive_count = command._discover_issues(
        values["source_url"],
        include_history=include_history,
        filename_pattern=values["filename_pattern"],
        date_format=values["date_format"],
        history_url_pattern=values["history_url_pattern"],
        allowed_extensions=values["allowed_extensions"],
    )
    issues.sort(key=lambda issue: issue["date"], reverse=True)
    return {
        "archive_count": archive_count,
        "issues": issues[:20],
        "discovered_count": len(issues),
    }
