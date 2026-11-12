from django.db import models
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page

from climweb.base.models import (
    AbstractBannerWithOptionalIntroPage,
    Application,
    ServiceCategory,
)
from climweb.config.settings.base import FULL_RICHTEXT_FRATURES


CLIMATE_HEALTH_SERVICE_NAME = "Climate and Health"


def get_climate_health_service():
    return ServiceCategory.objects.filter(
        name__iexact=CLIMATE_HEALTH_SERVICE_NAME
    ).first()


class ClimateHealthDeskHomePage(AbstractBannerWithOptionalIntroPage):
    """Root page for the dedicated Climate and Health Desk Wagtail Site."""

    template = "climate_health/home_page.html"
    parent_page_types = ["home.HomePage", "services.ServiceIndexPage"]
    subpage_types = [
        "climate_health.ClimateHealthAboutPage",
        "climate_health.ClimateHealthContentPage",
        "climate_health.ClimateHealthPolicyPage",
    ]
    max_count = 1
    show_in_menus_default = True

    hero_kicker = models.CharField(
        max_length=120,
        default="ACMAD Climate and Health Desk",
        verbose_name=_("Hero kicker"),
    )
    map_section_title = models.CharField(
        max_length=160,
        default="Climate and health risk map",
        verbose_name=_("Map section title"),
    )
    map_section_text = RichTextField(
        default=(
            "<p>Explore the latest operational climate-health information from ACMAD's "
            "Multi-Hazard platform. This dedicated view opens with the latest meningitis "
            "vigilance outlook to support public-health early warning and preparedness "
            "across Africa.</p>"
        ),
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("Map section text"),
    )
    map_card_title = models.CharField(
        max_length=100,
        default="Climate and Health",
        verbose_name=_("Map card title"),
    )
    map_viewer_label = models.CharField(
        max_length=80,
        default="Open full viewer",
        verbose_name=_("Map viewer link label"),
    )
    map_viewer_url = models.URLField(
        default="https://multi-hazard.acmad.org/geoportal",
        verbose_name=_("Map viewer URL"),
    )
    products_section_title = models.CharField(
        max_length=160,
        default="Climate and health products",
        verbose_name=_("Products section title"),
    )
    updates_section_title = models.CharField(
        max_length=160,
        default="Latest News and Events",
        verbose_name=_("News and events section title"),
    )
    platforms_section_title = models.CharField(
        max_length=160,
        default="Platforms",
        verbose_name=_("Platforms section title"),
    )
    partners_section_title = models.CharField(
        max_length=160,
        default="Our partners",
        verbose_name=_("Partners section title"),
    )

    mission_title = models.CharField(
        max_length=160,
        default="Turning climate intelligence into healthier outcomes",
        verbose_name=_("Mission title"),
    )
    mission_text = RichTextField(
        blank=True,
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("Mission text"),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerWithOptionalIntroPage.content_panels,
        MultiFieldPanel(
            [FieldPanel("hero_kicker")],
            heading=_("Homepage hero"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("map_section_title"),
                FieldPanel("map_section_text"),
                FieldPanel("map_card_title"),
                FieldPanel("map_viewer_label"),
                FieldPanel("map_viewer_url"),
            ],
            heading=_("Interactive map section"),
        ),
        InlinePanel(
            "priorities",
            label=_("What we do card"),
            heading=_("What we do cards shown below the map"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("products_section_title"),
                FieldPanel("updates_section_title"),
                FieldPanel("platforms_section_title"),
                FieldPanel("partners_section_title"),
            ],
            heading=_("Homepage section titles"),
        ),
        MultiFieldPanel(
            [FieldPanel("mission_title"), FieldPanel("mission_text")],
            heading=_("Mission"),
        ),
        InlinePanel(
            "platform_links",
            label=_("Platform"),
            heading=_("Existing platforms shown by the Health Desk"),
        ),
        InlinePanel(
            "partner_links",
            label=_("Partner"),
            heading=_("Partners shown on the Health Desk homepage"),
        ),
    ]

    class Meta:
        verbose_name = _("Climate and Health Desk homepage")

    @cached_property
    def service_category(self):
        return get_climate_health_service()

    @cached_property
    def products(self):
        from climweb.pages.products.models import ProductPage

        if not self.service_category:
            return ProductPage.objects.none()
        return ProductPage.objects.live().filter(
            Q(service=self.service_category)
            | Q(other_services=self.service_category)
        ).distinct().order_by("menu_order", "title")

    @cached_property
    def publications(self):
        from climweb.pages.publications.models import PublicationPage

        if not self.service_category:
            return PublicationPage.objects.none()
        return PublicationPage.objects.live().filter(
            categories=self.service_category
        ).distinct().order_by("-publication_date")

    @cached_property
    def news(self):
        from climweb.pages.news.models import NewsPage

        if not self.service_category:
            return NewsPage.objects.none()
        return NewsPage.objects.live().public().filter(
            services=self.service_category
        ).distinct().order_by("-date", "-pk")

    @cached_property
    def events(self):
        from climweb.pages.events.models import EventPage

        if not self.service_category:
            return EventPage.objects.none()
        return EventPage.objects.live().filter(
            category=self.service_category,
            is_hidden=False,
        ).distinct().order_by("-date_from")

    @cached_property
    def platforms(self):
        return Application.objects.filter(
            climate_health_links__page=self
        ).distinct().order_by("order", "title")

    @cached_property
    def partners(self):
        from climweb.pages.organisation_pages.partners.models import Partner

        return Partner.objects.filter(
            climate_health_links__page=self
        ).distinct().order_by("order", "name")

    @cached_property
    def section_pages(self):
        pages = {}
        for child in self.get_children().live().specific():
            if isinstance(child, ClimateHealthContentPage):
                pages[child.listing_type] = child
            elif isinstance(child, ClimateHealthAboutPage):
                pages["about"] = child
            elif isinstance(child, ClimateHealthPolicyPage):
                pages["policies"] = child
        return pages

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update({
            "featured_products": self.products[:3],
            "latest_news": self.news[:3],
            "latest_events": self.events[:3],
            "featured_platforms": self.platforms[:3],
            "health_partners": self.partners,
            "section_pages": self.section_pages,
        })

        from adminboundarymanager.models import AdminBoundarySettings
        from climweb.pages.home.models import HomeMapSettings

        map_settings = HomeMapSettings.for_request(request)
        boundary_settings = AdminBoundarySettings.for_request(request)
        context.update({
            "multi_hazard_api_base_url": (
                map_settings.multi_hazard_api_base_url
                or "https://multi-hazard.acmad.org"
            ),
            "multi_hazard_project_slug": (
                map_settings.multi_hazard_project_slug or "multi-hazard"
            ),
            "country_bounds": boundary_settings.combined_countries_bounds,
        })
        return context


