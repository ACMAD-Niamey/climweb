#!/usr/bin/env python3
"""Build a reviewable product migration inventory from the legacy ACMAD website.

This is deliberately read-only: it fetches public pages and writes CSV/Markdown
reports. It never connects to Django or changes Wagtail content.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


OUTPUT_DIR = Path(__file__).resolve().parent
CHECKED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
USER_AGENT = "ACMAD-ClimWeb-Migration-Audit/1.0 (+https://new.acmad.org/)"

SOURCE_PAGES = {
    "products_and_services": "https://acmad.org/index.php/products-and-services/",
    "flagship_products": "https://acmad.org/index.php/flagship-climate-services-products/",
    "data_center": "https://acmad.org/index.php/data-center-2/",
    "bulletins": "https://acmad.org/index.php/bulletins/",
    "climate_monitoring": "https://acmad.org/index.php/acmad-climate-monitoring/",
}

PRODUCT_HOSTS = {
    "acmad.org",
    "www.acmad.org",
    "sgbd.acmad.org",
    "rcc.acmad.org",
    "ada.acmad.org",
    "climserviceshub.acmad.org",
    "rcc-cmd.acmad.org",
    "acmad.net",
    "www.acmad.net",
    "web.csag.uct.ac.za",
}

NON_PRODUCT_LABELS = {
    "skip to content", "home", "homepage", "learn more", "archive", "archives",
    "search", "facebook", "twitter", "youtube", "contact-us", "contact us",
}

SERVICE_NAMES = {
    "NOWCASTING",
    "SHORT RANGE WEATHER FORECAST (D1,D2 AND D3)",
    "WEEKLY WEATHER FORECAST",
    "HEAT WAVE",
    "DATA SERVICE",
    "TRAINING SERVICE",
    "LONG RANGE FORECASTING SERVICE",
    "CLIMATE MONITORING SERVICES",
    "CLIMATE AND HELP SERVICE",
    "CLIMATE CHANGE SERVICE",
}


@dataclass
class InventoryRow:
    record_type: str
    source_catalogue: str
    source_name: str
    source_url: str
    source_system: str
    file_type: str
    frequency: str
    validity: str
    archive_url: str
    observed_issue_date: str
    link_status: str
    target_product_page: str
    target_category: str
    migration_method: str
    priority: str
    editorial_status: str
    notes: str


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" \t\r\n|,;:-")


def source_system(url: str) -> str:
    if not url:
        return "legacy WordPress catalogue only"
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"acmad.org", "www.acmad.org"}:
        return "Legacy ACMAD WordPress"
    if host == "sgbd.acmad.org":
        return "ACMAD SGBD/THREDDS"
    if host == "rcc.acmad.org":
        return "African RCC portal"
    if host == "ada.acmad.org":
        return "African Drought Advisory platform"
    if host == "climserviceshub.acmad.org":
        return "Climate Services Hub"
    if host == "rcc-cmd.acmad.org":
        return "RCC climate-model display"
    if host in {"acmad.net", "www.acmad.net"}:
        return "Legacy ACMAD operational host"
    return host or "unknown"


def infer_file_type(url: str, label: str) -> str:
    path = urlparse(url).path.lower()
    ext = Path(path).suffix.lstrip(".")
    if ext in {"pdf", "png", "jpg", "jpeg", "gif", "csv", "geojson", "zip", "nc", "tif", "tiff"}:
        return ext
    lower = label.lower()
    if "bulletin" in lower or "technical note" in lower or "statement" in lower:
        return "document or archive page"
    return "HTML/application"


def infer_observed_date(text: str) -> str:
    matches = re.findall(r"\b(20\d{2})[-_/](0[1-9]|1[0-2])[-_/]([0-2]\d|3[01])\b", text)
    return "-".join(matches[-1]) if matches else ""


def target_mapping(name: str) -> tuple[str, str, str, str]:
    n = name.lower()
    rules = [
        (("multi-hazard", "multihazard", "hazard outlook", "flood assessment", "strong wind"),
         "Continental Multi-Hazard Outlook", "Advisories and bulletins", "P0"),
        (("dekadal", "10-day", "10 days climate", "climate diagnostic", "dek3"),
         "Dekadal Climate Bulletin", "Bulletins and diagnostics", "P0"),
        (("drought",), "Continental Drought", "Drought monitoring and advisories", "P0"),
        (("policy", "decision maker", "information note"),
         "Policy and Decision Briefs", "Briefs and technical notes", "P0"),
        (("rapid developing thunderstorm", "rdt", "satellite imagery", "sat image", "convection"),
         "Thunderstorm and Nowcasting", "Nowcasting imagery", "P1"),
        (("itd", "itcz", "inter-tropical", "meridianal wind"),
         "ITD and ITCZ Monitoring", "Position and circulation analysis", "P1"),
        (("rainfall", "precipitation", "gsmap", "precip_likelihood"),
         "Daily Rainfall Monitoring", "Observation and forecast maps", "P1"),
        (("arpege", "ecm", "gfs", "ukmo", "dwd", "ensemble", "meteogram", "model output", "multimodel", "multimodele"),
         "Numerical Weather Forecasts", "Model guidance", "P1"),
        (("pressure", "geopotential", "relative humidity", "vorticity", "streamline", "steamline", "wind", "synoptic", "technote.pdf", "mslp", "rh_", "vor_", "z500", "climo 5-day"),
         "Atmospheric Analysis", "Synoptic analysis", "P1"),
        (("heat", "temperature", "discomfort", "hot days", "tmax", "tmin", "temp maximum", "temp minimum", "temp mean", "hi-40c"),
         "Heat and Thermal Stress", "Temperature and heat risk", "P1"),
        (("agric", "soil moisture", "vegetation", "onset", "cessation"),
         "Agriculture Climate Services", "Agricultural monitoring", "P2"),
        (("meningitis", "malaria", "health", "dust concentration", "air quality"),
         "Climate and Health", "Health risk products", "P2"),
        (("long range", "longerange", "seasonal", "presac", "presagg", "presass", "swiocof", "ghacof", "sarcof", "medcof", "ond", "ndj", "jfm", "djf"),
         "Seasonal and Long-Range Forecasts", "Outlooks and consensus statements", "P2"),
        (("climate change", "projection"),
         "Climate Change and Projections", "Projections", "P2"),
        (("climate monitoring", "climate indices", "climatolog", "state of the climate", "monthly climate", "rcc afrique"),
         "Climate Monitoring", "Diagnostics and reference data", "P2"),
    ]
    for terms, page, category, priority in rules:
        if any(term in n for term in terms):
            method = "synchronize" if priority in {"P0", "P1"} else "copy_or_link_after_review"
            return page, category, method, priority
    return "Needs editorial classification", "Unclassified", "editorial_review", "P3"


def looks_like_product_link(label: str, url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if "grid-list-toggle=" in parsed.query:
        return False
    if Path(parsed.path).suffix.lower() in {".mp4", ".webm", ".mov"}:
        return False
    if parsed.netloc.lower() not in PRODUCT_HOSTS:
        return False
    low_label = label.lower()
    if low_label in NON_PRODUCT_LABELS or low_label in {"<", ">"}:
        return False
    path = parsed.path.lower()
    return any((
        parsed.netloc.lower() not in {"acmad.org", "www.acmad.org"},
        "/wp-content/uploads/" in path,
        any(word in path for word in ("product", "bulletin", "climate", "forecast", "monitor", "outlook")),
    ))


def fetch_source(name: str, url: str) -> tuple[str, BeautifulSoup]:
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return name, BeautifulSoup(response.text, "html.parser")


def table_rows(catalogue: str, soup: BeautifulSoup) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    section = "product"
    for element in soup.find_all(["h2", "h3", "h4", "table"]):
        if element.name != "table":
            heading = clean_text(element.get_text(" ", strip=True)).lower()
            if "service" in heading and "product" not in heading:
                section = "service"
            elif "product" in heading:
                section = "product"
            continue
        for tr in element.find_all("tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
            if not cells or not cells[0] or cells[0].lower() in {"products name", "product name", "service name", "bulletin number", "services table"}:
                continue
            name = cells[0]
            if name.isdigit() and len(cells) > 1:
                name = cells[1]
            link = tr.find("a", href=True)
            url = urljoin(SOURCE_PAGES[catalogue], link["href"]) if link else ""
            if (not clean_text(name) or clean_text(name).isdigit() or clean_text(name).startswith("<")
                    or clean_text(name).lower() in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
                    or "grid-list-toggle=" in url):
                continue
            frequency = cells[1] if len(cells) > 1 and not cells[0].isdigit() else ""
            validity = cells[2] if len(cells) > 2 else ""
            page, category, method, priority = target_mapping(name)
            normalized_name = clean_text(name).upper()
            is_service = catalogue == "products_and_services" and normalized_name in SERVICE_NAMES
            if is_service:
                page, category, method, priority = "Not a /products/ page", "Service catalogue", "exclude_from_products", "P3"
            rows.append(InventoryRow(
                "service" if is_service else "product", catalogue, name, url, source_system(url), infer_file_type(url, name),
                frequency, validity, "", infer_observed_date(name + " " + url), "unchecked",
                page, category, method, priority, "needs_review",
                "Legacy table entry; authoritative status must be confirmed by the responsible department.",
            ))
    return rows


def linked_rows(catalogue: str, soup: BeautifulSoup) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    for anchor in soup.find_all("a", href=True):
        label = clean_text(anchor.get_text(" ", strip=True) or anchor.get("title", ""))
        url = urljoin(SOURCE_PAGES[catalogue], anchor["href"])
        if not label or not looks_like_product_link(label, url):
            continue
        if label.lower() in {"services", "nowcasting", "forecasting service"}:
            continue
        page, category, method, priority = target_mapping(label + " " + url)
        rows.append(InventoryRow(
            "product_link", catalogue, label, url, source_system(url), infer_file_type(url, label),
            "", "", "", infer_observed_date(label + " " + url), "unchecked",
            page, category, method, priority, "needs_review",
            "Linked product endpoint discovered in the legacy catalogue.",
        ))
    return rows


def audit_url(url: str) -> dict[str, str]:
    result = {
        "url": url, "status": "", "final_url": "", "content_type": "", "response_ms": "", "error": "",
    }
    started = datetime.now(timezone.utc)
    try:
        response = requests.get(
            url, timeout=(8, 18), headers={"User-Agent": USER_AGENT, "Range": "bytes=0-8191"},
            allow_redirects=True, stream=True,
        )
        result["status"] = str(response.status_code)
        result["final_url"] = response.url
        result["content_type"] = response.headers.get("Content-Type", "").split(";")[0]
        response.close()
    except requests.RequestException as exc:
        result["status"] = "ERROR"
        result["error"] = clean_text(str(exc))[:500]
    elapsed = datetime.now(timezone.utc) - started
    result["response_ms"] = str(round(elapsed.total_seconds() * 1000))
    return result


def deduplicate(rows: list[InventoryRow]) -> list[InventoryRow]:
    merged: dict[tuple[str, str], InventoryRow] = {}
    for row in rows:
        key = (clean_text(row.source_name).lower(), row.source_url.rstrip("/"))
        if key not in merged:
            merged[key] = row
        else:
            existing = merged[key]
            catalogues = sorted(set(existing.source_catalogue.split(";") + row.source_catalogue.split(";")))
            existing.source_catalogue = ";".join(catalogues)
    return sorted(merged.values(), key=lambda r: (r.priority, r.target_product_page, r.source_name.lower()))


def write_inventory(rows: list[InventoryRow]) -> None:
    path = OUTPUT_DIR / "acmad-product-inventory.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_link_audit(rows: list[InventoryRow], audits: dict[str, dict[str, str]]) -> None:
    references: dict[str, list[InventoryRow]] = defaultdict(list)
    for row in rows:
        if row.source_url:
            references[row.source_url].append(row)
    path = OUTPUT_DIR / "link-audit.csv"
    fields = ["url", "domain", "labels", "referenced_by", "status", "final_url", "content_type", "response_ms", "checked_at", "error"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for url in sorted(references):
            audit = audits[url]
            writer.writerow({
                "url": url,
                "domain": urlparse(url).netloc,
                "labels": " | ".join(sorted({r.source_name for r in references[url]})),
                "referenced_by": ";".join(sorted({r.source_catalogue for r in references[url]})),
                "status": audit["status"],
                "final_url": audit["final_url"],
                "content_type": audit["content_type"],
                "response_ms": audit["response_ms"],
                "checked_at": CHECKED_AT,
                "error": audit["error"],
            })


def write_taxonomy(rows: list[InventoryRow], audits: dict[str, dict[str, str]]) -> None:
    products = [row for row in rows if row.record_type != "service"]
    grouped: dict[str, list[InventoryRow]] = defaultdict(list)
    for row in products:
        grouped[row.target_product_page].append(row)
    ok = sum(1 for audit in audits.values() if audit["status"].isdigit() and int(audit["status"]) < 400)
    broken = len(audits) - ok
    lines = [
        "# Proposed ACMAD Product Taxonomy",
        "",
        f"Generated: {CHECKED_AT}",
        "",
        "## Audit summary",
        "",
        f"- Inventory records: {len(rows)}",
        f"- Product/product-link records: {len(products)}",
        f"- Unique linked endpoints checked: {len(audits)}",
        f"- Endpoints responding below HTTP 400: {ok}",
        f"- Endpoints broken, blocked, or timing out: {broken}",
        "",
        "This is a review proposal, not an import log. Similar legacy entries are intentionally consolidated into stable product families.",
        "",
        "## Proposed product families",
        "",
        "| Priority | Target ProductPage | Discovered records | Recommended handling |",
        "|---|---|---:|---|",
    ]
    for page, items in sorted(grouped.items(), key=lambda item: (min(r.priority for r in item[1]), item[0])):
        priority = min(row.priority for row in items)
        methods = ", ".join(sorted({row.migration_method for row in items}))
        lines.append(f"| {priority} | {page} | {len(items)} | {methods} |")
    lines.extend([
        "",
        "## Content-model mapping",
        "",
        "- **ProductPage:** one stable product family, not one page per model variable or file.",
        "- **ProductCategory:** a coherent format or subject grouping such as Bulletins, Observations, Forecast Maps, Technical Notes, or Data.",
        "- **ProductItemType:** the specific layer or component, for example ECMWF Precipitation, ITD Position, or Flood Assessment.",
        "- **ProductItemPage:** one issuance date containing all related images/documents for that issue.",
        "- **External application:** keep live dashboards external and add an explicit external-product link rather than copying their HTML.",
        "",
        "## Editorial decisions required",
        "",
        "1. Confirm which operational systems are authoritative and expected to remain online.",
        "2. Confirm whether ACCOF/PRESAC/SWIOCOF/GHACOF/SARCOF documents belong in Products or Publications.",
        "3. Assign an ACMAD owner to each P0/P1 product family.",
        "4. Confirm the historical cutoff date and whether all legacy files or only recent years should be copied.",
        "5. Confirm copyright/redistribution permission for partner-hosted products.",
        "6. Decide whether bilingual metadata is required during initial migration or as a second pass.",
        "",
        "## Recommended pilot",
        "",
        "Use **Continental Multi-Hazard Outlook** first. It already has a local ProductPage-equivalent, exposes a current archive, and exercises PDF, image, date, validity, archive, and scheduled-update behavior.",
        "",
        "## Source catalogues",
        "",
    ])
    lines.extend(f"- [{name}]({url})" for name, url in SOURCE_PAGES.items())
    (OUTPUT_DIR / "proposed-taxonomy.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[InventoryRow] = []
    for catalogue, url in SOURCE_PAGES.items():
        _, soup = fetch_source(catalogue, url)
        rows.extend(table_rows(catalogue, soup))
        rows.extend(linked_rows(catalogue, soup))
    rows = deduplicate(rows)

    urls = sorted({row.source_url for row in rows if row.source_url})
    audits: dict[str, dict[str, str]] = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(audit_url, url): url for url in urls}
        for future in as_completed(futures):
            audits[futures[future]] = future.result()

    for row in rows:
        if row.source_url:
            row.link_status = audits[row.source_url]["status"]
            content_type = audits[row.source_url]["content_type"]
            if content_type and row.file_type == "HTML/application":
                row.file_type = content_type

    write_inventory(rows)
    write_link_audit(rows, audits)
    write_taxonomy(rows, audits)
    print(f"Generated {len(rows)} inventory records and audited {len(urls)} unique links in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
