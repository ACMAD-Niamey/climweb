"""Helpers for resolving and inspecting configurable product sources."""

import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from django.db import OperationalError, ProgrammingError

from .import_registry import PRODUCT_IMPORTS_BY_KEY
from .models import ProductImportSourceConfig


CONFIG_FIELDS = (
    "source_type",
    "source_url",
    "source_system",
    "allowed_extensions",
    "filename_pattern",
    "date_format",
    "history_url_pattern",
    "request_headers",
)
INSPECTION_USER_AGENT = (
    "ACMAD-ClimWeb-Source-Inspector/1.0 (+https://new.acmad.org/)"
)


def get_product_import_source_values(family_key):
    definition = PRODUCT_IMPORTS_BY_KEY[family_key]
    values = dict(definition.get("source_defaults", {}))
    try:
        config = ProductImportSourceConfig.objects.get(product_family=family_key)
    except ProductImportSourceConfig.DoesNotExist:
        return values
    except (OperationalError, ProgrammingError):
        return values

    for field in CONFIG_FIELDS:
        values[field] = getattr(config, field)
    return values


def get_product_import_source_command_options(family_key):
    """Return a saved dashboard source as management-command options.

    Built-in command defaults remain authoritative until an administrator saves
    an override. This keeps restoration to defaults equivalent to deleting the
    database override.
    """
    definition = PRODUCT_IMPORTS_BY_KEY[family_key]
    option_name = definition.get("source_option")
    if not option_name:
        return {}
    try:
        source_url = ProductImportSourceConfig.objects.values_list(
            "source_url", flat=True
        ).get(product_family=family_key)
    except ProductImportSourceConfig.DoesNotExist:
        return {}
    except (OperationalError, ProgrammingError):
        return {}
    if definition.get("source_option_multiple"):
        source_url = [source_url]
    return {option_name: source_url}


def _request(url, headers):
    request_headers = {"User-Agent": INSPECTION_USER_AGENT, **headers}
    response = requests.get(url, timeout=(10, 60), headers=request_headers)
    response.raise_for_status()
    return response


def _extract_date(value, filename_pattern, date_format, fallback=None):
    match = re.search(filename_pattern, value, re.IGNORECASE)
    if match:
        try:
            return datetime.strptime(match.group("date"), date_format).date()
        except (ValueError, IndexError):
            return None
    if fallback:
        try:
            return datetime.fromisoformat(fallback.replace("Z", "+00:00")).date()
        except (TypeError, ValueError):
            return None
    return None


def _extension_allowed(url, allowed_extensions):
    extension = os.path.splitext(urlparse(url).path)[1].lower()
    return extension in set(allowed_extensions)


def _inspect_html(values):
    response = _request(values["source_url"], values.get("request_headers", {}))
    soup = BeautifulSoup(response.text, "html.parser")
    issues = []
    for anchor in soup.find_all("a", href=True):
        source_url = urljoin(values["source_url"], anchor["href"])
        if not _extension_allowed(source_url, values["allowed_extensions"]):
            continue
        issue_date = _extract_date(
            urlparse(source_url).path,
            values["filename_pattern"],
            values["date_format"],
        )
        if issue_date:
            issues.append({"date": issue_date, "source_url": source_url})
    return issues, 1


def _inspect_thredds(values):
    response = _request(values["source_url"], values.get("request_headers", {}))
    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid THREDDS XML catalogue: {exc}") from exc

    issues = []
    for dataset in root.iter():
        if not dataset.tag.endswith("dataset"):
            continue
        filename = dataset.get("name", "")
        source_path = dataset.get("urlPath", "")
        candidate = source_path or filename
        if not candidate or not _extension_allowed(
            candidate, values["allowed_extensions"]
        ):
            continue
        modified = None
        for child in dataset:
            if child.tag.endswith("date") and child.get("type") == "modified":
                modified = (child.text or "").strip()
                break
        issue_date = _extract_date(
            candidate,
            values["filename_pattern"],
            values["date_format"],
            fallback=modified,
        )
        if issue_date:
            issues.append(
                {
                    "date": issue_date,
                    "source_url": urljoin(values["source_url"], candidate),
                }
            )
    return issues, 1


def _inspect_wordpress(values):
    response = _request(values["source_url"], values.get("request_headers", {}))
    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise ValueError("The source did not return valid JSON") from exc
    if not isinstance(payload, list):
        raise ValueError("The WordPress media endpoint must return a JSON list")

    issues = []
    for media in payload:
        source_url = media.get("source_url", "")
        if not source_url or not _extension_allowed(
            source_url, values["allowed_extensions"]
        ):
            continue
        issue_date = _extract_date(
            urlparse(source_url).path,
            values["filename_pattern"],
            values["date_format"],
            fallback=media.get("date_gmt") or media.get("date"),
        )
        if issue_date:
            issues.append({"date": issue_date, "source_url": source_url})
    return issues, 1


def inspect_product_import_source(family_key, values, include_history=False):
    """Connect to a configured source and preview its matching dated files."""
    if family_key == "rainfall":
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
    elif family_key == "monthly-climate":
        from .management.commands.import_acmad_monthly_climate import Command

        assets = Command()._discover_assets(
            values["source_url"], include_history=include_history
        )
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = len({asset["date"].year for asset in assets})
    elif family_key == "season-onset":
        from .management.commands.import_acmad_season_onset import (
            Command,
            parse_catalog,
        )

        assets = parse_catalog(
            Command._request(values["source_url"]).content,
            values["source_url"],
        )
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = 1
    else:
        inspectors = {
            "html_archive": _inspect_html,
            "thredds_catalog": _inspect_thredds,
            "wordpress_api": _inspect_wordpress,
        }
        try:
            inspector = inspectors[values["source_type"]]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported source type: {values['source_type']}"
            ) from exc
        issues, archive_count = inspector(values)

    unique_issues = {
        (issue["date"], issue["source_url"]): issue for issue in issues
    }
    issues = sorted(
        unique_issues.values(), key=lambda issue: issue["date"], reverse=True
    )
    return {
        "archive_count": archive_count,
        "issues": issues[:20],
        "discovered_count": len(issues),
    }
