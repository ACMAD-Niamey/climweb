import hashlib
import json
import os
import re
import tempfile
from argparse import ArgumentTypeError
from collections import Counter
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from climweb.base.models import CustomDocumentModel, ProductCategory, ProductItemType
from climweb.pages.products.models import ProductItemPage, ProductPage, ProductSourceImport
from climweb.pages.products.tasks import _append_document_block


DEFAULT_ARCHIVE_URL = (
    "https://sgbd.acmad.org/thredds/fileServer/FIT/BRIEFING/ARCHIVE/"
    "Hazard_Outlook/archive_hazard_outlook.html"
)
SOURCE_SYSTEM = "ACMAD SGBD/THREDDS"
DATE_PATTERN = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
PDF_NAME_PATTERN = re.compile(r"Continental_Hazard_Outlook_(20\d{6})\.pdf$", re.IGNORECASE)
YEAR_ARCHIVE_PATTERN = re.compile(r"archive_hazard_outlook_20\d{2}\.html$", re.IGNORECASE)
USER_AGENT = "ACMAD-ClimWeb-MultiHazard-Importer/1.0 (+https://new.acmad.org/)"
RANGE_CHUNK_SIZE = 8 * 1024 * 1024


def operational_url(url):
    """Use the archive's working HTTP/8080 endpoint while retaining HTTPS provenance."""
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org" and parsed.scheme == "https":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def parse_archive(html, archive_url):
    soup = BeautifulSoup(html, "html.parser")
    issues = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        label = anchor.get_text(" ", strip=True)
        url = urljoin(archive_url, anchor["href"])
        filename_match = PDF_NAME_PATTERN.search(urlparse(url).path)
        if DATE_PATTERN.match(label):
            issue_date = date.fromisoformat(label)
        elif filename_match:
            issue_date = date.fromisoformat(
                f"{filename_match.group(1)[:4]}-{filename_match.group(1)[4:6]}-{filename_match.group(1)[6:]}"
            )
        else:
            continue
        if not filename_match or url in seen:
            continue
        seen.add(url)
        issues.append({"date": issue_date, "source_url": url})
    return sorted(issues, key=lambda issue: issue["date"], reverse=True)


def parse_year_archive_links(html, archive_url):
    """Return unique linked yearly archive indexes from the current index."""
    soup = BeautifulSoup(html, "html.parser")
    links = {
        urljoin(archive_url, anchor["href"])
        for anchor in soup.find_all("a", href=True)
        if YEAR_ARCHIVE_PATTERN.search(
            urlparse(urljoin(archive_url, anchor["href"])).path
        )
    }
    return sorted(links, reverse=True)


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(f"Expected an ISO date (YYYY-MM-DD), got {value!r}") from exc


