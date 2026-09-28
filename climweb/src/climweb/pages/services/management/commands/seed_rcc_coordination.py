from django.core.management import call_command
from django.core.management.base import BaseCommand
from wagtail.models import Site

from climweb.base.models import NavigationSettings
from climweb.pages.services.legacy_forum_content import LEGACY_FORUM_SECTIONS
from climweb.pages.services.long_range_forums import LEGACY_FORUM_BACKGROUNDS
from climweb.pages.services.models import (
    RCCConsensusForumPage,
    RCCCoordinationPage,
    RCCDataServicesPage,
    RCCLongRangeForecastingPage,
    RCCTrainingPage,
    ServicePage,
)


ACCOF_BACKGROUND = LEGACY_FORUM_BACKGROUNDS["ACCOF"]

ACCOF_SECTIONS = LEGACY_FORUM_SECTIONS["ACCOF"]


class Command(BaseCommand):
    help = "Create the editable RCC Coordination page and link ACCOF beneath it."

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

        training_page = RCCTrainingPage.objects.live().first()
        data_page = RCCDataServicesPage.objects.live().first()
        long_range_page = RCCLongRangeForecastingPage.objects.live().first()
        page = RCCCoordinationPage.objects.child_of(parent).first()
        if not page:
            page = RCCCoordinationPage(
                title="Coordination",
                slug="coordination",
                banner_title="Coordinating climate services across Africa",
                banner_subtitle=(
                    "Connecting Regional Climate Centres, national services and "
                    "global partners around consistent methods, products and delivery."
                ),
                banner_image=parent.banner_image,
                introduction_title="A connected Regional Climate Centre community",
                introduction_text=(
                    "<p>ACMAD coordinates Regional Climate Centre activities within "
                    "WMO Regional Association I, helping African institutions align "
                    "training, data services, climate monitoring and long-range "
                    "forecasting.</p><p>This function promotes common approaches, "
                    "technical exchange and consistent climate information across "
                    "the continent.</p>"
                ),
                introduction_image=parent.introduction_image,
                coordination_areas=[
                    (
                        "area",
                        {
                            "activity": "Coordination of training",
                            "output_title": "RCC meetings and training reports",
                            "description": "Regional learning, technical exchange and capacity-development records for RCCs in Africa.",
                            "icon": "group",
                            "related_page": training_page,
                            "external_url": "",
                            "link_label": "Explore training",
                        },
                    ),
                    (
                        "area",
                        {
                            "activity": "Coordination on data services",
                            "output_title": "Data rescue and management reports",
                            "description": "Coordinated approaches to climate-data rescue, quality, management and access.",
                            "icon": "database",
                            "related_page": data_page,
                            "external_url": "",
                            "link_label": "Explore data services",
                        },
                    ),
                    (
                        "area",
                        {
                            "activity": "Coordination on climate",
                            "output_title": "Monitoring and forecasting meeting reports",
                            "description": "Continental exchange on monitoring evidence, seasonal prediction and consistent outlook communication.",
                            "icon": "globe",
                            "related_page": long_range_page,
                            "external_url": "",
                            "link_label": "Explore forecasting",
                        },
                    ),
                ],
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"Created RCC Coordination page at {page.url}"))
        else:
            self.stdout.write("RCC Coordination page already exists; its dashboard content was preserved.")

        accof_page = RCCConsensusForumPage.objects.filter(
            forum_code__iexact="ACCOF"
        ).first()
        if not accof_page and long_range_page:
            call_command("seed_rcc_consensus_forums", stdout=self.stdout)
            accof_page = RCCConsensusForumPage.objects.filter(
                forum_code__iexact="ACCOF"
            ).first()
        if accof_page:
            accof_page.overview = ACCOF_BACKGROUND
            accof_page.consensus_method = ACCOF_SECTIONS["consensus_method"]
            accof_page.user_involvement = ACCOF_SECTIONS["user_involvement"]
            accof_page.development_priorities = ACCOF_SECTIONS[
                "development_priorities"
            ]
            accof_page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Updated the editable ACCOF profile."))

        self._link_custom_menu(page, accof_page)

    def _link_custom_menu(self, coordination_page, accof_page):
        site = Site.objects.filter(is_default_site=True).first()
        if not site:
            return

        navigation = NavigationSettings.for_site(site)
        menu = []
        coordination_found = False
        for block in navigation.rcc_main_menu:
            value = dict(block.value)
            if value.get("label", "").strip().casefold() == "coordination":
                coordination_found = True
                value["page"] = coordination_page
                value["external_url"] = ""
                sub_items = []
                accof_found = False
                for sub_block in value.get("sub_items") or []:
                    sub_value = dict(sub_block.value)
                    if sub_value.get("label", "").strip().casefold() == "accof":
                        accof_found = True
                        sub_value["page"] = accof_page
                        sub_value["external_url"] = ""
                    sub_items.append((sub_block.block_type, sub_value))
                if accof_page and not accof_found:
                    sub_items.append(
                        (
                            "sub_item",
                            {
                                "label": "ACCOF",
                                "page": accof_page,
                                "external_url": "",
                                "is_action": False,
                            },
                        )
                    )
                value["sub_items"] = sub_items
            menu.append((block.block_type, value))

        if not coordination_found:
            sub_items = []
            if accof_page:
                sub_items.append(
                    (
                        "sub_item",
                        {
                            "label": "ACCOF",
                            "page": accof_page,
                            "external_url": "",
                            "is_action": False,
                        },
                    )
                )
            menu.append(
                (
                    "navigation_item",
                    {
                        "label": "Coordination",
                        "page": coordination_page,
                        "external_url": "",
                        "include_subpages": False,
                        "large_submenu": False,
                        "sub_items": sub_items,
                    },
                )
            )

        navigation.rcc_main_menu = menu
        navigation.save()
        self.stdout.write(self.style.SUCCESS("Linked Coordination and ACCOF in the RCC menu."))
