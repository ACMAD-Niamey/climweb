from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from wagtail.images import get_image_model
from wagtail.models import Site

from climweb.pages.climsa.models import ClimsaAboutPage, ClimsaHomePage
from climweb.pages.home.models import HomePage


class Command(BaseCommand):
    help = "Create or update the Wagtail Site used by the dedicated CLIMSA hostname."

    def add_arguments(self, parser):
        parser.add_argument("--hostname", default="climsa.acmad.org")
        parser.add_argument("--port", type=int, default=443)
        parser.add_argument(
            "--create",
            action="store_true",
            help="Create and publish the CLIMSA home page beneath the default homepage if missing.",
        )

    def handle(self, *args, **options):
        hostname = options["hostname"].strip().lower().rstrip(".")
        if not hostname or "://" in hostname or "/" in hostname:
            raise CommandError("--hostname must be a hostname without a scheme or path")

        climsa_page = ClimsaHomePage.objects.live().first()
        page_created = False
        if not climsa_page and options["create"]:
            parent = HomePage.objects.live().first()
            if not parent:
                raise CommandError("A live main HomePage is required before creating CLIMSA")
            climsa_page = ClimsaHomePage(title="CLIMSA", slug="climsa")
            parent.add_child(instance=climsa_page)
            climsa_page.save_revision().publish()
            page_created = True

        if not climsa_page:
            raise CommandError(
                "The live CLIMSA home page was not found. Create it in Wagtail or rerun with --create."
            )

        about_page = ClimsaAboutPage.objects.child_of(climsa_page).first()
        about_created = False
        if not about_page and options["create"]:
            about_page = ClimsaAboutPage(title="About Us", slug="about")
            climsa_page.add_child(instance=about_page)
            about_page.save_revision().publish()
            about_created = True

        if about_page and climsa_page.about_page_id != about_page.pk:
            climsa_page.about_page = about_page
            climsa_page.save_revision().publish()

        if not climsa_page.climsa_logo_id:
            Image = get_image_model()
            logo = (
                Image.objects.filter(
                    Q(title__iexact="ClimSA_Prime.jpg")
                    | Q(file__iendswith="/ClimSA_Prime.jpg")
                )
                .order_by("pk")
                .first()
            )
            if logo:
                climsa_page.climsa_logo = logo
                climsa_page.save_revision().publish()

        if not climsa_page.programme_partners_logo_id:
            Image = get_image_model()
            partners_logo = (
                Image.objects.filter(
                    Q(title__iexact="climsa2")
                    | Q(file__iendswith="/climsa2.jpg")
                )
                .order_by("pk")
                .first()
            )
            if partners_logo:
                climsa_page.programme_partners_logo = partners_logo
                climsa_page.save_revision().publish()

        site = Site.objects.filter(hostname=hostname).order_by("pk").first()
        site_created = site is None
        if site_created:
            site = Site(hostname=hostname)

        site.port = options["port"]
        site.site_name = "ACMAD CLIMSA"
        site.root_page = climsa_page
        site.is_default_site = False
        site.full_clean()
        site.save()

        created_pages = []
        if page_created:
            created_pages.append("CLIMSA home page")
        if about_created:
            created_pages.append("About Us page")
        page_action = f"Created {' and '.join(created_pages)} and " if created_pages else ""
        site_action = "created" if site_created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{page_action}{site_action} Wagtail Site {hostname}:{site.port} "
                f"with root page {climsa_page.title!r}."
            )
        )