class ClimateHealthPlatformLink(Orderable):
    page = ParentalKey(
        ClimateHealthDeskHomePage,
        on_delete=models.CASCADE,
        related_name="platform_links",
    )
    application = models.ForeignKey(
        "base.Application",
        on_delete=models.CASCADE,
        related_name="climate_health_links",
        verbose_name=_("Existing platform"),
    )

    panels = [FieldPanel("application")]


class ClimateHealthPriority(Orderable):
    page = ParentalKey(
        ClimateHealthDeskHomePage,
        on_delete=models.CASCADE,
        related_name="priorities",
    )
    title = models.CharField(max_length=180, verbose_name=_("Title"))
    description = models.TextField(verbose_name=_("Description"))

    panels = [FieldPanel("title"), FieldPanel("description")]


class ClimateHealthPartnerLink(Orderable):
    page = ParentalKey(
        ClimateHealthDeskHomePage,
        on_delete=models.CASCADE,
        related_name="partner_links",
    )
    partner = models.ForeignKey(
        "partners.Partner",
        on_delete=models.CASCADE,
        related_name="climate_health_links",
        verbose_name=_("Existing partner"),
    )

    panels = [FieldPanel("partner")]


class ClimateHealthAboutPage(AbstractBannerWithOptionalIntroPage):
    template = "climate_health/about_page.html"
    parent_page_types = ["climate_health.ClimateHealthDeskHomePage"]
    subpage_types = []
    max_count_per_parent = 1
    show_in_menus_default = True

    vision = RichTextField(
        blank=True,
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("Vision"),
    )
    what_we_do = RichTextField(
        blank=True,
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("What we do"),
    )
    focus_areas = RichTextField(
        blank=True,
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("Areas of focus"),
    )
    launch_context = RichTextField(
        blank=True,
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("Launch context"),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerWithOptionalIntroPage.content_panels,
        FieldPanel("vision"),
        FieldPanel("what_we_do"),
        FieldPanel("focus_areas"),
        FieldPanel("launch_context"),
    ]

    class Meta:
        verbose_name = _("Climate and Health About page")