class Command(BaseCommand):
    help = "Import dated Continental Multi-Hazard Outlook PDFs from ACMAD's public archive."

    def add_arguments(self, parser):
        parser.add_argument("--archive-url", default=DEFAULT_ARCHIVE_URL)
        parser.add_argument("--limit", type=int, default=3, help="Maximum newest issues to consider (default: 3).")
        parser.add_argument(
            "--include-history",
            action="store_true",
            help="Follow yearly archive indexes linked from the current archive.",
        )
        parser.add_argument(
            "--from-date",
            type=iso_date,
            help="Only consider issues on or after this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--to-date",
            type=iso_date,
            help="Only consider issues on or before this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--oldest-first",
            action="store_true",
            help="Process the selected date range from oldest to newest.",
        )
        parser.add_argument(
            "--inventory-only",
            action="store_true",
            help="Report discovered issues by year without accessing or changing ClimWeb content.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Report actions without downloading or writing.")
        parser.add_argument("--refresh", action="store_true", help="Redownload already tracked source URLs.")
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Attempt the rest of the batch after an issue fails, then return an error summary.",
        )
        parser.add_argument(
            "--retry-failures",
            action="store_true",
            help="Retry source URLs previously recorded as failed.",
        )
        parser.add_argument("--valid-days", type=int, default=5, help="Inclusive validity period (default: 5 days).")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if options["valid_days"] < 1:
            raise CommandError("--valid-days must be at least 1")
        if (
            options["from_date"]
            and options["to_date"]
            and options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        archive_url = options["archive_url"]
        issues, archive_count = self._discover_issues(
            archive_url, include_history=options["include_history"]
        )
        discovered_count = len(issues)
        if options["from_date"]:
            issues = [issue for issue in issues if issue["date"] >= options["from_date"]]
        if options["to_date"]:
            issues = [issue for issue in issues if issue["date"] <= options["to_date"]]
        issues.sort(key=lambda issue: issue["date"], reverse=not options["oldest_first"])
        filtered_count = len(issues)

        yearly_counts = Counter(issue["date"].year for issue in issues)
        self.stdout.write(
            f"Discovered {discovered_count} unique issues across {archive_count} archive page(s); "
            f"{filtered_count} match the selected date range."
        )
        self.stdout.write(
            "Issues by year: "
            + ", ".join(
                f"{year}={count}" for year, count in sorted(yearly_counts.items(), reverse=True)
            )
        )
        if options["inventory_only"]:
            return

        issues = issues[:options["limit"]]
        if not issues:
            raise CommandError(f"No dated PDF issues found at {archive_url}")
        self.stdout.write(
            f"Selected {len(issues)} issue(s), "
            f"{issues[0]['date']} through {issues[-1]['date']}."
        )

        product_page = ProductPage.objects.filter(slug="weather-watch-and-prediction-products").live().first()
        if not product_page:
            raise CommandError("Live ProductPage 'weather-watch-and-prediction-products' was not found")

        bulletin_category = ProductCategory.objects.filter(product=product_page.product, name="Bulletin").first()
        if not bulletin_category:
            raise CommandError("The destination product has no 'Bulletin' category")

        item_type = ProductItemType.objects.filter(
            category=bulletin_category, name="Continental Hazard Outlook PDF"
        ).first()
        if not item_type and not options["dry_run"]:
            item_type = ProductItemType.objects.create(
                category=bulletin_category,
                name="Continental Hazard Outlook PDF",
                valid_for_days=options["valid_days"],
            )
            self.stdout.write(self.style.SUCCESS(f"Created product item type #{item_type.pk}"))

        counts = {
            "created": 0,
            "skipped": 0,
            "would_create": 0,
            "refreshed": 0,
            "failed": 0,
            "known_failed": 0,
        }
        failures = []
        for issue in issues:
            existing = ProductSourceImport.objects.filter(source_url=issue["source_url"]).first()
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
                self.stdout.write(f"SKIP {issue['date']} already imported as provenance #{existing.pk}")
                continue
            if options["dry_run"]:
                action = "REFRESH" if existing else "CREATE"
                counts["would_create"] += 1
                self.stdout.write(f"{action} {issue['date']} {issue['source_url']}")
                continue

            try:
                result = self._import_issue(
                    product_page=product_page,
                    item_type=item_type,
                    issue=issue,
                    valid_days=options["valid_days"],
                    existing=existing,
                )
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
                "Multi-Hazard migration batch complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            failed_dates = ", ".join(str(issue_date) for issue_date, _ in failures)
            raise CommandError(
                f"{len(failures)} issue(s) failed after the remaining batch was attempted: "
                f"{failed_dates}"
            )

    def _discover_issues(self, archive_url, include_history=False):
        archive_response = self._get(operational_url(archive_url))
        archive_pages = [(archive_url, archive_response.text)]
        if include_history:
            for year_url in parse_year_archive_links(archive_response.text, archive_url):
                year_response = self._get(operational_url(year_url))
                archive_pages.append((year_url, year_response.text))

        issues_by_url = {}
        for page_url, html in archive_pages:
            for issue in parse_archive(html, page_url):
                issues_by_url[issue["source_url"]] = issue
        return list(issues_by_url.values()), len(archive_pages)

    @staticmethod
    def _record_failure(product_page, issue, existing, message):
        if existing and existing.status == ProductSourceImport.STATUS_IMPORTED:
            existing.error_message = message
            existing.attempt_count += 1
            existing.save(update_fields=["error_message", "attempt_count", "updated_at"])
            return

        ProductSourceImport.objects.update_or_create(
            source_url=issue["source_url"],
            defaults={
                "product": product_page.product,
                "source_system": SOURCE_SYSTEM,
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

    def _get(self, url, stream=False):
        try:
            response = requests.get(
                url,
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                stream=stream,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _download_pdf(self, source_url):
        url = operational_url(source_url)
        digest = hashlib.sha256()
        size = 0
        temp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            with temp:
                start = 0
                total = None
                while total is None or start < total:
                    end = start + RANGE_CHUNK_SIZE - 1
                    try:
                        response = requests.get(
                            url,
                            timeout=(10, 60),
                            headers={"User-Agent": USER_AGENT, "Range": f"bytes={start}-{end}"},
                            allow_redirects=True,
                        )
                        response.raise_for_status()
                    except requests.RequestException as exc:
                        raise CommandError(
                            f"Could not fetch PDF range {start}-{end} "
                            f"from {source_url}: {exc}"
                        ) from exc

                    content_range = response.headers.get("Content-Range", "")
                    match = re.match(r"bytes\s+(\d+)-(\d+)/(\d+)", content_range)
                    if response.status_code != 206 or not match:
                        raise CommandError(
                            f"Archive did not honor byte-range download for {source_url} "
                            f"(HTTP {response.status_code}, Content-Range={content_range!r})"
                        )
                    returned_start, returned_end, total = (int(value) for value in match.groups())
                    if returned_start != start or len(response.content) != returned_end - returned_start + 1:
                        raise CommandError(f"Incomplete PDF range returned for {source_url}: {content_range}")
                    if total > 50 * 1024 * 1024:
                        raise CommandError(f"PDF exceeds the 50 MiB pilot limit: {source_url}")
                    digest.update(response.content)
                    temp.write(response.content)
                    size += len(response.content)
                    start = returned_end + 1
            with open(temp.name, "rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise CommandError(f"Source did not return a PDF: {source_url}")
            if total is None or size != total:
                raise CommandError(f"Incomplete PDF download for {source_url}: received {size} of {total}")
            return temp.name, digest.hexdigest()
        except Exception:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            raise

    def _import_issue(self, product_page, item_type, issue, valid_days, existing):
        temp_path, checksum = self._download_pdf(issue["source_url"])
        issue_date = issue["date"]
        valid_until = issue_date + timedelta(days=valid_days - 1)
        filename = f"Continental_Hazard_Outlook_{issue_date.strftime('%Y%m%d')}.pdf"
        title = f"Continental Multi-Hazard Outlook — {issue_date.isoformat()}"
        slug = slugify(f"continental-multi-hazard-outlook-{issue_date.isoformat()}")
        try:
            with transaction.atomic():
                # Serialize imports for this destination. This closes the window where
                # two scheduled runs can both pass the provenance check while a PDF is
                # downloading and then create duplicate documents for the same issue.
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

                page = ProductItemPage.objects.child_of(product_page).filter(slug=slug).first()
                if not page:
                    page = ProductItemPage(
                        title=title,
                        slug=slug,
                        date=issue_date,
                        valid_until=valid_until,
                        products=json.dumps([]),
                    )
                    product_page.add_child(instance=page)

                document = existing.document if existing and existing.document else None
                with open(temp_path, "rb") as handle:
                    if document:
                        document.title = title
                        document.file.save(filename, File(handle), save=True)
                    else:
                        document = CustomDocumentModel(title=title)
                        document.file.save(filename, File(handle), save=True)

                _append_document_block(page, item_type.pk, issue_date, document, valid_until)
                page.refresh_from_db()
                page.title = title
                page.date = issue_date
                page.valid_until = valid_until
                page.save_revision().publish()

                ProductSourceImport.objects.update_or_create(
                    source_url=issue["source_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": SOURCE_SYSTEM,
                        "source_published_date": issue_date,
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": (existing.attempt_count + 1) if existing else 1,
                        "document": document,
                        "image": None,
                        "product_item_page": page,
                    },
                )
            action = "refreshed" if existing else "created"
            message = (
                f"{action.upper()} {issue_date} {filename} "
                f"sha256={checksum[:12]}…"
            )
            self.stdout.write(self.style.SUCCESS(message))
            return action
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
