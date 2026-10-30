import mimetypes
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from wagtail.documents import get_document_model
from wagtail.images import get_image_model

from climweb.pages.cop.models import CopEditionPage, CopIndexPage, CopSideEventPage


SOURCE_BASE = "https://old.acmad.org"
COP29_URL = f"{SOURCE_BASE}/index.php/cop29/"
HERO_URL = f"{SOURCE_BASE}/wp-content/uploads/2024/10/ACMAD-at-COP_29-1024x576.png"
SIDE_EVENT_1_CONCEPT_URL = (
    f"{SOURCE_BASE}/wp-content/uploads/2019/03/"
    "ACMAD_Concept-Note_-Side-Event_DRR_COP29-2-1.pdf"
)
SCHEDULES = (
    (
        "COP29 side-events schedule - Week 1",
        f"{SOURCE_BASE}/wp-content/uploads/2019/03/Week1_COP29_Agenda.pdf",
    ),
    (
        "COP29 side-events schedule - Week 2",
        f"{SOURCE_BASE}/wp-content/uploads/2019/03/Week2_COP29_Agenda.pdf",
    ),
)

# Dates and times are frozen from the archived event pages. Side event 6's page
# omits its date; the archived week-one programme identifies it as 16 November.
EVENT_TIMES = {
    1: ("2024-11-11 12:00", "2024-11-11 13:30"),
    2: ("2024-11-11 18:30", "2024-11-11 20:00"),
    3: ("2024-11-13 11:15", "2024-11-13 13:30"),
    4: ("2024-11-15 16:00", "2024-11-15 17:30"),
    5: ("2024-11-16 14:00", "2024-11-16 15:30"),
    6: ("2024-11-16 14:00", "2024-11-16 15:30"),
    7: ("2024-11-16 14:00", "2024-11-16 15:30"),
    8: ("2024-11-18 14:30", "2024-11-18 16:00"),
    9: ("2024-11-20 16:00", "2024-11-20 16:50"),
    10: ("2024-11-19 14:00", "2024-11-19 15:30"),
    11: ("2024-11-22 14:00", "2024-11-22 15:30"),
}

PANELISTS = {
    1: [
        ("Dr Kamoru Abiodun Lawal", "ACMAD", "", "speaker"),
        ("Dr Seydou Traore", "AGRHYMET", "", "speaker"),
        ("Dr Jolly Wasambo", "African Union Commission", "", "speaker"),
        ("Mr Zachary Atheru", "ICPAC", "", "speaker"),
    ],
    2: [
        ("Dr Philip Omondi", "ICPAC", "Project Manager", "moderator"),
        ("Mohamud Khadar", "Ministry of Environment and Climate Change, Somalia", "", "speaker"),
        ("Benedicte Giaever", "NORCAP", "Executive Director", "speaker"),
        ("Dr Sarra Touzi", "GWP", "Senior Water and Climate Specialist", "speaker"),
        ("Kamoru A. Lawal", "ACMAD", "Senior Climate Change Expert", "speaker"),
        (
            "Mr Zachary K. K. Atheru",
            "ICPAC",
            "Programme Manager, Climate Diagnostics and Prediction",
            "speaker",
        ),
    ],
}

ALLOWED_RICH_TEXT_TAGS = {
    "p", "ul", "ol", "li", "strong", "b", "em", "i", "u", "a", "br",
    "h2", "h3", "h4",
}


