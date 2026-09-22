import io
import zipfile

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from wagtail.models import Collection
from wagtail.documents import get_document_model

from climweb.pages.services.climsoft_resources import CLIMSOFT_DOCUMENTS


MAX_DOCUMENT_BYTES = 25 * 1024 * 1024


def validate_document(content, filename):
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds the 25 MiB limit")
    if filename.endswith(".pdf"):
        if not content.startswith(b"%PDF-"):
            raise ValueError("source did not return a PDF")
        return
    if filename.endswith(".pptx"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile as exc:
            raise ValueError("source did not return a valid PowerPoint file") from exc
        if "[Content_Types].xml" not in names or "ppt/presentation.xml" not in names:
            raise ValueError("source did not return a valid PowerPoint file")
        return
    raise ValueError("unsupported document format")


class Command(BaseCommand):
    help = "Mirror the audited legacy RCC Climsoft manuals into the Wagtail document library."

    def handle(self, *args, **options):
        Document = get_document_model()
        collection = Collection.objects.filter(name="RCC Climsoft Resources").first()
        if not collection:
            collection = Collection.get_first_root_node().add_child(name="RCC Climsoft Resources")

        imported = 0
        failures = []
        for record in CLIMSOFT_DOCUMENTS:
            document = Document.objects.filter(
                Q(title=record["title"]) | Q(file__endswith=record["filename"])
            ).first()
            if document:
                document.tags.add("Climsoft", "RCC")
                if document.collection_id != collection.pk:
                    document.collection = collection
                    document.save(update_fields=["collection"])
                self.stdout.write(f"Already available: {record['title']}")
                continue
            try:
                response = requests.get(
                    record["source_url"], timeout=(15, 90),
                    headers={"User-Agent": "ACMAD-ClimWeb/1.0"}, allow_redirects=False,
                )
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError("source did not return a direct response")
                content = response.content
                validate_document(content, record["filename"])
                document = Document(title=record["title"], collection=collection)
                document.file.save(
                    f"climsoft/{record['filename']}", ContentFile(content), save=True,
                )
                document.tags.add("Climsoft", "RCC")
                imported += 1
                self.stdout.write(self.style.SUCCESS(f"Imported: {record['title']}"))
            except (requests.RequestException, ValueError) as exc:
                failures.append(record["title"])
                self.stderr.write(self.style.ERROR(f"Failed {record['title']}: {exc}"))
        if failures:
            raise CommandError(f"{len(failures)} Climsoft resource(s) failed to import.")
        self.stdout.write(self.style.SUCCESS(f"Climsoft resources ready: {imported} imported."))
