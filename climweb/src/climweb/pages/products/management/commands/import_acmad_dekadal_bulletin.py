import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ElementTree
from argparse import ArgumentTypeError
from calendar import monthrange
from collections import Counter
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import (
    parse_qs,
    quote,
    unquote,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests
from bs4 import BeautifulSoup
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from climweb.base.models import CustomDocumentModel, ProductCategory, ProductItemType
from climweb.pages.products.models import ProductItemPage, ProductPage, ProductSourceImport
from climweb.pages.products.rcc import get_rcc_service_category
from climweb.pages.products.tasks import _append_document_block


DEFAULT_CATALOG_URL = "https://rcc.acmad.org/dacadebulletin.php"
DEFAULT_HISTORY_CATALOG_URL = (
    "https://sgbd.acmad.org/thredds/catalog/ACMAD/PROJECTS/CLIMSA/CDD/"
    "ACTIVITIES/SERVICES/Climate_monitoring/catalog.xml"
)
SOURCE_SYSTEM = "ACMAD RCC / SGBD THREDDS"
USER_AGENT = "ACMAD-ClimWeb-Dekadal-Importer/1.0 (+https://new.acmad.org/)"
RANGE_CHUNK_SIZE = 8 * 1024 * 1024
MAX_PDF_SIZE = 50 * 1024 * 1024
THREDDS_NAMESPACE = "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
MONTH_NUMBERS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "septembre": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

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
DOCUMENT_ORDER = {
    spec["key"]: position for position, spec in enumerate(DOCUMENT_SPECS)
}


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


def parse_thredds_catalog(xml, catalog_url):
    """Return child catalogues and file datasets from a THREDDS XML index."""
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid THREDDS XML at {catalog_url}: {exc}") from exc

    references = []
    for reference in root.findall(f".//{{{THREDDS_NAMESPACE}}}catalogRef"):
        href = reference.get(f"{{{XLINK_NAMESPACE}}}href")
        if not href:
            continue
        references.append(
            {
                "title": reference.get(f"{{{XLINK_NAMESPACE}}}title", ""),
                "catalog_url": canonical_source_url(urljoin(catalog_url, href)),
            }
        )

    datasets = []
    file_server_root = "https://sgbd.acmad.org/thredds/fileServer/"
    for dataset in root.findall(f".//{{{THREDDS_NAMESPACE}}}dataset"):
        url_path = dataset.get("urlPath")
        if not url_path:
            continue
        datasets.append(
            {
                "name": dataset.get("name", os.path.basename(url_path)),
                "source_url": urljoin(file_server_root, quote(url_path, safe="/()")),
            }
        )
    return references, datasets


def infer_history_issue_date(source_url):
    """Infer the represented dekad end date from a THREDDS path or filename."""
    decoded_path = unquote(urlparse(source_url).path)
    filename = os.path.basename(decoded_path)

    def extract(value):
        year_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", value)
        month_match = re.search(
            r"(?i)(?<![a-z])(" + "|".join(MONTH_NUMBERS) + r")(?![a-z])",
            value,
        )
        dekad_match = re.search(r"(?i)dek(?:ad)?[_\s-]*([123])(?!\d)", value)
        if not (year_match and month_match and dekad_match):
            return None
        year = int(year_match.group(1))
        month = MONTH_NUMBERS[month_match.group(1).lower()]
        dekad = int(dekad_match.group(1))
        day = {1: 10, 2: 20}.get(dekad, monthrange(year, month)[1])
        return date(year, month, day)

    return extract(filename) or extract(decoded_path)


def history_document_from_dataset(dataset):
    """Classify a dated bulletin-related PDF from a THREDDS dataset."""
    source_url = canonical_source_url(dataset["source_url"])
    decoded_path = unquote(urlparse(source_url).path).lower()
    if not decoded_path.endswith(".pdf"):
        return None
    if "tech" in decoded_path:
        key = "technical-note"
    elif "high" in decoded_path:
        key = "highlights"
    elif "bulletin" in decoded_path or re.search(r"(?:^|[/_])bull", decoded_path):
        key = "bulletin"
    else:
        return None

    issue_date = infer_history_issue_date(source_url)
    if not issue_date:
        return None
    spec = next(spec for spec in DOCUMENT_SPECS if spec["key"] == key)
    return {
        **spec,
        "date": issue_date,
        "source_url": source_url,
        "provenance_url": source_url,
        "is_history": True,
    }


class Command(BaseCommand):
    help = "Import the current ACMAD Dekadal Climate Bulletin document set."

    def add_arguments(self, parser):
        parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL)
        parser.add_argument(
            "--history-catalog-url", default=DEFAULT_HISTORY_CATALOG_URL
        )
        parser.add_argument(
            "--issue-date",
            type=iso_date,
            help="Override the issue date inferred from the bulletin Last-Modified header.",
        )
        parser.add_argument(
            "--include-history",
            action="store_true",
            help="Recursively discover dated PDFs in the THREDDS archive.",
        )
        parser.add_argument(
            "--history-only",
            action="store_true",
            help="Exclude the current fixed-name documents; implies --include-history.",
        )
        parser.add_argument("--from-date", type=iso_date)
        parser.add_argument("--to-date", type=iso_date)
        parser.add_argument(
            "--limit",
            type=int,
            default=3,
            help="Maximum issue dates to process when importing history (default: 3).",
        )
        parser.add_argument("--oldest-first", action="store_true")
        parser.add_argument("--inventory-only", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--refresh", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("--limit must be at least 1")
        if (
            options["from_date"]
            and options["to_date"]
            and options["from_date"] > options["to_date"]
        ):
            raise CommandError("--from-date cannot be later than --to-date")

        documents = []
        if not options["history_only"]:
            documents.extend(self._discover_current(options))
        if options["include_history"] or options["history_only"]:
            history, catalog_count, duplicate_count, catalog_error_count = (
                self._discover_history(
                    options["history_catalog_url"],
                    options["from_date"],
                    options["to_date"],
                )
            )
            documents.extend(history)
            self.stdout.write(
                f"Scanned {catalog_count} historical catalog(s); found "
                f"{len(history)} unique document(s) and suppressed "
                f"{duplicate_count} duplicate type/date entries; "
                f"{catalog_error_count} stale catalog link(s) were skipped."
            )

        if options["from_date"]:
            documents = [
                document
                for document in documents
                if document["date"] >= options["from_date"]
            ]
        if options["to_date"]:
            documents = [
                document
                for document in documents
                if document["date"] <= options["to_date"]
            ]

        documents_by_url = {
            document["provenance_url"]: document for document in documents
        }
        documents = list(documents_by_url.values())
        if options["oldest_first"]:
            documents.sort(
                key=lambda document: (
                    document["date"],
                    DOCUMENT_ORDER[document["key"]],
                )
            )
        else:
            documents.sort(
                key=lambda document: (
                    -document["date"].toordinal(),
                    DOCUMENT_ORDER[document["key"]],
                )
            )

        history_requested = options["include_history"] or options["history_only"]
        if history_requested and not options["inventory_only"]:
            issue_dates = sorted(
                {document["date"] for document in documents},
                reverse=not options["oldest_first"],
            )[: options["limit"]]
            documents = [
                document for document in documents if document["date"] in issue_dates
            ]

        if not documents:
            raise CommandError("No Dekadal documents matched the selected options")

        yearly_counts = Counter(document["date"].year for document in documents)
        issue_count = len({document["date"] for document in documents})
        self.stdout.write(
            f"Selected {len(documents)} document(s) across {issue_count} issue(s)."
        )
        self.stdout.write(
            "Documents by year: "
            + ", ".join(
                f"{year}={count}"
                for year, count in sorted(yearly_counts.items(), reverse=True)
            )
        )
        if options["inventory_only"]:
            return

        if options["dry_run"]:
            for document in documents:
                existing = ProductSourceImport.objects.filter(
                    source_url=document["provenance_url"]
                ).first()
                action = "REFRESH" if existing and options["refresh"] else (
                    "SKIP" if existing else "CREATE"
                )
                self.stdout.write(
                    f"{action} {document['date']} {document['item_type']} "
                    f"{document['source_url']}"
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

    def _discover_current(self, options):
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
            document["is_history"] = False
        return documents

    def _discover_history(self, root_catalog_url, from_date=None, to_date=None):
        pending = [canonical_source_url(root_catalog_url)]
        visited = set()
        documents = {}
        duplicate_count = 0
        catalog_error_count = 0
        minimum_year = from_date.year if from_date else None
        maximum_year = to_date.year if to_date else None

        while pending:
            catalog_url = pending.pop()
            if catalog_url in visited:
                continue
            visited.add(catalog_url)
            try:
                response = self._get(catalog_url)
            except CommandError as exc:
                catalog_error_count += 1
                self.stderr.write(self.style.WARNING(f"SKIP CATALOG {exc}"))
                continue
            try:
                references, datasets = parse_thredds_catalog(
                    response.content, catalog_url
                )
            except ValueError as exc:
                raise CommandError(str(exc)) from exc

            for dataset in datasets:
                document = history_document_from_dataset(dataset)
                if not document:
                    continue
                issue_date = document["date"]
                if from_date and issue_date < from_date:
                    continue
                if to_date and issue_date > to_date:
                    continue
                identity = (issue_date, document["key"])
                if identity in documents:
                    duplicate_count += 1
                    if document["source_url"] < documents[identity]["source_url"]:
                        documents[identity] = document
                else:
                    documents[identity] = document

            for reference in references:
                if self._history_catalog_is_relevant(
                    reference,
                    minimum_year,
                    maximum_year,
                ):
                    pending.append(reference["catalog_url"])

        return (
            list(documents.values()),
            len(visited),
            duplicate_count,
            catalog_error_count,
        )

    @staticmethod
    def _history_catalog_is_relevant(reference, minimum_year, maximum_year):
        decoded = unquote(reference["catalog_url"]).lower()
        title = reference["title"].lower()
        if any(
            excluded in decoded
            for excluded in (
                "/monthly/",
                "/drought_product/",
                "/product/",
                "/products/",
                "/new directory/",
                "/doc_dek/",
            )
        ):
            return False

        year_match = re.search(r"/climate_monitoring/(20\d{2})(?:/|$)", decoded)
        if not year_match:
            return title.isdigit()
        year = int(year_match.group(1))
        if minimum_year and year < minimum_year:
            return False
        if maximum_year and year > maximum_year:
            return False
        return True

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

        rcc_service = get_rcc_service_category()
        if product_page.service_id != rcc_service.pk:
            product_page.service = rcc_service
            product_page.save_revision().publish()

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
