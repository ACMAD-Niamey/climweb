import hashlib
import json
import os
import re
import tempfile
from argparse import ArgumentTypeError
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from climweb.base.models import CustomDocumentModel, ProductCategory, ProductItemType
from climweb.pages.products.models import ProductItemPage, ProductPage, ProductSourceImport
from climweb.pages.products.tasks import _append_document_block


DEFAULT_CATALOG_URL = "https://rcc.acmad.org/dacadebulletin.php"
SOURCE_SYSTEM = "ACMAD RCC / SGBD THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Dekadal-Importer/1.0 (+https://new.acmad.org/)"
RANGE_CHUNK_SIZE = 8 * 1024 * 1024
MAX_PDF_SIZE = 50 * 1024 * 1024

DOCUMENT_SPECS = (
    {
        "key": "bulletin",
        "source_filename": "Bull_dek.pdf",
        "item_type": "Dekadal Climate Bulletin",
        "local_filename": "Dekadal_Climate_Bulletin",
    },
    {
        "key": "technical-note",
        "source_filename": "Dek_Tech_Note.pdf",
        "item_type": "Dekadal Technical Note",
        "local_filename": "Dekadal_Technical_Note",
    },
    {
        "key": "highlights",
        "source_filename": "HIGHLIHTS_DEKAD.pdf",
        "item_type": "Dekadal Highlights",
        "local_filename": "Dekadal_Highlights",
    },
)


def iso_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ArgumentTypeError(
            f"Expected an ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def canonical_source_url(url):
    """Store stable HTTPS provenance while fetching from ACMAD's HTTP endpoint."""
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="https", netloc="sgbd.acmad.org")
    return urlunparse(parsed)


def operational_url(url):
    parsed = urlparse(url)
    if parsed.hostname == "sgbd.acmad.org":
        parsed = parsed._replace(scheme="http", netloc="sgbd.acmad.org:8080")
    return urlunparse(parsed)