class ClimateHealthContentPage(AbstractBannerWithOptionalIntroPage):
    PRODUCTS = "products"
    PUBLICATIONS = "publications"
    PLATFORMS = "platforms"
    EVENTS = "events"
    CONTENT_TYPES = (
        (PRODUCTS, _("Products")),
        (PUBLICATIONS, _("Publications")),
        (PLATFORMS, _("Platforms")),
        (EVENTS, _("Events")),
    )

    template = "climate_health/content_page.html"
    parent_page_types = ["climate_health.ClimateHealthDeskHomePage"]
    subpage_types = []
    show_in_menus_default = True

    listing_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPES,
        verbose_name=_("Content to display"),
    )
    items_per_page = models.PositiveSmallIntegerField(default=12)

    content_panels = Page.content_panels + [
        FieldPanel("listing_type"),
        *AbstractBannerWithOptionalIntroPage.content_panels,
        FieldPanel("items_per_page"),
    ]

    class Meta:
        verbose_name = _("Climate and Health content page")

    @cached_property
    def desk_home(self):
        return self.get_parent().specific

    def get_items(self, request):
        items = getattr(self.desk_home, self.listing_type)
        query = request.GET.get("q", "").strip()
        year = request.GET.get("year", "").strip()

        if query:
            items = items.filter(title__icontains=query)
        if year.isdigit():
            if self.listing_type == self.PUBLICATIONS:
                items = items.filter(publication_date__year=int(year))
            elif self.listing_type == self.EVENTS:
                items = items.filter(date_from__year=int(year))

        return items

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        items = self.get_items(request)
        paginator = Paginator(items, self.items_per_page)
        context.update({
            "items": paginator.get_page(request.GET.get("page")),
            "result_count": paginator.count,
            "query": request.GET.get("q", "").strip(),
            "selected_year": request.GET.get("year", "").strip(),
        })
        return context


class ClimateHealthPolicyPage(AbstractBannerWithOptionalIntroPage):
    template = "climate_health/policy_page.html"
    parent_page_types = ["climate_health.ClimateHealthDeskHomePage"]
    subpage_types = []
    max_count_per_parent = 1
    show_in_menus_default = True

    body = RichTextField(
        blank=True,
        features=FULL_RICHTEXT_FRATURES,
        verbose_name=_("Action plan and policy content"),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerWithOptionalIntroPage.content_panels,
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = _("Climate and Health action plan and policies page")

    @cached_property
    def related_publications(self):
        from climweb.pages.publications.models import PublicationPage

        service = get_climate_health_service()
        if not service:
            return PublicationPage.objects.none()
        policy_terms = (
            Q(publication_type__name__icontains="policy")
            | Q(publication_type__name__icontains="action plan")
            | Q(publication_type__name__icontains="strategy")
        )
        return PublicationPage.objects.live().filter(
            policy_terms,
            categories=service,
        ).distinct().order_by("-publication_date")
