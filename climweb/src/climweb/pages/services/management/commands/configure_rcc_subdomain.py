from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Site

from climweb.pages.services.models import ServicePage


class Command(BaseCommand):
    help = "Create or update the Wagtail Site used by the dedicated RCC hostname."

    def add_arguments(self, parser):
        parser.add_argument("--hostname", default="nrcc.acmad.org")
        parser.add_argument("--port", type=int, default=443)

    def handle(self, *args, **options):
        hostname = options["hostname"].strip().lower().rstrip(".")
        if not hostname or "://" in hostname or "/" in hostname:
            raise CommandError("--hostname must be a hostname without a scheme or path")

        rcc_page = ServicePage.objects.live().filter(
            service__name__iexact=ServicePage.rcc_service_name
        ).first()
        if not rcc_page:
            raise CommandError("The live Regional Climate Center page was not found")

        site = Site.objects.filter(hostname=hostname).order_by("pk").first()
        created = site is None
        if created:
            site = Site(hostname=hostname)

        site.port = options["port"]
        site.site_name = "ACMAD Regional Climate Centre"
        site.root_page = rcc_page
        site.is_default_site = False
        site.full_clean()
        site.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Wagtail Site {hostname}:{site.port} with root "
                f"page {rcc_page.title!r}."
            )
        )
