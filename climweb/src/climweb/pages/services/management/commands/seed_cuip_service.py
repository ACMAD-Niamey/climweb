from django.core.management.base import BaseCommand
from django.utils.text import slugify
from wagtail.models import Page

from climweb.base.models import ServiceCategory
from climweb.pages.home.models import HomePage
from climweb.pages.products.models import ProductPage
from climweb.pages.services.models import ServiceIndexPage, ServicePage


SERVICE_NAME = "Climate User Interface Platform"
PAGE_TITLE = "African Continental User Interface Platform (CUIP)"
CONTINENTAL_TOR_RECORD = {
    "title": "Continental CUIP workshop concept note and adoption programme",
    "description": "Official 2022 ACMAD workshop record covering the development and adoption of sector TORs and rules of procedure.",
    "url": "https://acmad.org/wp-content/uploads/2019/03/ConceptNoteUserInterfaceWorkshop.pdf",
    "link_label": "View official PDF",
}
AGRICULTURE_DRR_TOR_RECORD = {
    "title": "Agriculture and DRR user-platform consultation TOR",
    "description": "Official French TOR for the 2024 Cameroon consultation and operationalization workshop; relevant to Agriculture and DRR.",
    "url": "https://acmad.org/wp-content/uploads/2019/03/TDRs-Atelier-de-concertation-pour-mise-en-place-des-interfaces-utilisateursnotrackchange.pdf",
    "link_label": "View official PDF",
}

PRODUCTS_BY_SECTOR = {
    "agriculture": [
        "Rainfall and Seasonal Onset Monitoring",
        "Seasonal Forecast Maps",
        "5-Day Rainfall Probability Forecast",
        "Dekadal Weather Forecast",
    ],
    "health": ["Climate and Health", "Heat and Thermal Stress"],
    "water": [
        "Daily Rainfall Monitoring",
        "Monthly Climate Diagnostic Bulletin",
        "Seasonal Forecast Maps",
        "Climate Watch Bulletin",
    ],
    "disaster-risk-reduction": [
        "Weather Watch and Prediction Products",
        "Thunderstorm and Nowcasting",
        "Heat and Thermal Stress",
        "Climate Watch Bulletin",
        "5-Day Rainfall Probability Forecast",
    ],
}


