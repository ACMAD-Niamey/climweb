import hashlib
import json
import os
import re
import tempfile
from argparse import ArgumentTypeError
from collections import Counter
from datetime import date, datetime
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from PIL import Image as PillowImage
from wagtail.images import get_image_model

from climweb.base.models import Product, ProductCategory, ProductItemType, ServiceCategory
from climweb.pages.products.models import (
    ProductIndexPage,
    ProductItemPage,
    ProductPage,
    ProductSourceImport,
)
from climweb.pages.products.tasks import _append_image_block


DEFAULT_ARCHIVE_URL = (
    "https://sgbd.acmad.org/thredds/fileServer/ACMAD/WWFD/verificationservice/"
    "OBS/ARCHIVE/GSMAP/archive_gsmap.html"
)
SOURCE_SYSTEM = "ACMAD SGBD/THREDDS GSMaP"
PNG_NAME_PATTERN = re.compile(
    r"gsmap24_(?P<date>20\d{6})\.png$", re.IGNORECASE
)
YEAR_ARCHIVE_PATTERN = re.compile(r"archive_gsmap_20\d{2}\.html$", re.IGNORECASE)
USER_AGENT = "ACMAD-ClimWeb-Rainfall-Importer/1.0 (+https://new.acmad.org/)"
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def operational_url(url):
    """Use ACMAD's working HTTP/8080 endpoint while retaining HTTPS provenance."""
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org" and parsed.scheme == "https":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def parse_archive(
    html,
    archive_url,
    filename_pattern=PNG_NAME_PATTERN,
    date_format="%Y%m%d",
    allowed_extensions=(".png",),
):
    """Extract unique dated GSMaP PNGs from an ACMAD archive page."""
    if isinstance(filename_pattern, str):
        filename_pattern = re.compile(filename_pattern, re.IGNORECASE)
    allowed_extensions = {extension.lower() for extension in allowed_extensions}
    soup = BeautifulSoup(html, "html.parser")
    issues_by_url = {}
    for anchor in soup.find_all("a", href=True):
        source_url = urljoin(archive_url, anchor["href"])
        path = urlparse(source_url).path
        if os.path.splitext(path)[1].lower() not in allowed_extensions:
            continue
        match = filename_pattern.search(path)
        if not match:
            continue
        raw_date = match.groupdict().get("date") or match.group(1)
        try:
            issue_date = datetime.strptime(raw_date, date_format).date()
        except ValueError:
            continue
        issues_by_url[source_url] = {
            "date": issue_date,
            "source_url": source_url,
        }
    return sorted(
        issues_by_url.values(), key=lambda issue: issue["date"], reverse=True
    )


def parse_year_archive_links(
    html,
    archive_url,
    history_url_pattern=YEAR_ARCHIVE_PATTERN,
):
    if isinstance(history_url_pattern, str):
        history_url_pattern = re.compile(history_url_pattern, re.IGNORECASE)
    soup = BeautifulSoup(html, "html.parser")
    links = {
        urljoin(archive_url, anchor["href"])
        for anchor in soup.find_all("a", href=True)
        if history_url_pattern and history_url_pattern.search(
            urlparse(urljoin(archive_url, anchor["href"])).path
        )
    }
    return sorted(links, reverse=True)


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


