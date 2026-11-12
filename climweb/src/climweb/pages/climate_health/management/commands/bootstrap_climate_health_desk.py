from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from wagtail.models import Site

from climweb.base.models import Application, ServiceCategory
from climweb.pages.climate_health.models import (
    CLIMATE_HEALTH_SERVICE_NAME,
    ClimateHealthAboutPage,
    ClimateHealthContentPage,
    ClimateHealthDeskHomePage,
    ClimateHealthPartnerLink,
    ClimateHealthPlatformLink,
    ClimateHealthPolicyPage,
    ClimateHealthPriority,
)
from climweb.pages.home.models import HomePage
from climweb.pages.products.models import ProductPage
from climweb.pages.services.models import ServiceIndexPage
from climweb.pages.organisation_pages.partners.models import Partner


CONTENT_PAGES = (
    (
        "products",
        "Products",
        "Climate and health products",
        "Operational bulletins, risk outlooks, maps and decision-ready climate information for public-health partners.",
    ),
    (
        "publications",
        "Publications",
        "Climate and health publications",
        "Research, technical guidance and evidence connecting climate conditions with health risks and response.",
    ),
    (
        "platforms",
        "Platforms",
        "Climate and health platforms",
        "Existing ACMAD applications and decision-support tools used to explore climate and health information.",
    ),
    (
        "events",
        "Events",
        "Climate and health events",
        "Upcoming and past dialogues, trainings and coordination events for the climate and health community.",
    ),
)

HEALTH_PARTNERS = (
    ("African Centre of Meteorological Applications for Development (ACMAD)", "https://acmad.org/"),
    ("WHO-WMO Climate and Health Joint Programme", "https://www.climahealth.info/"),
    ("The Rockefeller Foundation", "https://www.rockefellerfoundation.org/"),
    ("Wellcome Trust", "https://wellcome.org/"),
    (
        "Weather and Climate Information Services (WISER)",
        "https://www.metoffice.gov.uk/services/government/international-development/weather-and-climate-information-services-wiser/index",
    ),
    ("University of Reading", "https://www.reading.ac.uk/"),
)

WHAT_WE_DO_HTML = (
    "<p>The Africa Climate and Health Desk focuses on the following priorities:</p>"
    "<ul><li><strong>Strengthening climate-informed health early warning systems (EWS):</strong> "
    "Develop and deliver operational early warning information for climate-sensitive health risks "
    "such as heat-related mortality and morbidity, vector-borne diseases, and meningitis.</li>"
    "<li><strong>Case study research:</strong> Analyze extreme climate events to understand their "
    "health impacts and enable rapid scientific assessments during—or even before—climate-health crises.</li>"
    "<li><strong>Building capacity and technical expertise:</strong> Provide specialized on-the-job "
    "training and e-learning programmes to strengthen the technical skills of National Meteorological "
    "and Hydrological Services (NMHSs) and Ministries of Health (MoH).</li>"
    "<li><strong>Strengthening collaboration and co-production:</strong> Jointly design climate "
    "services with climate scientists and health experts for operational use.</li></ul>"
)

FOCUS_AREAS_HTML = (
    "<p>The Africa Climate and Health Desk addresses key climate-sensitive health risks, including:</p>"
    "<ul><li><strong>Heatwave Early Warning Systems</strong> – Developing early warning information "
    "to reduce heat-related health impacts.</li>"
    "<li><strong>Meningitis Climate Risk Forecasting</strong> – Enhancing the Meningitis Early Warning "
    "System (MEWS) with new data, improved climate forecasts and validation processes.</li>"
    "<li><strong>Infectious Diseases</strong> – Supporting climate-informed monitoring of diseases "
    "such as malaria and dengue.</li>"
    "<li><strong>Drought Monitoring and Forecasting</strong> – Providing real-time drought monitoring "
    "and advisories to support food security and malnutrition risk planning.</li>"
    "<li><strong>Air Quality Monitoring</strong> – Supporting analysis of air-pollution risks and their "
    "impacts on public health.</li>"
    "<li><strong>Applied Research and Innovation</strong> – Using AI-based downscaling models to "
    "produce high-resolution impact-based forecasts.</li></ul>"
)