def versioned_source_url(source_url, issue_date):
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["acmad_issue"] = [issue_date.isoformat()]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def parse_catalog(html, catalog_url):
    """Find the three current Dekadal PDFs in the legacy RCC catalogue."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for anchor in soup.find_all("a", href=True):
        candidates.append(urljoin(catalog_url, anchor["href"]))

    for frame in soup.find_all("iframe", src=True):
        frame_url = urljoin(catalog_url, frame["src"])
        embedded_url = parse_qs(urlparse(frame_url).query).get("url", [])
        candidates.extend(embedded_url)

    documents = []
    for spec in DOCUMENT_SPECS:
        match = next(
            (
                candidate
                for candidate in candidates
                if os.path.basename(urlparse(candidate).path).lower()
                == spec["source_filename"].lower()
            ),
            None,
        )
        if match:
            documents.append({**spec, "source_url": canonical_source_url(match)})
    return documents


class Command(BaseCommand):
    help = "Import the current ACMAD Dekadal Climate Bulletin document set."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument(
            "--issue-date",
            type=iso_date,
            help="Override the issue date inferred from the bulletin Last-Modified header.",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        catalog_response = self._get(options["catalog_url"])
        documents = parse_catalog(catalog_response.text, options["catalog_url"])
        if not documents:
            raise CommandError(
                f"No current Dekadal PDFs were found at {options['catalog_url']}"
            )

        bulletin = next(
            (document for document in documents if document["key"] == "bulletin"),
            None,
        )
        if not bulletin:
            raise CommandError("The catalogue does not expose a current Dekadal bulletin")

        issue_date = options["issue_date"] or self._source_date(
            bulletin["source_url"]
        )
        for document in documents:
            document["date"] = issue_date
            document["provenance_url"] = versioned_source_url(
                document["source_url"], issue_date
            )

        self.stdout.write(
            f"Discovered {len(documents)} current document(s) for issue {issue_date}."
        )
        if options["dry_run"]:
            for document in documents:
                existing = ProductSourceImport.objects.filter(
                    source_url=document["provenance_url"]
                ).first()
                action = "REFRESH" if existing and options["refresh"] else (
                    "SKIP" if existing else "CREATE"
                )
                self.stdout.write(
                    f"{action} {document['item_type']} {document['source_url']}"
                )
            return

        product_page, item_types = self._get_or_create_destination()
        counts = {"created": 0, "refreshed": 0, "skipped": 0, "failed": 0}
        failures = []
        for document in documents:
            existing = ProductSourceImport.objects.filter(
                source_url=document["provenance_url"]
            ).first()
            if (
                existing
                and existing.status == ProductSourceImport.STATUS_IMPORTED
                and not options["refresh"]
            ):
                counts["skipped"] += 1
                self.stdout.write(
                    f"SKIP {document['item_type']} provenance #{existing.pk}"
                )
                continue

            try:
                action = self._import_document(
                    product_page,
                    item_types[document["key"]],
                    document,
                    existing,
                )
                counts[action] += 1
            except CommandError as exc:
                counts["failed"] += 1
                failures.append((document["item_type"], str(exc)))
                self._record_failure(product_page, document, existing, str(exc))
                self.stderr.write(
                    self.style.ERROR(f"FAILED {document['item_type']}: {exc}")
                )
                if not options["continue_on_error"]:
                    raise

        self.stdout.write(
            self.style.SUCCESS(
                "Dekadal bulletin migration complete: "
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
        if failures:
            raise CommandError(
                f"{len(failures)} document(s) failed: "
                + ", ".join(name for name, _ in failures)
            )

    def _get(self, url, **kwargs):
        try:
            response = requests.get(
                operational_url(url),
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise CommandError(f"Could not fetch {url}: {exc}") from exc

    def _source_date(self, source_url):
        url = operational_url(source_url)
        try:
            response = requests.head(
                url,
                timeout=(10, 60),
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            response.raise_for_status()
            last_modified = response.headers.get("Last-Modified")
            if not last_modified:
                response = requests.get(
                    url,
                    timeout=(10, 60),
                    headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"},
                    allow_redirects=True,
                )
                response.raise_for_status()
                last_modified = response.headers.get("Last-Modified")
        except requests.RequestException as exc:
            raise CommandError(f"Could not inspect {source_url}: {exc}") from exc
        if not last_modified:
            raise CommandError(
                f"No Last-Modified date was provided for {source_url}; use --issue-date"
            )
        try:
            return parsedate_to_datetime(last_modified).date()
        except (TypeError, ValueError) as exc:
            raise CommandError(
                f"Invalid Last-Modified date {last_modified!r} for {source_url}"
            ) from exc

    def _get_or_create_destination(self):
        product_page = ProductPage.objects.filter(
            slug="dekadal-weather-forecast"
        ).first()
        if not product_page:
            product_page = ProductPage.objects.filter(
                slug="dekadal-climate-bulletin"
            ).first()
        if not product_page:
            raise CommandError(
                "Neither the restored 'dekadal-weather-forecast' page nor a "
                "'dekadal-climate-bulletin' page was found"
            )

        product = product_page.product
        changed_fields = []
        if product.temporal_resolution != "dekadal":
            product.temporal_resolution = "dekadal"
            changed_fields.append("temporal_resolution")
        if not product.variable_name:
            product.variable_name = "dekadal-climate-bulletin"
            changed_fields.append("variable_name")
        if changed_fields:
            product.save(update_fields=changed_fields)

        category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Bulletin",
            defaults={"icon": "doc-full-inverse", "category_format": "pdf"},
        )
        if not category.category_format:
            category.category_format = "pdf"
            category.save(update_fields=["category_format"])

        item_types = {}
        for spec in DOCUMENT_SPECS:
            item_type, _ = ProductItemType.objects.get_or_create(
                category=category,
                name=spec["item_type"],
                defaults={
                    "file_name_convention": (
                        f"{spec['local_filename']}_{{yyyy}}{{mm}}{{dd}}"
                    ),
                    "valid_for_days": 10,
                },
            )
            item_types[spec["key"]] = item_type
        return product_page, item_types

    def _download_pdf(self, source_url):
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
                            operational_url(source_url),
                            timeout=(10, 60),
                            headers={
                                "User-Agent": USER_AGENT,
                                "Range": f"bytes={start}-{end}",
                            },
                            allow_redirects=True,
                        )
                        response.raise_for_status()
                    except requests.RequestException as exc:
                        raise CommandError(
                            f"Could not fetch PDF range {start}-{end} from "
                            f"{source_url}: {exc}"
                        ) from exc

                    content_range = response.headers.get("Content-Range", "")
                    match = re.match(r"bytes\s+(\d+)-(\d+)/(\d+)", content_range)
                    if response.status_code != 206 or not match:
                        raise CommandError(
                            f"Source did not honor byte ranges for {source_url} "
                            f"(HTTP {response.status_code})"
                        )
                    returned_start, returned_end, total = (
                        int(value) for value in match.groups()
                    )
                    if total > MAX_PDF_SIZE:
                        raise CommandError(
                            f"PDF exceeds the 50 MiB limit: {source_url}"
                        )
                    expected_size = returned_end - returned_start + 1
                    if returned_start != start or len(response.content) != expected_size:
                        raise CommandError(
                            f"Incomplete PDF range returned for {source_url}: "
                            f"{content_range}"
                        )
                    digest.update(response.content)
                    temp.write(response.content)
                    size += len(response.content)
                    start = returned_end + 1

            with open(temp.name, "rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise CommandError(f"Source did not return a PDF: {source_url}")
                handle.seek(-16, os.SEEK_END)
                if b"%%EOF" not in handle.read():
                    raise CommandError(f"PDF is incomplete: {source_url}")
            if total is None or size != total:
                raise CommandError(
                    f"Incomplete PDF download for {source_url}: {size} of {total}"
                )
            return temp.name, digest.hexdigest()
        except Exception:
            if os.path.exists(temp.name):
                os.unlink(temp.name)
            raise

    def _import_document(self, product_page, item_type, document_data, existing):
        temp_path, checksum = self._download_pdf(document_data["source_url"])
        issue_date = document_data["date"]
        valid_until = issue_date + timedelta(days=9)
        title = f"{document_data['item_type']} — {issue_date.isoformat()}"
        filename = (
            f"{document_data['local_filename']}_{issue_date.strftime('%Y%m%d')}.pdf"
        )
        page_title = f"Dekadal Climate Bulletin — {issue_date.isoformat()}"
        page_slug = slugify(page_title)
        try:
            with transaction.atomic():
                ProductPage.objects.select_for_update().get(pk=product_page.pk)
                current_import = ProductSourceImport.objects.filter(
                    source_url=document_data["provenance_url"]
                ).first()
                if current_import and not existing:
                    self.stdout.write(
                        f"SKIP {document_data['item_type']} imported concurrently"
                    )
                    return "skipped"

                page = ProductItemPage.objects.child_of(product_page).filter(
                    slug=page_slug
                ).first()
                if not page:
                    page = ProductItemPage(
                        title=page_title,
                        slug=page_slug,
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

                _append_document_block(
                    page, item_type.pk, issue_date, document, valid_until
                )
                page.refresh_from_db()
                page.title = page_title
                page.date = issue_date
                page.valid_until = valid_until
                page.save_revision().publish()

                ProductSourceImport.objects.update_or_create(
                    source_url=document_data["provenance_url"],
                    defaults={
                        "product": product_page.product,
                        "source_system": SOURCE_SYSTEM,
                        "source_published_date": issue_date,
                        "checksum_sha256": checksum,
                        "status": ProductSourceImport.STATUS_IMPORTED,
                        "error_message": "",
                        "attempt_count": existing.attempt_count + 1 if existing else 1,
                        "document": document,
                        "image": None,
                        "product_item_page": page,
                    },
                )
            action = "refreshed" if existing else "created"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{action.upper()} {document_data['item_type']} "
                    f"sha256={checksum[:12]}…"
                )
            )
            return action
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @staticmethod
    def _record_failure(product_page, document_data, existing, message):
        ProductSourceImport.objects.update_or_create(
            source_url=document_data["provenance_url"],
            defaults={
                "product": product_page.product,
                "source_system": SOURCE_SYSTEM,
                "source_published_date": document_data["date"],
                "checksum_sha256": existing.checksum_sha256 if existing else "",
                "status": ProductSourceImport.STATUS_FAILED,
                "error_message": message,
                "attempt_count": existing.attempt_count + 1 if existing else 1,
                "document": existing.document if existing else None,
                "image": None,
                "product_item_page": existing.product_item_page if existing else None,
            },
        )
