"""Helpers for resolving and inspecting configurable product sources."""

import os
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup
from django.db import OperationalError, ProgrammingError

from .import_registry import get_product_import_definition
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
    definition = get_product_import_definition(family_key)
    if definition is None:
        raise KeyError(family_key)
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
    definition = get_product_import_definition(family_key)
    if definition is None:
        raise KeyError(family_key)
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


def _inspect_html_page(values, page_url):
    response = _request(page_url, values.get("request_headers", {}))
    soup = BeautifulSoup(response.text, "html.parser")
    issues = []
    for anchor in soup.find_all("a", href=True):
        source_url = urljoin(page_url, anchor["href"])
        if not _extension_allowed(source_url, values["allowed_extensions"]):
            continue
        issue_date = _extract_date(
            urlparse(source_url).path,
            values["filename_pattern"],
            values["date_format"],
        )
        if issue_date:
            issues.append({"date": issue_date, "source_url": source_url})
    return issues, soup


def _inspect_html(values, include_history=False):
    issues, soup = _inspect_html_page(values, values["source_url"])
    archive_count = 1
    history_pattern = values.get("history_url_pattern")
    if include_history and history_pattern:
        archive_urls = []
        for anchor in soup.find_all("a", href=True):
            archive_url = urljoin(values["source_url"], anchor["href"])
            if re.search(history_pattern, archive_url, re.IGNORECASE):
                archive_urls.append(archive_url)
        for archive_url in list(dict.fromkeys(archive_urls))[:100]:
            archive_issues, _ = _inspect_html_page(values, archive_url)
            issues.extend(archive_issues)
            archive_count += 1
    return issues, archive_count


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
            if source_path:
                parsed = urlparse(values["source_url"])
                source_url = (
                    f"{parsed.scheme}://{parsed.netloc}/thredds/fileServer/"
                    f"{source_path.lstrip('/')}"
                )
            else:
                source_url = urljoin(values["source_url"], candidate)
            issues.append(
                {
                    "date": issue_date,
                    "source_url": source_url,
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


def inspect_product_import_source(
    family_key, values, include_history=False, preview_limit=20
):
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
    elif family_key == "climate-change":
        from .management.commands.import_acmad_climate_change import Command

        assets = Command()._discover_assets(values["source_url"])
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = 1
    elif family_key == "annual-climate":
        from .management.commands.import_acmad_annual_climate import Command

        assets = Command()._discover_assets(values["source_url"])
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = len({asset["year"] for asset in assets})
    elif family_key == "climate-watch":
        from .management.commands.import_acmad_climate_watch import Command

        assets = Command()._discover_assets(values["source_url"])
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = len({asset["date"].year for asset in assets})
    elif family_key == "rainfall-exceedance":
        from .management.commands.import_acmad_rainfall_exceedance import Command

        assets = Command()._discover_assets(values["source_url"])
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = len({asset["date"] for asset in assets})
    elif family_key == "five-day-rainfall":
        from .management.commands.import_acmad_five_day_rainfall import Command

        catalogs = Command()._discover_catalogs(values["source_url"])
        issues = [
            {"date": catalog["date"], "source_url": catalog["catalog_url"]}
            for catalog in catalogs
        ]
        archive_count = len(catalogs)
    elif family_key == "seasonal-verification":
        from .management.commands.import_acmad_seasonal_verification import Command

        assets = Command()._collect_assets({"source_url": values["source_url"]})
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = len({asset["date"].year for asset in assets})
    elif family_key == "model-performance":
        from .management.commands.import_acmad_model_performance import Command

        assets = Command()._collect_assets({"source_url": values["source_url"]})
        issues = [
            {"date": asset["date"], "source_url": asset["source_url"]}
            for asset in assets
        ]
        archive_count = len({asset["date"].year for asset in assets})
    elif family_key == "cryosphere":
        from .management.commands.import_acmad_cryosphere import Command

        assets = Command()._discover_assets(values["source_url"])
        issues = [{"date": asset["date"], "source_url": asset["source_url"]} for asset in assets]
        archive_count = len(issues)
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
        if values["source_type"] == "html_archive":
            issues, archive_count = inspector(
                values, include_history=include_history
            )
        else:
            issues, archive_count = inspector(values)

    unique_issues = {
        (issue["date"], issue["source_url"]): issue for issue in issues
    }
    issues = sorted(
        unique_issues.values(), key=lambda issue: issue["date"], reverse=True
    )
    return {
        "archive_count": archive_count,
        "issues": issues[:preview_limit] if preview_limit else issues,
        "discovered_count": len(issues),
    }