WHAT_WE_DO_CARDS = (
    (
        "Climate-informed health early warning systems",
        "Develop and deliver operational early warning information for heat-related health impacts, vector-borne diseases and meningitis.",
    ),
    (
        "Case study research",
        "Analyze extreme climate events to understand their health impacts and enable rapid scientific assessments before and during climate-health crises.",
    ),
    (
        "Capacity and technical expertise",
        "Provide specialized on-the-job training and e-learning for National Meteorological and Hydrological Services and Ministries of Health.",
    ),
    (
        "Collaboration and co-production",
        "Jointly design operational climate services with climate scientists, health experts and decision-makers.",
    ),
)


class Command(BaseCommand):
    help = "Create or update the Climate and Health Desk page tree and Wagtail Site."

    def add_arguments(self, parser):
        parser.add_argument("--hostname", default="climatehealthdesk.domainname")
        parser.add_argument("--port", type=int, default=443)

    @transaction.atomic
    def handle(self, *args, **options):
        hostname = options["hostname"].strip().lower().rstrip(".")
        if not hostname or "://" in hostname or "/" in hostname:
            raise CommandError("--hostname must be a hostname without a scheme or path")

        service, _ = ServiceCategory.objects.get_or_create(
            name=CLIMATE_HEALTH_SERVICE_NAME,
            defaults={"icon": "heart-pulse"},
        )
        ProductPage.objects.filter(slug="climate-and-health").exclude(
            service=service
        ).update(service=service)

        home = ClimateHealthDeskHomePage.objects.first()
        if not home:
            parent = ServiceIndexPage.objects.live().first() or HomePage.objects.live().first()
            if not parent:
                raise CommandError("A live ServiceIndexPage or HomePage is required")
            home = ClimateHealthDeskHomePage(
                title="Climate and Health Desk",
                slug="climate-health-desk",
                banner_title="Climate and Health Desk",
                banner_subtitle="",
                introduction_title="Climate-informed public health",
                introduction_text=(
                    "<p>The ACMAD Climate and Health Desk brings climate services, health-risk "
                    "information and regional coordination into one trusted space.</p>"
                ),
                mission_text=(
                    "<p>We support institutions to anticipate climate-sensitive health threats, "
                    "translate evidence into action and protect communities across Africa.</p>"
                ),
            )
            parent.add_child(instance=home)
            home.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Created Climate and Health Desk homepage"))

        hero_changed = False
        if home.banner_title != "Climate and Health Desk":
            home.banner_title = "Climate and Health Desk"
            hero_changed = True
        if home.banner_subtitle:
            home.banner_subtitle = ""
            hero_changed = True
        if hero_changed:
            home.save_revision().publish()
            self.stdout.write("Updated Health Desk hero")

        if not home.priorities.exists():
            for order, (title, description) in enumerate(WHAT_WE_DO_CARDS):
                ClimateHealthPriority.objects.create(
                    page=home,
                    title=title,
                    description=description,
                    sort_order=order,
                )

        if not ClimateHealthAboutPage.objects.child_of(home).exists():
            about = ClimateHealthAboutPage(
                title="About",
                slug="about",
                banner_title="About the Climate and Health Desk",
                banner_subtitle="A continental hub connecting climate science and public-health action.",
                introduction_title="Bridging climate science and public health",
                introduction_text=(
                    "<p>Hosted by the African Centre of Meteorological Applications for Development "
                    "(ACMAD), the Africa Climate and Health Desk is a flagship initiative advancing "
                    "the use of climate intelligence in public-health decision-making across Africa. "
                    "It strengthens collaboration, supports capacity development, co-produces climate "
                    "services and delivers operational early warnings for climate-sensitive health risks.</p>"
                ),
                vision=(
                    "<p>A continent where climate intelligence is systematically integrated into "
                    "public-health decision-making to protect lives and well-being, strengthen health "
                    "systems and build resilient communities.</p>"
                ),
                what_we_do=WHAT_WE_DO_HTML,
                focus_areas=FOCUS_AREAS_HTML,
                launch_context=(
                    "<p>The Africa Climate and Health Desk was officially launched on 13 March 2026 "
                    "alongside the 20th African Continental Climate Outlook Forum (ACCOF-20), marking "
                    "a major step toward stronger connections between climate services and public-health "
                    "systems across Africa.</p>"
                ),
            )
            home.add_child(instance=about)
            about.save_revision().publish()
            self.stdout.write("Created About page")

        about = ClimateHealthAboutPage.objects.child_of(home).first()
        about_changed = False
        if str(about.what_we_do) != WHAT_WE_DO_HTML:
            about.what_we_do = WHAT_WE_DO_HTML
            about_changed = True
        if str(about.focus_areas) != FOCUS_AREAS_HTML:
            about.focus_areas = FOCUS_AREAS_HTML
            about_changed = True
        if about_changed:
            about.save_revision().publish()
            self.stdout.write("Updated About page priorities and focus areas")

        existing_types = set(
            ClimateHealthContentPage.objects.child_of(home).values_list(
                "listing_type", flat=True
            )
        )
        for content_type, title, banner_title, introduction in CONTENT_PAGES:
            if content_type in existing_types:
                continue
            child = ClimateHealthContentPage(
                title=title,
                slug=content_type,
                listing_type=content_type,
                banner_title=banner_title,
                banner_subtitle=introduction,
                introduction_title=banner_title,
                introduction_text=f"<p>{introduction}</p>",
            )
            home.add_child(instance=child)
            child.save_revision().publish()
            self.stdout.write(f"Created {title} page")

        if not ClimateHealthPolicyPage.objects.child_of(home).exists():
            policy = ClimateHealthPolicyPage(
                title="Action Plan & Policies",
                slug="action-plan-policies",
                banner_title="Action Plan & Policies",
                banner_subtitle=(
                    "A shared framework for climate-informed public-health preparedness and action."
                ),
                introduction_title="Turning shared priorities into coordinated action",
                introduction_text=(
                    "<p>This page brings together the Desk's strategic direction, action priorities "
                    "and the policies that support climate-resilient health systems.</p>"
                ),
                body=(
                    "<h3>Priority areas</h3>"
                    "<ul><li>Climate-informed disease surveillance and early warning</li>"
                    "<li>Heat-health preparedness and response</li>"
                    "<li>Data sharing, research and regional coordination</li>"
                    "<li>Capacity development for climate and health practitioners</li></ul>"
                    "<p>Editors can replace this starter content with the approved action plan and policy framework.</p>"
                ),
            )
            home.add_child(instance=policy)
            policy.save_revision().publish()
            self.stdout.write("Created Action Plan & Policies page")

        drought_advisory, _ = Application.objects.get_or_create(
            title="Africa Drought Monitoring and Advisory",
            defaults={"url": "https://ada.acmad.org/home", "order": 0},
        )
        multi_hazard, _ = Application.objects.get_or_create(
            title="Multi-Hazard Hub",
            defaults={"url": "https://multi-hazard.acmad.org/geoportal", "order": 1},
        )
        platform_candidates = Application.objects.filter(
            Q(pk__in=[drought_advisory.pk, multi_hazard.pk])
            | Q(title__icontains="health")
            | Q(title__icontains="heat")
            | Q(title__icontains="meningitis")
            | Q(title__icontains="hazard")
            | Q(title__icontains="drought")
        ).order_by("order", "title")
        for application in platform_candidates:
            ClimateHealthPlatformLink.objects.get_or_create(
                page=home,
                application=application,
            )

        if not home.partner_links.exists():
            for order, (name, link) in enumerate(HEALTH_PARTNERS, start=20):
                partner, created = Partner.objects.get_or_create(
                    name=name,
                    defaults={"link": link, "order": order},
                )
                if not created and not partner.link:
                    partner.link = link
                    partner.save(update_fields=["link"])
                ClimateHealthPartnerLink.objects.create(
                    page=home,
                    partner=partner,
                    sort_order=order,
                )

        site = Site.objects.filter(hostname=hostname).order_by("pk").first()
        created = site is None
        if created:
            site = Site(hostname=hostname)
        site.port = options["port"]
        site.site_name = "ACMAD Climate and Health Desk"
        site.root_page = home
        site.is_default_site = False
        site.full_clean()
        site.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Wagtail Site {hostname}:{site.port} with root {home.title!r}."
            )
        )