def sector_content(products):
    return [
        (
            "sector",
            {
                "anchor": "agriculture",
                "title": "Agriculture and Food Security",
                "icon": "globe",
                "summary": "Climate information that supports resilient production, food security planning and agricultural decisions.",
                "aim": "<p>CUIP brings climate producers and agricultural users together to shape practical services for crop planning, early action and food security.</p>",
                "risks": ["Floods", "Drought", "High and low temperatures", "Dry spells", "Disruption of the start or end of the season", "Strong winds", "Thunderstorms", "Hailstorms"],
                "climate_services": ["Rainfall onset and cessation information", "Dry-spell forecasts before the planting season", "Impact-based thunderstorm early warnings in clear language", "Seasonal outlooks and agrometeorological advisories"],
                "activities": ["Analyse agricultural commodity value chains and share climate advice", "Assess climate risk along each commodity value chain", "Prepare advice for farmers, herders and fishers", "Estimate production and warehouse requirements", "Estimate commodity supply and demand", "Support commodity conservation and market-price management", "Update, tailor and share climate information among stakeholders"],
                "institutions": ["ACMAD", "Pan African Farmers' Organization (PAFO)", "AGRHYMET", "PROPAC", "CILSS", "FAO", "ICPAC", "SADC Climate Services Centre", "WFP", "FEWS NET", "Agricultural research and producer organisations"],
                "rules_of_procedure": "",
                "platform_composition": [],
                "tor_documents": [CONTINENTAL_TOR_RECORD, AGRICULTURE_DRR_TOR_RECORD],
                "products": products["agriculture"],
                "external_tools": [],
                "meetings": [
                    {
                        "title": "Technical meeting on climate services for agriculture",
                        "details": "Reference material from the original CUIP programme.",
                        "url": "https://acmad.org/wp-content/uploads/2019/03/TOR-AGRICULTURE-CLIMATE-SERVICES-TECHNICAL-MEETING.pdf",
                    }
                ],
            },
        ),
        (
            "sector",
            {
                "anchor": "health",
                "title": "Health",
                "icon": "plus",
                "summary": "Impact-based climate information for meningitis, heat, air quality and other climate-sensitive health risks.",
                "aim": "<p>The health sector service translates meteorological and environmental information into warnings and decision support for public-health partners.</p>",
                "risks": ["Floods and drought", "Heat waves and cold waves", "Dust and haze episodes", "Air pollution", "Humidity-related health risks"],
                "climate_services": ["Clear forecasts on daily, weekly, monthly and seasonal timescales", "Dust and particulate-matter concentration information", "Onset, cessation and duration of climate thresholds", "Meningitis and malaria watches, warnings and alerts", "Historical reviews and projections of climate-health relationships", "Seasonal precipitation, humidity and temperature forecasts", "Risk assessments for climate-sensitive diseases"],
                "activities": ["Analyse health value chains and share climate information for epidemic surveillance and control", "Conduct climate-risk assessments for the health sector", "Prepare advice for disease surveillance and control", "Train and exchange knowledge between climate-service providers and health experts", "Develop and update integrated climate and health information systems", "Tailor and share climate and health data among stakeholders"],
                "institutions": ["World Meteorological Organization", "Regional Climate-Health Network", "ACMAD", "OCEAC", "West African Health Organisation", "Africa Centres for Disease Control and Prevention", "AGRHYMET", "ICPAC", "SADC Climate Services Centre"],
                "rules_of_procedure": "<ul><li>Chair elected from the ClimHealth Network</li><li>Secretariat provided by ACMAD</li><li>Meetings twice a year, with ad hoc meetings when required</li></ul>",
                "platform_composition": ["WMO", "Regional Climate-Health Network", "ACMAD", "OCEAC", "West African Health Organisation", "Africa CDC", "AGRHYMET", "ICPAC", "SADC Climate Services Centre"],
                "tor_documents": [CONTINENTAL_TOR_RECORD],
                "products": products["health"],
                "external_tools": [
                    {
                        "title": "Air Quality Monitoring Map",
                        "description": "External real-time air-quality monitoring tool referenced by the original CUIP portal.",
                        "url": "https://openmap.clarity.io/",
                        "link_label": "Open map",
                    }
                ],
                "meetings": [],
            },
        ),
        (
            "sector",
            {
                "anchor": "water",
                "title": "Water Resources",
                "icon": "site",
                "summary": "Climate monitoring and outlooks that support water-resource planning, preparedness and cooperation.",
                "aim": "<p>CUIP connects climate and water institutions so rainfall monitoring and forecast information can inform water management across timescales.</p>",
                "risks": ["Heavy rainfall and flooding", "Drought", "High temperatures"],
                "climate_services": ["Flood, drought and high-temperature watches, warnings and alerts", "Seasonal precipitation and temperature forecasts", "Climate-risk assessments for water basins"],
                "activities": ["Assess surface-water and groundwater availability", "Conduct climate-risk assessments for the water sector", "Provide flood and drought warnings", "Prepare water-level advice for dams, lakes and rivers", "Train and exchange knowledge between climate-service providers and water experts", "Develop integrated climate and water information systems", "Tailor and share climate and water data among stakeholders"],
                "institutions": ["African Union Commission", "African Ministers' Council on Water", "Regional economic communities", "WMO", "WHO", "ACMAD", "UNESCO", "FAO", "African river-basin organisations and water networks"],
                "rules_of_procedure": "",
                "platform_composition": [],
                "tor_documents": [CONTINENTAL_TOR_RECORD],
                "products": products["water"],
                "external_tools": [],
                "meetings": [],
            },
        ),
        (
            "sector",
            {
                "anchor": "disaster-risk-reduction",
                "title": "Disaster Risk Reduction",
                "icon": "warning",
                "summary": "Multi-hazard climate services for anticipatory action, preparedness and disaster-risk management.",
                "aim": "<p>The disaster-risk-reduction service strengthens knowledge brokering, harmonized warnings and the operational use of forecasts before high-impact events.</p>",
                "risks": ["Floods", "Drought", "Heat waves", "Dry spells", "Strong winds and storms", "Disruption of the start or end of the season"],
                "climate_services": ["Downscaled high-resolution forecasts and scenarios", "Sector-specific advisories", "Verified forecasts with uncertainty information", "Simplified products in accessible languages", "Advanced tailored products and real-time dissemination"],
                "activities": ["Conduct risk assessments", "Raise awareness of hazards, risks and mitigation measures", "Establish multi-hazard early-warning systems", "Update emergency preparedness and response measures", "Provide meteorological support for post-disaster needs assessments", "Support early response and rehabilitation", "Train DRR experts to interpret and use climate services"],
                "institutions": ["African Union Commission", "Regional economic communities", "WMO", "WHO", "UNDRR", "OCHA", "IFRC", "IOM", "WFP", "ASECNA", "National disaster-management and meteorological agencies", "Humanitarian and civil-protection partners"],
                "rules_of_procedure": "",
                "platform_composition": [],
                "tor_documents": [CONTINENTAL_TOR_RECORD, AGRICULTURE_DRR_TOR_RECORD],
                "products": products["disaster-risk-reduction"],
                "external_tools": [],
                "meetings": [],
            },
        ),
    ]


