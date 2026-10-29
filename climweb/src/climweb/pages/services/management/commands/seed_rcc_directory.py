import uuid

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from wagtail.models import Page

from climweb.pages.flex_page.models import FlexPage
from climweb.pages.home.models import HomePage


DIRECTORY_BLOCK_VALUE = {
    "heading": "African Regional Climate Centres",
    "introduction": (
        "Explore the Regional Climate Centres coordinating climate services across Africa."
    ),
    "show_search": True,
}


class Command(BaseCommand):
    help = "Create the dashboard-managed Regional Climate Centres directory page."

    def add_arguments(self, parser):
        parser.add_argument("--create-page", action="store_true")
        parser.add_argument("--page-title", default="Regional Climate Centres")

    def handle(self, *args, **options):
        title = options["page_title"]
        page = self._get_or_create_page(title, options["create_page"])
        if page:
            self._ensure_directory_block(page)

    def _get_or_create_page(self, title, create_page):
        matching_page = Page.objects.filter(title__iexact=title).first()
        if matching_page:
            specific = matching_page.specific
            if not isinstance(specific, FlexPage):
                self.stdout.write(
                    self.style.WARNING(
                        f'"{title}" exists as {specific.__class__.__name__}; the RCC directory requires a Flex Page.'
                    )
                )
                return None
            return specific

        if not create_page:
            self.stdout.write(self.style.WARNING(f'No "{title}" Flex Page found.'))
            return None

        home_page = HomePage.objects.live().first() or HomePage.objects.first()
        if not home_page:
            self.stdout.write(self.style.WARNING("No Home Page exists; the RCC directory was not created."))
            return None

        page = FlexPage(
            title=title,
            slug=slugify(title),
            banner_title=title,
            banner_subtitle="Regional climate coordination and services across Africa",
            content=[("rcc_directory", DIRECTORY_BLOCK_VALUE)],
        )
        home_page.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f'Created and published "{title}" at {page.url}.'))
        return page

    def _ensure_directory_block(self, page):
        if any(block.block_type == "rcc_directory" for block in page.content):
            return

        raw_content = list(page.content.raw_data)
        raw_content.append(
            {
                "type": "rcc_directory",
                "value": DIRECTORY_BLOCK_VALUE,
                "id": str(uuid.uuid4()),
            }
        )
        page.content = raw_content
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS("Added the RCC directory block to the page."))
