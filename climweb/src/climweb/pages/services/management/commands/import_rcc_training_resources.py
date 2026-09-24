import io
import zipfile

import requests
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from wagtail.documents import get_document_model
from wagtail.models import Collection

from climweb.pages.services.training_resources import RCC_TRAINING_DOCUMENTS


MAX_DOCUMENT_BYTES = 40 * 1024 * 1024


def validate_document(content, filename):
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds the 40 MiB limit")
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
    help = "Mirror the audited legacy RCC training library into Wagtail Documents."

    def handle(self, *args, **options):
        Document = get_document_model()
        collection = Collection.objects.filter(name="RCC Training Resources").first()
        if not collection:
            collection = Collection.get_first_root_node().add_child(
                name="RCC Training Resources"
            )

        imported = 0
        failures = []
        for record in RCC_TRAINING_DOCUMENTS:
            if not record.get("source_available", True):
                self.stdout.write(
                    self.style.WARNING(
                        f"Legacy source unavailable; catalogue record retained: {record['title']}"
                    )
                )
                continue
            document = Document.objects.filter(
                Q(title=record["title"]) | Q(file__endswith=record["filename"])
            ).first()
            if document:
                document.tags.add("RCC", "Training", record["group"])
                if document.collection_id != collection.pk:
                    document.collection = collection
                    document.save(update_fields=["collection"])
                self.stdout.write(f"Already available: {record['title']}")
                continue

            try:
                response = requests.get(
                    record["source_url"],
                    timeout=(15, 120),
                    headers={"User-Agent": "ACMAD-ClimWeb/1.0"},
                    allow_redirects=False,
                )
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError("source did not return a direct response")
                validate_document(response.content, record["filename"])
                document = Document(title=record["title"], collection=collection)
                document.file.save(
                    f"rcc-training/{record['filename']}",
                    ContentFile(response.content),
                    save=True,
                )
                document.tags.add("RCC", "Training", record["group"])
                imported += 1
                self.stdout.write(self.style.SUCCESS(f"Imported: {record['title']}"))
            except (requests.RequestException, ValueError) as exc:
                failures.append(record["title"])
                self.stderr.write(self.style.ERROR(f"Failed {record['title']}: {exc}"))

        if failures:
            raise CommandError(
                f"{len(failures)} RCC training resource(s) failed to import: "
                + ", ".join(failures)
            )
        self.stdout.write(
            self.style.SUCCESS(f"RCC training resources ready: {imported} imported.")
        )
        call_command("seed_rcc_training", sync_resources=True, stdout=self.stdout)
