from django.core.management.base import BaseCommand
from wagtail.models import Site

from climweb.base.models import NavigationSettings
from climweb.pages.products.models import ProductPage
from climweb.pages.services.models import RCCRecommendedFunctionsPage, ServicePage


CLIMATE_INDICES_URL = (
    "https://rcc.acmad.org/CC_Services/climate_change_indexes.html"
)


class Command(BaseCommand):
    help = "Create the editable RCC Highly Recommended Functions page."

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

        report_product = ProductPage.objects.filter(
            slug="climate-change-and-climate-projections"
        ).first()
        page = RCCRecommendedFunctionsPage.objects.child_of(parent).first()
        if page:
            self.stdout.write(
                "RCC Highly Recommended Functions page already exists; its "
                "dashboard content was preserved."
            )
        else:
            page = RCCRecommendedFunctionsPage(
                title="Highly Recommended Functions",
                slug="highly-recommended-functions",
                banner_title="Climate-change analysis for African decision-making",
                banner_subtitle=(
                    "Model evaluation, regional scenarios, risk studies and "
                    "climate-change indices for Africa."
                ),
                banner_image=parent.banner_image,
                introduction_title="Turning climate science into regional evidence",
                introduction_text=(
                    "<p>ACMAD and its partners assess observed and projected climate "
                    "change across Africa using global and regional model simulations, "
                    "long-term observations and standard climate indices.</p>"
                    "<p>These highly recommended RCC functions support robust model "
                    "comparison, downscaling, scenario development, risk assessment "
                    "and the detection of long-term change.</p>"
                ),
                introduction_image=parent.introduction_image,
                functions=[
                    (
                        "function",
                        {
                            "activity": "Access and analyse CMIP, CORDEX and other model simulations",
                            "output_title": "Model intercomparison and evaluation",
                            "description": "Compare global and regional simulations with observations and analyses to understand model performance over Africa.",
                            "icon": "layer-group",
                            "topics": ["CMIP", "CORDEX", "Model evaluation"],
                            "related_page": report_product,
                            "external_url": "",
                            "link_label": "View reports",
                        },
                    ),
                    (
                        "function",
                        {
                            "activity": "Perform regional climate downscaling",
                            "output_title": "Downscaling research",
                            "description": "Develop finer-scale climate information from global simulations for regional and national assessment.",
                            "icon": "site",
                            "topics": ["Regional models", "Bias assessment", "Local information"],
                            "related_page": report_product,
                            "external_url": "",
                            "link_label": "Explore research",
                        },
                    ),
                    (
                        "function",
                        {
                            "activity": "Provide climate scenarios",
                            "output_title": "Climate scenario reports",
                            "description": "Analyse plausible future temperature and precipitation conditions to support adaptation planning.",
                            "icon": "date",
                            "topics": ["Future climate", "Temperature", "Precipitation"],
                            "related_page": report_product,
                            "external_url": "",
                            "link_label": "View scenarios",
                        },
                    ),
                    (
                        "function",
                        {
                            "activity": "Conduct climate variability and risk studies",
                            "output_title": "Climate-risk studies",
                            "description": "Examine historical variability, extremes and exposure to provide evidence for climate-sensitive development.",
                            "icon": "warning",
                            "topics": ["Variability", "Extremes", "Risk"],
                            "related_page": report_product,
                            "external_url": "",
                            "link_label": "View studies",
                        },
                    ),
                    (
                        "function",
                        {
                            "activity": "Detect and project changes in climate indices",
                            "output_title": "Climate-change indices",
                            "description": "Explore station-level observed trends, near-future comparisons and precipitation and temperature indices under multiple scenarios.",
                            "icon": "globe",
                            "topics": ["Observed trends", "RCP scenarios", "Climate extremes"],
                            "related_page": None,
                            "external_url": CLIMATE_INDICES_URL,
                            "link_label": "Open indices application",
                        },
                    ),
                ],
                evidence_heading="Research reports and climate-change evidence",
                evidence_introduction=(
                    "<p>Locally managed reports bring together observed variability, "
                    "model evaluation, climate projections, scenarios and risk studies. "
                    "New reports imported into the Climate Change and Climate "
                    "Projections product archive appear here automatically.</p>"
                ),
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created RCC Highly Recommended Functions page at {page.url}"
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
        labels = {
            "highly recommended function",
            "highly recommended functions",
        }
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
                    "Linked the custom RCC Highly Recommended Functions menu item."
                )
            )
