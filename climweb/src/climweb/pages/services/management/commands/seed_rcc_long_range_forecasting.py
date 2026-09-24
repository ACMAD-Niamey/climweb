from django.core.management import call_command
from django.core.management.base import BaseCommand
from wagtail.models import Site

from climweb.base.models import NavigationSettings
from climweb.pages.services.models import RCCLongRangeForecastingPage, ServicePage


class Command(BaseCommand):
    help = "Create the editable RCC Long-range Forecasting function page."

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

        page = RCCLongRangeForecastingPage.objects.child_of(parent).first()
        if page:
            self.stdout.write(
                "RCC Long-range Forecasting page already exists; its dashboard "
                "content was preserved."
            )
        else:
            page = RCCLongRangeForecastingPage(
                title="Long-range Forecasting",
                slug="long-range-forecasting",
                banner_title="Seasonal outlooks for Africa",
                banner_subtitle=(
                    "Regional climate guidance for the months and seasons ahead."
                ),
                banner_image=parent.banner_image,
                introduction_title="From global guidance to regional outlooks",
                introduction_text=(
                    "<p>ACMAD collects ensemble and multimodel guidance from Global "
                    "Producing Centres for Long-Range Forecasts, assesses the "
                    "performance of those systems and develops consolidated outlooks "
                    "for Africa and its sub-regions.</p>"
                    "<p>The resulting maps, bulletins, consensus statements and "
                    "verification products support regional climate services and "
                    "climate-sensitive decision-making.</p>"
                ),
                introduction_image=parent.introduction_image,
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created RCC Long-range Forecasting page at {page.url}"
                )
            )

        self._link_custom_menu(page)
        call_command("seed_rcc_consensus_forums", stdout=self.stdout)

    def _link_custom_menu(self, page):
        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            return

        navigation = NavigationSettings.for_site(site)
        menu = []
        changed = False
        labels = {"long-range forecasting", "long range forecasting"}
        for block in navigation.rcc_main_menu:
            value = dict(block.value)
            if value.get("label", "").strip().casefold() in labels:
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
                    "Linked the custom RCC Long-range Forecasting menu item."
                )
            )