class Command(BaseCommand):
    help = "Import COP29 and its archived side events from the previous ACMAD website."

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Refresh fields and media references on an existing COP29 edition.",
        )

    def handle(self, *args, **options):
        self.replace = options["replace"]
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ACMAD ClimWeb COP29 content migration/1.0",
        })

        index = CopIndexPage.objects.live().first() or CopIndexPage.objects.first()
        if not index:
            raise CommandError("Create the COP landing page before importing COP29.")

        index_soup = self._fetch_soup(COP29_URL)
        edition = self._upsert_edition(index, index_soup)
        self._import_side_events(edition, index_soup)

        self.stdout.write(self.style.SUCCESS(
            f"COP29 import complete: {edition.url} ({edition.side_events.count()} side events)"
        ))

    def _fetch_soup(self, url):
        response = self.session.get(url, timeout=90)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _upsert_edition(self, index, soup):
        root = soup.select_one('[data-elementor-type="wp-page"]')
        if not root:
            raise CommandError("The archived COP29 page has no Elementor content root.")

        values = {
            "acmad_participation": self._widget_html_containing(root, "ACMAD will participate"),
            "about": self._strip_leading_label(
                self._widget_html_containing(root, "About COP 29"),
                {"about cop 29"},
            ),
            "objectives": self._strip_leading_label(
                self._widget_html_containing(root, "Objectives"),
                {"objectives"},
            ),
            "expected_outcomes": self._strip_leading_label(
                self._widget_html_containing(root, "Expected outcomes"),
                {"expected outcomes", "expected outcomes:"},
            ),
        }
        if not values["acmad_participation"]:
            raise CommandError("Could not locate the COP29 participation statement.")

        hero = self._download_image(HERO_URL, "ACMAD at COP29")
        schedule_documents = []
        for title, url in SCHEDULES:
            document = self._download_document(url, title)
            if document:
                schedule_documents.append(("document", {
                    "title": title,
                    "document": document,
                    "description": "Archived ACMAD COP29 side-event programme",
                }))

        edition = CopEditionPage.objects.child_of(index).filter(slug="cop29").first()
        if edition and not self.replace:
            self.stdout.write("COP29 already exists; use --replace to refresh it.")
            return edition.specific

        fields = {
            "title": "COP 29",
            "slug": "cop29",
            "cop_number": 29,
            "is_current": False,
            "start_date": datetime(2024, 11, 11).date(),
            "end_date": datetime(2024, 11, 22).date(),
            "host_city": "Baku",
            "host_country": "Azerbaijan",
            "official_website_url": "https://unfccc.int/cop29",
            "hero_image": hero,
            "primary_color": "#08777a",
            "secondary_color": "#ff9700",
            "accent_color": "#eaf5f5",
            "text_on_primary_color": "#ffffff",
            "schedule_documents": schedule_documents,
            **values,
        }

        if edition:
            edition = edition.specific
            for field, value in fields.items():
                setattr(edition, field, value)
        else:
            edition = CopEditionPage(**fields)
            index.add_child(instance=edition)

        edition.save_revision().publish()
        self.stdout.write(f"Imported COP29 edition: {edition.url}")
        return edition

    def _import_side_events(self, edition, index_soup):
        old_links = {
            int(match.group(1)): anchor.get("href")
            for anchor in index_soup.select('a[href*="/side-event-"]')
            if (match := re.search(r"/side-event-(\d+)/", anchor.get("href", "")))
        }
        for number in sorted(old_links):
            soup = self._fetch_soup(old_links[number])
            self._upsert_side_event(edition, number, soup)

    def _upsert_side_event(self, edition, number, soup):
        root = soup.select_one('[data-elementor-type="wp-page"]')
        if not root:
            self.stderr.write(f"Skipping side event {number}: content root missing")
            return

        heading = root.select_one(".elementor-headline-plain-text")
        title = self._clean_text(heading.get_text(" ", strip=True)) if heading else f"Side event {number}"
        metadata = next(
            (
                node.get_text(" ", strip=True)
                for node in root.select(".elementor-widget-text-editor .elementor-widget-container")
                if "Where:" in node.get_text(" ", strip=True)
            ),
            "",
        )
        venue_match = re.search(r"Where:\s*(.*?)(?:\s*[–-]\s*When\s*:)", metadata, re.I)
        venue = self._clean_text(venue_match.group(1)) if venue_match else "COP29 venue"

        content = self._main_content_widget(root)
        summary, description = self._split_summary(content, title)
        concept_note = None
        presentations = []
        additional_documents = []

        for anchor in root.select("a.elementor-button[href]"):
            label = self._clean_text(anchor.get_text(" ", strip=True))
            url = anchor.get("href", "")
            if not url or not self._looks_like_document_link(url, label):
                continue
            if "concept" in label.lower():
                concept_note = self._download_document(url, f"COP29 side event {number} - Concept note")
                continue
            document = self._download_document(url, f"COP29 side event {number} - {label}")
            if not document:
                continue
            item = ("presentation" if "presentation" in label.lower() else "document", {
                "title": label or document.title,
                "document": document,
                "description": "",
            })
            if item[0] == "presentation":
                presentations.append(item)
            else:
                additional_documents.append(item)

        if number == 1 and not concept_note:
            concept_note = self._download_document(
                SIDE_EVENT_1_CONCEPT_URL,
                "COP29 side event 1 - Concept note",
            )

        gallery = []
        seen_images = set()
        for image_node in root.select(".elementor-widget-image-carousel img"):
            url = self._best_image_url(image_node)
            if not url or url in seen_images:
                continue
            seen_images.add(url)
            image = self._download_image(url, f"COP29 side event {number} gallery {len(gallery) + 1}")
            if image:
                gallery.append(("image", {
                    "image": image,
                    "caption": image_node.get("alt", ""),
                    "credit": "ACMAD",
                }))

        panelists = [
            ("panelist", {
                "name": name,
                "organisation": organisation,
                "position": position,
                "role": role,
                "topic_title": "",
                "bio": "",
            })
            for name, organisation, position, role in PANELISTS.get(number, [])
        ]

        start, end = EVENT_TIMES[number]
        baku_timezone = ZoneInfo("Asia/Baku")
        fields = {
            "title": title,
            "slug": f"side-event-{number}",
            "side_event_number": number,
            "start_datetime": datetime.strptime(start, "%Y-%m-%d %H:%M").replace(tzinfo=baku_timezone),
            "end_datetime": datetime.strptime(end, "%Y-%m-%d %H:%M").replace(tzinfo=baku_timezone),
            "timezone": "Asia/Baku",
            "venue": venue,
            "summary": summary,
            "description": description,
            "concept_note": concept_note,
            "presentations": presentations,
            "additional_documents": additional_documents,
            "panelists": panelists,
            "gallery": gallery,
            "featured_image": gallery[0][1]["image"] if gallery else None,
        }

        page = CopSideEventPage.objects.child_of(edition).filter(slug=fields["slug"]).first()
        if page and not self.replace:
            self.stdout.write(f"Side event {number} already exists; skipped.")
            return
        if page:
            page = page.specific
            for field, value in fields.items():
                setattr(page, field, value)
        else:
            page = CopSideEventPage(**fields)
            edition.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(
            f"Imported side event {number}: {len(gallery)} images, "
            f"{len(presentations) + len(additional_documents) + int(bool(concept_note))} documents"
        )

    def _widget_html_containing(self, root, phrase):
        for node in root.select(".elementor-widget-text-editor .elementor-widget-container"):
            if phrase.lower() in node.get_text(" ", strip=True).lower():
                return self._sanitize_rich_text(node)
        return ""

    def _main_content_widget(self, root):
        candidates = []
        for node in root.select(".elementor-widget-text-editor .elementor-widget-container"):
            text = node.get_text(" ", strip=True)
            if "Where:" in text or len(text) < 40:
                continue
            candidates.append((len(text), node))
        return max(candidates, default=(0, None), key=lambda item: item[0])[1]

    def _split_summary(self, node, title):
        if not node:
            return f"<p>ACMAD participated in the COP29 side event: {title}.</p>", ""
        fragment = BeautifulSoup(str(node), "html.parser")
        first_paragraph = fragment.find("p")
        if not first_paragraph:
            html = self._sanitize_rich_text(fragment)
            return html or f"<p>{title}</p>", ""
        summary = self._sanitize_rich_text(first_paragraph)
        first_paragraph.extract()
        return summary, self._sanitize_rich_text(fragment)

    def _sanitize_rich_text(self, node):
        fragment = BeautifulSoup(str(node), "html.parser")
        for tag in list(fragment.find_all(True)):
            if tag.name not in ALLOWED_RICH_TEXT_TAGS:
                tag.unwrap()
                continue
            if tag.name == "a" and tag.get("href"):
                tag.attrs = {"href": tag["href"]}
            else:
                tag.attrs = {}
        return "".join(str(child) for child in fragment.contents).strip()

    def _looks_like_document_link(self, url, label):
        path = urlparse(url).path.lower()
        return (
            "drive.google.com" in url
            or Path(path).suffix in {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
            or any(word in label.lower() for word in ("concept", "presentation", "document"))
        )

    def _download_document(self, url, title):
        Document = get_document_model()
        existing = Document.objects.filter(title=title).first()
        if existing:
            return existing
        response = self._download_response(url)
        if not response:
            return None
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if "text/html" in content_type:
            self.stderr.write(f"Skipped document returned as HTML: {url}")
            return None
        extension = Path(unquote(urlparse(response.url).path)).suffix.lower()
        if not extension:
            extension = ".pdf" if "drive.google.com" in url else (mimetypes.guess_extension(content_type) or ".pdf")
        file_name = f"{slugify(title)[:100]}{extension}"
        document = Document(title=title)
        document.file.save(file_name, ContentFile(response.content), save=True)
        return document

    def _download_image(self, url, title):
        Image = get_image_model()
        existing = Image.objects.filter(title=title).first()
        if existing:
            return existing
        response = self._download_response(url)
        if not response:
            return None
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if not content_type.startswith("image/"):
            self.stderr.write(f"Skipped non-image response: {url}")
            return None
        extension = Path(unquote(urlparse(response.url).path)).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            extension = mimetypes.guess_extension(content_type) or ".jpg"
        content_file = ContentFile(
            response.content,
            name=f"{slugify(title)[:100]}{extension}",
        )
        return Image.objects.create(title=title, file=content_file)

    def _download_response(self, url):
        request_url = url
        drive_match = re.search(r"drive\.google\.com/file/d/([^/]+)", url)
        if drive_match:
            request_url = f"https://drive.google.com/uc?export=download&id={drive_match.group(1)}"
        try:
            response = self.session.get(request_url, timeout=120, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            self.stderr.write(f"Download failed for {url}: {exc}")
            return None

    def _best_image_url(self, node):
        srcset = node.get("srcset", "")
        if srcset:
            return srcset.split(",")[-1].strip().split(" ")[0]
        return node.get("data-lazy-src") or node.get("src")

    def _clean_text(self, value):
        return re.sub(r"\s+", " ", value or "").strip(" \u00a0–-")

    def _strip_leading_label(self, html, labels):
        if not html:
            return html
        fragment = BeautifulSoup(html, "html.parser")
        first = fragment.find(recursive=False)
        if first and self._clean_text(first.get_text(" ", strip=True)).lower() in labels:
            first.decompose()
        return str(fragment)

