from django.core.management.base import BaseCommand
from wagtail.models import Site

from climweb.base.models import NavigationSettings
from climweb.pages.services.models import RCCClimateMonitoringPage, ServicePage


class Command(BaseCommand):
    help = "Create the editable RCC Climate Monitoring function page."

    def handle(self, *args, **options):
        parent = ServicePage.objects.filter(
            service__name__iexact=ServicePage.rcc_service_name,
        ).first()
        if not parent:
            self.stderr.write(
                "The Regional Climate Center service page was not found; "
                "page creation was deferred."
            )
            return

        existing = RCCClimateMonitoringPage.objects.child_of(parent).first()
        if existing:
            self.stdout.write(
                "RCC Climate Monitoring page already exists; its dashboard "
                "content was preserved."
            )
            page = existing
        else:
            page = RCCClimateMonitoringPage(
                title="Climate Monitoring",
                slug="climate-monitoring",
                banner_title="Climate monitoring for Africa",
                banner_subtitle=(
                    "Tracking present climate conditions, anomalies and extremes "
                    "across Africa and the global climate system."
                ),
                banner_image=parent.banner_image,
                introduction_title="Monitoring Africa's climate system",
                introduction_text=(
                    "<p>ACMAD's Regional Climate Centre monitors the present state "
                    "of the ocean-land-atmosphere system using temperature, "
                    "precipitation, atmospheric circulation and convection over "
                    "Africa and the globe.</p>"
                    "<p>The monitoring evidence combines in-situ and satellite "
                    "observations with analyses and reanalyses from global centres. "
                    "These consistent records support climate diagnostics, the "
                    "assessment of trends and extremes, climate research and "
                    "operational long-range forecasting.</p>"
                ),
                introduction_image=parent.introduction_image,
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created RCC Climate Monitoring page at {page.url}"
                )
            )

        self._link_custom_menu(page)

    def _link_custom_menu(self, page):
        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            return

        navigation = NavigationSettings.for_site(site)
        menu = []
        changed = False
        for block in navigation.rcc_main_menu:
            value = dict(block.value)
            if value.get("label", "").strip().casefold() == "climate monitoring":
                if value.get("page") != page or value.get("external_url"):
                    value["page"] = page
                    value["external_url"] = ""
                    changed = True
            menu.append((block.block_type, value))

        if changed:
            navigation.rcc_main_menu = menu
            navigation.save()
            self.stdout.write(
                self.style.SUCCESS(
                    "Linked the custom RCC Climate Monitoring menu item."
                )
            )