class Command(BaseCommand):
    help = "Import dated daily GSMaP rainfall observation images from ACMAD."

    def add_arguments(self, parser):
        parser.add_argument("--archive-url")
        parser.add_argument(
            "--limit",
            type=int,
            default=7,
            help="Maximum newest issues to consider (default: 7).",
        )
        parser.add_argument("--include-history", action="store_true")
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")
        parser.add_argument("--retry-failures", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if (
            options["from_date"]
            and options["to_date"]
            and options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        from climweb.pages.products.import_sources import (
            get_product_import_source_values,
        )

        self.source_values = get_product_import_source_values("rainfall")
        archive_url = options["archive_url"] or self.source_values.get(
            "source_url", DEFAULT_ARCHIVE_URL
        )
        issues, archive_count = self._discover_issues(
            archive_url,
            options["include_history"],
            filename_pattern=self.source_values.get(
                "filename_pattern", PNG_NAME_PATTERN
            ),
            date_format=self.source_values.get("date_format", "%Y%m%d"),
            history_url_pattern=self.source_values.get(
                "history_url_pattern", YEAR_ARCHIVE_PATTERN
            ),
            allowed_extensions=self.source_values.get(
                "allowed_extensions", [".png"]
            ),
        )
        discovered_count = len(issues)
        if options["from_date"]:
            issues = [
                issue for issue in issues if issue["date"] >= options["from_date"]
            ]
        if options["to_date"]:
            issues = [
                issue for issue in issues if issue["date"] <= options["to_date"]
            ]
        issues.sort(
            key=lambda issue: issue["date"], reverse=not options["oldest_first"]
        )

        yearly_counts = Counter(issue["date"].year for issue in issues)
        self.stdout.write(
            f"Discovered {discovered_count} unique issues across {archive_count} "
            f"archive page(s); {len(issues)} match the selected date range."
        )
        self.stdout.write(
            "Issues by year: "
            + ", ".join(
                f"{year}={count}"
                for year, count in sorted(yearly_counts.items(), reverse=True)
            )
        )
        if options["inventory_only"]:
            return

        issues = issues[: options["limit"]]
        if not issues:
            raise CommandError(f"No dated GSMaP PNGs found at {archive_url}")
        self.stdout.write(
            f"Selected {len(issues)} issue(s), {issues[0]['date']} through "
            f"{issues[-1]['date']}."
        )

        if options["dry_run"]:
            for issue in issues:
                existing = ProductSourceImport.objects.filter(
                    source_url=issue["source_url"]
                ).first()
                action = "SKIP" if existing and not options["refresh"] else "CREATE"
                self.stdout.write(f"{action} {issue['date']} {issue['source_url']}")
            return

        product_page, item_type = self._get_or_create_destination()
        counts = {
            "created": 0,
            "skipped": 0,
            "refreshed": 0,
            "failed": 0,
            "known_failed": 0,
        }
        failures = []
        for issue in issues:
            existing = ProductSourceImport.objects.filter(
                source_url=issue["source_url"]
            ).first()
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_FAILED
                and not options["retry_failures"]
            ):
                counts["known_failed"] += 1
                self.stdout.write(
                    f"KNOWN FAILURE {issue['date']} provenance #{existing.pk}; "
                    "use --retry-failures to attempt it again"
                )
                continue
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_IMPORTED
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(
                    f"SKIP {issue['date']} already imported as provenance #{existing.pk}"
                )
                continue

            try:
                result = self._import_issue(product_page, item_type, issue, existing)
                counts[result] += 1
            except CommandError as exc:
                if not options["continue_on_error"]:
                    raise
                counts["failed"] += 1
                failures.append((issue["date"], str(exc)))
                self._record_failure(product_page, issue, existing, str(exc))
                self.stderr.write(self.style.ERROR(f"FAILED {issue['date']}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                "Daily rainfall migration batch complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            failed_dates = ", ".join(str(issue_date) for issue_date, _ in failures)
            raise CommandError(
                f"{len(failures)} issue(s) failed after the remaining batch was "
                f"attempted: {failed_dates}"
            )

    def _discover_issues(
        self,
        archive_url,
        include_history=False,
        filename_pattern=PNG_NAME_PATTERN,
        date_format="%Y%m%d",
        history_url_pattern=YEAR_ARCHIVE_PATTERN,
        allowed_extensions=(".png",),
    ):
        response = self._get(operational_url(archive_url))
        archive_pages = [(archive_url, response.text)]
        if include_history and history_url_pattern:
            for year_url in parse_year_archive_links(
                response.text, archive_url, history_url_pattern
            ):
                year_response = self._get(operational_url(year_url))
                archive_pages.append((year_url, year_response.text))

        issues_by_url = {}
        for page_url, html in archive_pages:
            for issue in parse_archive(
                html,
                page_url,
                filename_pattern=filename_pattern,
                date_format=date_format,
                allowed_extensions=allowed_extensions,
            ):
                issues_by_url[issue["source_url"]] = issue
        return list(issues_by_url.values()), len(archive_pages)

    def _get_or_create_destination(self):
        product, _ = Product.objects.get_or_create(
            name="Daily Rainfall Monitoring",
            defaults={
                "variable_name": "daily-rainfall-monitoring",
                "temporal_resolution": "daily",
            },
        )
        category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Observed Rainfall",
            defaults={"icon": "heavy-rain", "category_format": "png"},
        )
        item_type, _ = ProductItemType.objects.get_or_create(
            category=category,
            name="GSMaP 24-hour Satellite Rainfall",
            defaults={
                "file_name_convention": "gsmap24_{yyyy}{mm}{dd}",
                "valid_for_days": 1,
            },
        )

        product_page = ProductPage.objects.filter(
            slug="daily-rainfall-monitoring"
        ).first()
        if not product_page:
            index = ProductIndexPage.objects.live().first()
            if not index:
                raise CommandError("A live ProductIndexPage was not found")
            service = ServiceCategory.objects.filter(
                name="Weather Watch and Prediction"
            ).first()
            if not service:
                raise CommandError(
                    "Service category 'Weather Watch and Prediction' was not found"
                )
            product_page = ProductPage(
                title="Daily Rainfall Monitoring",
                slug="daily-rainfall-monitoring",
                service=service,
                product=product,
                introduction_title="Daily Rainfall Monitoring",
                introduction_text=(
                    "Daily satellite-derived rainfall estimates across Africa from "
                    "the Global Satellite Mapping of Precipitation (GSMaP) product."
                ),
                products_per_page=7,
            )
            index.add_child(instance=product_page)
            product_page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created Daily Rainfall Monitoring ProductPage #{product_page.pk}"
                )
            )
        return product_page, item_type

    def _record_failure(self, product_page, issue, existing, message):
        if existing and existing.status == ProductSourceImport.STATUS_IMPORTED:
            existing.error_message = message
            existing.attempt_count += 1
            existing.save(
                update_fields=["error_message", "attempt_count", "updated_at"]
            )
            return

        ProductSourceImport.objects.update_or_create(
            source_url=issue["source_url"],
            defaults={
                "product": product_page.product,
                "source_system": self.source_values.get(
                    "source_system", SOURCE_SYSTEM
                ),
                "source_published_date": issue["date"],
                "checksum_sha256": "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": (existing.attempt_count + 1) if existing else 1,
                "document": None,
                "image": None,
                "product_item_page": None,
            },
        )

    def _get(self, url):
        headers = {"User-Agent": USER_AGENT}
        headers.update(getattr(self, "source_values", {}).get("request_headers", {}))
        try:
            response = requests.get(
                url,
                timeout=(10, 60),
                headers=headers,
                allow_redirects=True,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _download_image(self, source_url):
        temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        digest = hashlib.sha256()
        size = 0
        try:
            try:
                headers = {"User-Agent": USER_AGENT}
                headers.update(
                    getattr(self, "source_values", {}).get("request_headers", {})
                )
                response = requests.get(
                    operational_url(source_url),
                    timeout=(10, 60),
                    headers=headers,
                    allow_redirects=True,
                    stream=True,
                )
                response.raise_for_status()
                with temp:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        size += len(chunk)
                        if size > MAX_IMAGE_SIZE:
                            raise CommandError(
                                f"Image exceeds the 10 MiB limit: {source_url}"
                            )
                        digest.update(chunk)
                        temp.write(chunk)
            except requests.RequestException as exc:
                raise CommandError(
                    f"Could not fetch rainfall image {source_url}: {exc}"
                ) from exc

            with PillowImage.open(temp.name) as image:
                image.verify()
                if image.format != "PNG":
                    raise CommandError(f"Source did not return a PNG: {source_url}")
            return temp.name, digest.hexdigest()
        except Exception as exc:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Invalid rainfall image {source_url}: {exc}") from exc

    def _import_issue(self, product_page, item_type, issue, existing):
        temp_path, checksum = self._download_image(issue["source_url"])
        issue_date = issue["date"]
        filename = f"gsmap24_{issue_date.strftime('%Y%m%d')}.png"
        title = f"GSMaP 24-hour Satellite Rainfall — {issue_date.isoformat()}"
        slug = f"daily-rainfall-monitoring-{issue_date.isoformat()}"
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                current_import = ProductSourceImport.objects.filter(
                    source_url=issue["source_url"]
                ).first()
                if current_import and not existing:
                    self.stdout.write(
                        f"SKIP {issue_date} imported concurrently as provenance "
                        f"#{current_import.pk}"
                    )
                    return "skipped"

                page = ProductItemPage.objects.child_of(product_page).filter(
                    slug=slug
                ).first()
                if not page:
                    page = ProductItemPage(
                        title=title,
                        slug=slug,
                        date=issue_date,
                        valid_until=issue_date,
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)

                Image = get_image_model()
                image = existing.image if existing and existing.image else None
                with open(temp_path, "rb") as handle:
                    if image:
                        image.title = title
                        image.file.save(filename, File(handle), save=True)
                    else:
                        image = Image(title=title)
                        image.file.save(filename, File(handle), save=True)

                _append_image_block(
                    page, item_type.pk, issue_date, image.pk, issue_date
                )
                page.refresh_from_db()
                page.title = title
                page.date = issue_date
                page.valid_until = issue_date
                page.save_revision().publish()

                ProductSourceImport.objects.update_or_create(
                    source_url=issue["source_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": self.source_values.get(
                            "source_system", SOURCE_SYSTEM
                        ),
                        "source_published_date": issue_date,
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": (
                            existing.attempt_count + 1 if existing else 1
                        ),
                        "document": None,
                        "image": image,
                        "product_item_page": page,
                    },
                )
            action = "refreshed" if existing else "created"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action.upper()} {issue_date} {filename} "
                    f"sha256={checksum[:12]}…"
                )
            )
            return action
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