class Command(BaseCommand):
    help = "Create the editable CUIP service page and connect existing ACMAD products."

    def handle(self, *args, **options):
        service, _ = ServiceCategory.objects.get_or_create(
            name=SERVICE_NAME,
            defaults={"icon": "people-group", "order": 20},
        )
        index = ServiceIndexPage.objects.live().first() or ServiceIndexPage.objects.first()
        if not index:
            home = HomePage.objects.live().first() or HomePage.objects.first()
            if not home:
                self.stdout.write(self.style.WARNING("No Home Page exists; CUIP page creation was deferred."))
                return
            index = ServiceIndexPage(title="Services", slug="services")
            home.add_child(instance=index)
            index.save_revision().publish()

        product_lookup = {
            product.title: product
            for product in ProductPage.objects.live().filter(
                title__in={title for titles in PRODUCTS_BY_SECTOR.values() for title in titles}
            )
        }
        products = {
            key: [product_lookup[title] for title in titles if title in product_lookup]
            for key, titles in PRODUCTS_BY_SECTOR.items()
        }

        existing = Page.objects.child_of(index).filter(slug="cuip").first()
        if existing and not isinstance(existing.specific, ServicePage):
            self.stdout.write(self.style.WARNING('The existing "/services/cuip/" page is not a Service Page and was left unchanged.'))
            return
        page = existing.specific if existing else None
        if not page:
            page = ServicePage(
                title=PAGE_TITLE,
                slug="cuip",
                service=service,
                banner_title="Climate information shaped around user decisions",
                banner_subtitle="African Continental User Interface Platform",
                introduction_title="Connecting climate knowledge with sector action",
                introduction_text=(
                    "<p>CUIP is ACMAD's interface for bringing climate-service producers and users together. "
                    "It organizes actionable information around agriculture, health, water resources and disaster risk reduction.</p>"
                ),
                sector_heading="Climate services for priority sectors",
                sector_introduction="<p>Choose a sector to explore its risks, services, partners, products and supporting resources.</p>",
                service_sectors=sector_content(products),
            )
            index.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f'Created and published "{PAGE_TITLE}" at {page.url}.'))
        elif not page.service_sectors:
            page.service_sectors = sector_content(products)
            page.sector_heading = page.sector_heading or "Climate services for priority sectors"
            page.sector_introduction = page.sector_introduction or "<p>Choose a sector to explore its products and supporting resources.</p>"
            page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Added sector content to the existing CUIP page."))
        else:
            seeded_by_anchor = {
                value["anchor"]: value
                for _, value in sector_content(products)
            }
            raw_sectors = list(page.service_sectors.raw_data)
            tor_fields = (
                "rules_of_procedure",
                "platform_composition",
                "tor_documents",
            )
            core_tor_fields = (
                "risks",
                "climate_services",
                "activities",
                "institutions",
            )
            changed = False
            for block in raw_sectors:
                value = block.get("value", {})
                seeded = seeded_by_anchor.get(value.get("anchor"))
                if not seeded:
                    continue
                is_legacy_seed = (
                    "tor_documents" not in value
                    and value.get("summary") == seeded["summary"]
                )
                for field in tor_fields:
                    if not value.get(field) and seeded.get(field):
                        value[field] = seeded[field]
                        changed = True
                if is_legacy_seed:
                    for field in core_tor_fields:
                        value[field] = seeded[field]
                    changed = True
            if changed:
                page.service_sectors = raw_sectors
                page.save_revision().publish()
                self.stdout.write(self.style.SUCCESS("Added the audited TOR content and records to the existing CUIP page."))
            else:
                self.stdout.write("CUIP page already contains TOR content; dashboard edits were preserved.")

        linked = set()
        for sector_products in products.values():
            for product in sector_products:
                if product.pk not in linked:
                    product.other_services.add(service)
                    linked.add(product.pk)
        self.stdout.write(self.style.SUCCESS(f"CUIP ready with four sectors and {len(linked)} linked product families."))
