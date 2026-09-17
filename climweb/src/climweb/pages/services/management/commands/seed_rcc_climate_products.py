from django.core.management.base import BaseCommand

from climweb.pages.services.models import RCCClimateProductsPage, ServicePage


class Command(BaseCommand):
    help = "Create the RCC Climate Products catalogue page."

    def handle(self, *args, **options):
        parent = ServicePage.objects.filter(
            service__name__iexact=ServicePage.rcc_service_name,
        ).first()
        if not parent:
            self.stderr.write("The Regional Climate Center service page was not found; page creation was deferred.")
            return

        existing = RCCClimateProductsPage.objects.child_of(parent).first()
        if existing:
            self.stdout.write("RCC Climate Products page already exists; its content was preserved.")
            return

        page = RCCClimateProductsPage(
            title="Climate Products",
            slug="climate-products",
            banner_title="Climate products for Africa",
            banner_subtitle="Operational monitoring, forecast and outlook products supporting climate-informed decisions across Africa.",
            banner_image=parent.banner_image,
            introduction_title="Regional climate intelligence",
            introduction_text=(
                "<p>Browse operational climate monitoring, forecast and outlook products published by ACMAD's Regional Climate Center for Africa.</p>"
            ),
            introduction_image=parent.introduction_image,
        )
        parent.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f"Created RCC Climate Products page at {page.url}"))
