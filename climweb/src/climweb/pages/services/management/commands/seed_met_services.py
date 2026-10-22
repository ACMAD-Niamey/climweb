import json
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from wagtail.images import get_image_model
from wagtail.models import Page

from climweb.pages.flex_page.models import FlexPage
from climweb.pages.home.models import HomePage
from climweb.pages.services.models import MeteorologicalService


DIRECTORY_BLOCK_VALUE = {
    "heading": "African National Meteorological Services",
    "introduction": (
        "Explore the official meteorological and hydrological services serving countries across Africa."
    ),
    "show_search": True,
}


class Command(BaseCommand):
    help = "Seed the African meteorological services directory and optionally create its Flex Page."

    def add_arguments(self, parser):
        parser.add_argument("--create-page", action="store_true", help="Create the Met Services page if missing.")
        parser.add_argument(
            "--download-logos",
            action="store_true",
            help="Download sourced WMO logos into the Wagtail image library.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Refresh existing seeded records from the bundled inventory.",
        )
        parser.add_argument("--page-title", default="Met Services")

    def handle(self, *args, **options):
        data_path = Path(__file__).resolve().parents[2] / "data" / "african_met_services.json"
        inventory = json.loads(data_path.read_text(encoding="utf-8"))
        created_count = 0
        updated_count = 0

        for order, item in enumerate(inventory, start=1):
            defaults = {
                "country": item["country"],
                "name": item["name"],
                "acronym": item.get("acronym", ""),
                "website_url": item["website_url"],
                "logo_source_url": item.get("logo_source_url", ""),
                "order": order,
                "is_active": True,
            }
            service, created = MeteorologicalService.objects.get_or_create(
                wmo_member_id=item["wmo_member_id"], defaults=defaults
            )
            if created:
                created_count += 1
            elif options["update_existing"]:
                for field, value in defaults.items():
                    setattr(service, field, value)
                service.save(update_fields=[*defaults.keys()])
                updated_count += 1

            if options["download_logos"] and not service.logo and service.logo_source_url:
                self._download_logo(service)

        page = self._get_or_create_page(options["page_title"], options["create_page"])
        if page:
            self._ensure_directory_block(page)

        self.stdout.write(
            self.style.SUCCESS(
                f"Meteorological services ready: {created_count} created, {updated_count} updated, "
                f"{MeteorologicalService.objects.count()} total."
            )
        )

    def _get_or_create_page(self, title, create_page):
        matching_page = Page.objects.filter(title__iexact=title).first()
        if matching_page:
            specific = matching_page.specific
            if not isinstance(specific, FlexPage):
                self.stdout.write(
                    self.style.WARNING(
                        f'"{title}" exists as {specific.__class__.__name__}; the meteorological '
                        "services directory requires a Flex Page. The snippet inventory was seeded, "
                        "but the page was left unchanged."
                    )
                )
                return None
            return specific

        if not create_page:
            self.stdout.write(
                self.style.WARNING(
                    f'No "{title}" Flex Page found. Add one in Wagtail or rerun with --create-page.'
                )
            )
            return None

        home_page = HomePage.objects.live().first() or HomePage.objects.first()
        if not home_page:
            self.stdout.write(
                self.style.WARNING(
                    'No Home Page exists yet, so the "Met Services" page could not be created. '
                    "It will be created on a later application startup after the site is configured."
                )
            )
            return None

        page = FlexPage(
            title=title,
            slug=slugify(title),
            banner_title=title,
            banner_subtitle="Official national meteorological and hydrological services across Africa",
            content=[("met_services_directory", DIRECTORY_BLOCK_VALUE)],
        )
        home_page.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f'Created and published "{title}" at {page.url}.'))
        return page

    def _ensure_directory_block(self, page):
        if any(block.block_type == "met_services_directory" for block in page.content):
            return

        raw_content = list(page.content.raw_data)
        raw_content.append(
            {
                "type": "met_services_directory",
                "value": DIRECTORY_BLOCK_VALUE,
                "id": str(uuid.uuid4()),
            }
        )
        page.content = raw_content
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS("Added the directory block to the Met Services page."))

    def _download_logo(self, service):
        try:
            request = Request(service.logo_source_url, headers={"User-Agent": "ACMAD-ClimWeb/1.0"})
            with urlopen(request, timeout=20) as response:
                content = response.read()
            filename = Path(urlparse(service.logo_source_url).path).name or f"service-{service.pk}.png"
            image = get_image_model()(
                title=f"{service.country} meteorological service logo",
                file=ContentFile(content, name=f"met-services/{filename}"),
            )
            image.save()
            service.logo = image
            service.save(update_fields=["logo"])
            self.stdout.write(f"Downloaded logo: {service.country}")
        except Exception as exc:
            self.stderr.write(f"Logo download skipped for {service.country}: {exc}")
