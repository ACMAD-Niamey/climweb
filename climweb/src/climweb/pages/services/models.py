from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import (FieldPanel, MultiFieldPanel, PageChooserPanel, InlinePanel)
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, Orderable
from wagtail.snippets.models import register_snippet
from wagtailmetadata.models import MetadataPageMixin

from climweb.base import blocks
from climweb.base import blocks as base_blocks
from climweb.base.models import ServiceCategory, AbstractBannerWithIntroPage
from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES
from climweb.pages.events.models import EventPage
from climweb.pages.flex_page.models import FlexPage
from climweb.pages.news.models import NewsPage
from climweb.pages.organisation_pages.partners.models import Partner
from climweb.pages.organisation_pages.projects.models import ServiceProject
from climweb.pages.products.models import ProductPage, SubNationalProductPage
from climweb.pages.publications.models import PublicationPage
from climweb.pages.videos.models import YoutubePlaylist
from . import blocks as local_blocks


@register_snippet
class MeteorologicalService(models.Model):
    country = models.CharField(max_length=100, verbose_name=_("Country"))
    name = models.CharField(max_length=255, verbose_name=_("Service name"))
    acronym = models.CharField(max_length=30, blank=True, verbose_name=_("Acronym"))
    website_url = models.URLField(
        max_length=500,
        verbose_name=_("Website URL"),
        help_text=_("The official website opened when a visitor selects the card."),
    )
    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Logo"),
        help_text=_("Upload the official service logo. A sourced fallback is used when empty."),
    )
    logo_source_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name=_("Fallback logo URL"),
        help_text=_("Optional external fallback used until a logo is uploaded."),
    )
    wmo_member_id = models.PositiveIntegerField(null=True, blank=True, unique=True, editable=False)
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display order"))
    is_active = models.BooleanField(default=True, verbose_name=_("Visible on the directory"))

    panels = [
        FieldPanel("country"),
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("website_url"),
        FieldPanel("logo"),
        FieldPanel("logo_source_url"),
        FieldPanel("order"),
        FieldPanel("is_active"),
    ]

    class Meta:
        ordering = ("order", "country", "name")
        verbose_name = _("Meteorological Service")
        verbose_name_plural = _("Meteorological Services")

    def __str__(self):
        return f"{self.country} — {self.name}"


@register_snippet
class RCCDatasetAsset(models.Model):
    """Metadata pointer to an RCC-managed dataset object.

    Keeping the object name separate from the database makes the public URL stable
    when the ``rcc_data`` storage backend is moved from disk to S3/MinIO.
    """

    key = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    station = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=100, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)
    latitude = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)
    source_url = models.URLField(max_length=700, blank=True)
    object_name = models.CharField(max_length=500, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    record_count = models.PositiveIntegerField(default=0)
    coverage_start = models.DateField(null=True, blank=True)
    coverage_end = models.DateField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    panels = [
        FieldPanel("key"),
        FieldPanel("title"),
        FieldPanel("summary"),
        MultiFieldPanel(
            [
                FieldPanel("station"),
                FieldPanel("country"),
                FieldPanel("longitude"),
                FieldPanel("latitude"),
            ],
            heading=_("Location"),
        ),
        FieldPanel("source_url"),
    ]

    class Meta:
        ordering = ("title",)
        verbose_name = _("RCC dataset")
        verbose_name_plural = _("RCC datasets")

    def __str__(self):
        return self.title

    @property
    def is_available(self):
        return bool(self.object_name and self.synced_at)


class RCCARC2ImportConfig(models.Model):
    """Shared ARC2 importer settings across every catalogue country."""

    singleton_key = models.CharField(max_length=20, unique=True, default="arc2", editable=False)
    catalogue_url = models.URLField(
        max_length=700,
        default=(
            "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
            "climatedataservice/Synoptic_Daily_ARC2_Data/catalog.xml"
        ),
    )
    enabled = models.BooleanField(default=False)
    interval_hours = models.PositiveSmallIntegerField(default=24)
    import_all_stations = models.BooleanField(default=False)
    discovered_countries = models.JSONField(default=list, blank=True)
    selected_stations = models.JSONField(default=list, blank=True)
    discovered_stations = models.JSONField(default=list, blank=True)
    discovered_at = models.DateTimeField(null=True, blank=True)
    discovery_error = models.TextField(blank=True)

    def __str__(self):
        return "ARC2 station importer"


BASE_IMPORT_STATUS_CHOICES = [
    ("queued", "Queued"),
    ("running", "Running"),
    ("succeeded", "Succeeded"),
    ("partial", "Partially succeeded"),
    ("failed", "Failed"),
]


class RCCARC2ImportRun(models.Model):
    STATUS_CHOICES = BASE_IMPORT_STATUS_CHOICES + [("cancelled", "Stopped")]
    TRIGGER_CHOICES = [("manual", "Manual"), ("scheduled", "Scheduled")]

    config = models.ForeignKey(RCCARC2ImportConfig, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="queued")
    trigger = models.CharField(max_length=12, choices=TRIGGER_CHOICES)
    stations = models.JSONField(default=list)
    country = models.CharField(max_length=80, default="Niger")
    catalogue_url = models.URLField(max_length=700, blank=True)
    import_all_stations = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)
    results = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ("-created_at",)


class RCCCPCImportConfig(models.Model):
    singleton_key = models.CharField(max_length=20, unique=True, default="cpc-unified", editable=False)
    catalogue_url = models.URLField(
        max_length=700,
        default=(
            "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
            "climatedataservice/Synoptic_Daily_CPC_Unified_Data/catalog.xml"
        ),
    )
    enabled = models.BooleanField(default=False)
    interval_hours = models.PositiveSmallIntegerField(default=24)
    import_all_stations = models.BooleanField(default=False)
    discovered_countries = models.JSONField(default=list, blank=True)
    selected_stations = models.JSONField(default=list, blank=True)
    discovered_stations = models.JSONField(default=list, blank=True)
    discovered_at = models.DateTimeField(null=True, blank=True)
    discovery_error = models.TextField(blank=True)

    def __str__(self):
        return "CPC-Unified station importer"


class RCCCPCImportRun(models.Model):
    STATUS_CHOICES = RCCARC2ImportRun.STATUS_CHOICES
    TRIGGER_CHOICES = RCCARC2ImportRun.TRIGGER_CHOICES

    config = models.ForeignKey(RCCCPCImportConfig, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="queued")
    trigger = models.CharField(max_length=12, choices=TRIGGER_CHOICES)
    stations = models.JSONField(default=list)
    country = models.CharField(max_length=80, default="")
    catalogue_url = models.URLField(max_length=700, blank=True)
    import_all_stations = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)
    results = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ("-created_at",)


class RCCStationImportLogBase(models.Model):
    LEVEL_CHOICES = [
        ("info", "Info"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    event = models.CharField(max_length=40)
    station = models.CharField(max_length=150, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        abstract = True
        ordering = ("id",)


class RCCARC2ImportLog(RCCStationImportLogBase):
    run = models.ForeignKey(RCCARC2ImportRun, on_delete=models.CASCADE, related_name="logs")


class RCCCPCImportLog(RCCStationImportLogBase):
    run = models.ForeignKey(RCCCPCImportRun, on_delete=models.CASCADE, related_name="logs")


class RCCSeasonalMapImportConfig(models.Model):
    singleton_key = models.CharField(max_length=30, unique=True, default="seasonal-maps", editable=False)
    catalogue_url = models.URLField(
        max_length=700,
        default=(
            "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
            "statisticalanalysis/Precipitation/Gridded_Observation/catalog.xml"
        ),
    )
    enabled = models.BooleanField(default=False)
    interval_hours = models.PositiveSmallIntegerField(default=168)
    import_all_maps = models.BooleanField(default=False)
    discovered_maps = models.JSONField(default=list, blank=True)
    selected_maps = models.JSONField(default=list, blank=True)
    discovered_at = models.DateTimeField(null=True, blank=True)
    discovery_error = models.TextField(blank=True)

    def __str__(self):
        return "Seasonal rainfall climatology map importer"


class RCCSeasonalMapImportRun(models.Model):
    STATUS_CHOICES = BASE_IMPORT_STATUS_CHOICES
    TRIGGER_CHOICES = RCCARC2ImportRun.TRIGGER_CHOICES

    config = models.ForeignKey(RCCSeasonalMapImportConfig, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="queued")
    trigger = models.CharField(max_length=12, choices=TRIGGER_CHOICES)
    maps = models.JSONField(default=list)
    catalogue_url = models.URLField(max_length=700)
    import_all_maps = models.BooleanField(default=False)
    results = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ("-created_at",)


class RCCSeasonalMapAsset(models.Model):
    filename = models.CharField(max_length=80, unique=True)
    season = models.CharField(max_length=3)
    variant = models.CharField(max_length=10)
    source_url = models.URLField(max_length=700)
    object_name = models.CharField(max_length=500)
    checksum_sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    synced_at = models.DateTimeField()

    class Meta:
        ordering = ("filename",)


class RCCClimateIndexAsset(models.Model):
    legacy_index = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=240)
    scope = models.CharField(max_length=30)
    period = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    source_url = models.URLField(max_length=700)
    active = models.BooleanField(default=True)
    object_name = models.CharField(max_length=500, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    synced_at = models.DateTimeField(null=True, blank=True)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ("legacy_index",)


@register_snippet
class RCCReferenceClimatology(models.Model):
    """Monthly station normals mirrored from the legacy African RCC service."""

    country_code = models.CharField(max_length=3)
    country = models.CharField(max_length=100)
    station_id = models.CharField(max_length=20)
    station_name = models.CharField(max_length=120)
    period_start = models.PositiveSmallIntegerField()
    period_end = models.PositiveSmallIntegerField()
    monthly_data = models.JSONField(default=list)
    source_url = models.URLField(max_length=700)
    synced_at = models.DateTimeField(auto_now=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("country_code"),
                FieldPanel("country"),
                FieldPanel("station_id"),
                FieldPanel("station_name"),
            ],
            heading=_("Station"),
        ),
        MultiFieldPanel(
            [FieldPanel("period_start"), FieldPanel("period_end")],
            heading=_("Reference period"),
        ),
        FieldPanel("monthly_data"),
        FieldPanel("source_url"),
    ]

    class Meta:
        ordering = ("country", "station_name", "period_start")
        constraints = [
            models.UniqueConstraint(
                fields=("country_code", "station_id", "period_start", "period_end"),
                name="unique_rcc_station_climatology_period",
            )
        ]
        verbose_name = _("RCC reference climatology")
        verbose_name_plural = _("RCC reference climatologies")

    def __str__(self):
        return f"{self.country} — {self.station_name} ({self.period_start}–{self.period_end})"

    @property
    def period_label(self):
        return f"{self.period_start}–{self.period_end}"

    @property
    def is_available(self):
        return bool(self.synced_at and self.monthly_data)


class RCCClimateIndexVersion(models.Model):
    asset = models.ForeignKey(RCCClimateIndexAsset, on_delete=models.CASCADE, related_name="versions")
    source_url = models.URLField(max_length=700)
    object_name = models.CharField(max_length=500)
    checksum_sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    synced_at = models.DateTimeField()

    class Meta:
        ordering = ("-synced_at",)
        constraints = [
            models.UniqueConstraint(fields=("asset", "checksum_sha256"), name="unique_climate_index_version"),
        ]


class RCCClimateIndexImportConfig(models.Model):
    singleton_key = models.CharField(max_length=30, unique=True, default="climate-indices", editable=False)
    enabled = models.BooleanField(default=False)
    interval_hours = models.PositiveSmallIntegerField(default=168)

    def __str__(self):
        return "Climate indices and historical graphs importer"


class RCCClimateIndexImportRun(models.Model):
    STATUS_CHOICES = BASE_IMPORT_STATUS_CHOICES
    TRIGGER_CHOICES = RCCARC2ImportRun.TRIGGER_CHOICES

    config = models.ForeignKey(RCCClimateIndexImportConfig, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="queued")
    trigger = models.CharField(max_length=12, choices=TRIGGER_CHOICES)
    asset_ids = models.JSONField(default=list)
    results = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ("-created_at",)


class RCCEIN15ImportConfig(models.Model):
    singleton_key = models.CharField(max_length=20, unique=True, default="ein15", editable=False)
    catalogue_url = models.URLField(
        max_length=700,
        default="http://sgbd.acmad.org:8080/thredds/catalog/ein15output/catalog.xml",
    )
    enabled = models.BooleanField(default=False)
    interval_hours = models.PositiveSmallIntegerField(default=168)
    discovered_files = models.JSONField(default=list, blank=True)
    selected_files = models.JSONField(default=list, blank=True)
    discovered_at = models.DateTimeField(null=True, blank=True)
    discovery_error = models.TextField(blank=True)

    def __str__(self):
        return "EIN15 regional model output importer"


class RCCEIN15ImportRun(models.Model):
    STATUS_CHOICES = BASE_IMPORT_STATUS_CHOICES
    TRIGGER_CHOICES = RCCARC2ImportRun.TRIGGER_CHOICES

    config = models.ForeignKey(RCCEIN15ImportConfig, on_delete=models.CASCADE, related_name="runs")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="queued")
    trigger = models.CharField(max_length=12, choices=TRIGGER_CHOICES)
    files = models.JSONField(default=list)
    catalogue_url = models.URLField(max_length=700)
    results = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ("-created_at",)


class RCCEIN15Asset(models.Model):
    filename = models.CharField(max_length=100, unique=True)
    source_url = models.URLField(max_length=700)
    object_name = models.CharField(max_length=500)
    checksum_sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()
    source_last_modified = models.CharField(max_length=100, blank=True)
    synced_at = models.DateTimeField()

    class Meta:
        ordering = ("filename",)


class ServiceIndexPage(MetadataPageMixin, Page):
    parent_page_types = ['home.HomePage']
    subpage_types = ['services.ServicePage']
    template = "subpages_listing.html"
    
    listing_heading = models.CharField(max_length=255, default="Explore our Services",
                                       verbose_name=_("Services listing Heading"))
    max_count = 1
    is_services_index = True
    
    content_panels = Page.content_panels + [
        FieldPanel("listing_heading")
    ]
    
    class Meta:
        verbose_name = _('Service List Page')
        verbose_name_plural = _('Service List Pages')
    
    def get_meta_image(self):
        meta_image = super().get_meta_image()
        
        if not meta_image:
            parent = self.get_parent()
            ## get from homepage
            if hasattr(parent, 'get_meta_image'):
                meta_image = parent.get_meta_image()
        
        return meta_image
    
    def get_meta_description(self):
        meta_description = super().get_meta_description()
        
        if not meta_description:
            parent = self.get_parent()
            # get from homepage
            if hasattr(parent, 'get_meta_description'):
                meta_description = parent.get_meta_description()
        
        return meta_description
    
    @cached_property
    def service_pages(self):
        service_pages = ServicePage.objects.live().descendant_of(self).order_by('service__order')
        return service_pages


class ServicePage(AbstractBannerWithIntroPage):
    template = 'services/service_page.html'
    rcc_template = 'services/rcc_service_page.html'
    rcc_service_name = 'Regional Climate Center'
    parent_page_types = ['services.ServiceIndexPage']
    subpage_types = [
        'flex_page.FlexPage',
        'services.OnTheJobTrainingPage',
        'services.RCCClimateMonitoringPage',
        'services.RCCClimateProductsPage',
        'services.RCCDataServicesPage',
    ]
    show_in_menus_default = True

    introduction_title = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Introduction Title"),
        help_text=_("Optional introduction section title"),
    )
    service = models.OneToOneField(ServiceCategory, on_delete=models.PROTECT, verbose_name=_("Service"))

    sector_heading = models.CharField(
        max_length=180,
        blank=True,
        default="",
        verbose_name=_("Sector section heading"),
    )
    sector_introduction = RichTextField(
        blank=True,
        default="",
        features=SUMMARY_RICHTEXT_FEATURES,
        verbose_name=_("Sector section introduction"),
    )
    service_sectors = StreamField(
        [("sector", local_blocks.SectorServiceBlock())],
        blank=True,
        null=True,
        use_json_field=True,
        verbose_name=_("Service sectors"),
    )
    
    what_we_do_items = StreamField([
        ('what_we_do', base_blocks.WhatWeDoBlock()),
    ], null=True, blank=True, use_json_field=True)
    
    what_we_do_button_text = models.TextField(max_length=20, blank=True, null=True,
                                              verbose_name=_("What we do button text"))
    what_we_do_button_link = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("What we do button link")
    )
    
    projects_description = RichTextField(help_text=_("Projects description text"), blank=True, null=True,
                                         features=SUMMARY_RICHTEXT_FEATURES, verbose_name=_("Project Description"))
    
    feature_block_items = StreamField([
        ('feature_item', base_blocks.FeatureBlock()),
    ], null=True, blank=True, use_json_field=True, verbose_name=_("Feature block items"))
    
    extra_content = StreamField(
        [
            ("title_text", blocks.TitleTextBlock()),
            ("title_text_image", blocks.TitleTextImageBlock()),
            ("accordion", blocks.AccordionBlock()),
            ("table", blocks.TableInfoBlock()),
        ],
        null=True,
        blank=True
    )
    
    youtube_playlist = models.ForeignKey(
        YoutubePlaylist,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Youtube playlist")
    )
    
    content_panels = Page.content_panels + [
        FieldPanel('service'),
        *AbstractBannerWithIntroPage.content_panels,
        MultiFieldPanel([
            FieldPanel("sector_heading"),
            FieldPanel("sector_introduction"),
            FieldPanel("service_sectors"),
        ], heading=_("Sector-based service content")),
        MultiFieldPanel([
            FieldPanel('what_we_do_items'),
            FieldPanel('what_we_do_button_text'),
            PageChooserPanel('what_we_do_button_link'),
        ],
            heading=_("What we do in this Service section"),
        ),
        FieldPanel('feature_block_items'),
        FieldPanel("extra_content"),
        MultiFieldPanel([
            FieldPanel('projects_description'),
        ],
            heading=_("Projects Section"),
        ),
        FieldPanel('youtube_playlist'),
        InlinePanel('applications', heading=_("Applications"), label=_("Heading")),
    ]
    
    class Meta:
        verbose_name = _('Service Page')
        verbose_name_plural = _('Service Pages')
        ordering = ['service__order']

    def get_template(self, request, *args, **kwargs):
        """Use the dedicated landing page for the Regional Climate Center."""
        if self.service.name == self.rcc_service_name:
            return self.rcc_template
        return super().get_template(request, *args, **kwargs)
    
    @cached_property
    def products(self):
        """
        Get list of products related to this service
        :return: products list
        """
        # Get all products related to this service
        national_products = ProductPage.objects.filter(
            Q(service=self.service) | Q(other_services__in=[self.service]), live=True).distinct()
        sub_national_products = SubNationalProductPage.objects.filter(Q(service=self.service), live=True).distinct()
        
        return list(national_products) + list(sub_national_products)
    
    @cached_property
    def core_products(self):
        """
        Get list of core products related to this service
        :return: core products list
        """
        # Get all products related to this service
        national_products = ProductPage.objects.filter(service=self.service, live=True)
        sub_national_products = SubNationalProductPage.objects.filter(service=self.service, live=True)
        
        return list(national_products) + list(sub_national_products)
    
    @cached_property
    def flex_pages(self):
        """
        Get list of flex pages related to this service
        """
        flex_pages = FlexPage.objects.live().descendant_of(self)
        
        return flex_pages

    @cached_property
    def data_services_page(self):
        """Return the published RCC data catalogue below this service page."""
        return RCCDataServicesPage.objects.live().child_of(self).first()

    @cached_property
    def climate_products_page(self):
        """Return the published RCC climate-products catalogue below this page."""
        return RCCClimateProductsPage.objects.live().child_of(self).first()

    @cached_property
    def climate_monitoring_page(self):
        """Return the published RCC climate-monitoring function page."""
        return RCCClimateMonitoringPage.objects.live().child_of(self).first()
    
    @cached_property
    def listing_image(self):
        if self.banner_image:
            return self.banner_image
        if self.introduction_image:
            return self.introduction_image
        return None
    
    @cached_property
    def projects(self):
        """
        Get list of projects related to this service
        :return: projects list
        """
        # Get all projects related to this service
        projects = ServiceProject.objects.filter(service=self.service, project__live=True)
        return projects
    
    @cached_property
    def events(self):
        """
        Get list of events related to this service and not archived
        :return: events list
        """
        events = EventPage.objects.live().filter(
            category__in=[self.service], is_archived=False, is_hidden=False).order_by('-date_from')[:3]
        
        return events
    
    @cached_property
    def latest_updates(self):
        updates = []
        
        news = NewsPage.objects.live().filter(services__in=[self.service]).order_by('-is_featured', '-date')[:2]
        
        publications = PublicationPage.objects.live().filter(categories__in=[self.service]).order_by(
            '-featured',
            '-publication_date')
        
        if news.exists():
            if news.count() > 1:
                # we have 2 news , get 2 publications
                publications = publications[:2]
            else:
                # we have 1 news, get 3 publications
                publications = publications[:3]
            # add news
            updates.extend(news)
        else:
            # no news, get 4 publications
            publications = publications[:4]
        
        # add publications
        updates.extend(publications)
        
        return updates

    @cached_property
    def featured_partners(self):
        """Partners selected for prominent display across the main website."""
        return Partner.objects.filter(visible_on_homepage=True, logo__isnull=False)[:6]
    
    @cached_property
    def nav_menu_icon(self):
        return self.service.icon
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        if self.service.name == self.rcc_service_name:
            from adminboundarymanager.models import AdminBoundarySettings
            from climweb.pages.home.models import HomeMapSettings

            map_settings = HomeMapSettings.for_request(request)
            boundary_settings = AdminBoundarySettings.for_request(request)
            context.update({
                "multi_hazard_api_base_url": map_settings.multi_hazard_api_base_url or "https://multi-hazard.acmad.org",
                "multi_hazard_project_slug": map_settings.multi_hazard_project_slug or "multi-hazard",
                "country_bounds": boundary_settings.combined_countries_bounds,
            })

        if self.youtube_playlist:
            context['youtube_playlist_url'] = self.youtube_playlist.get_playlist_items_api_url(request)
        
        return context


class RCCDataServicesPage(AbstractBannerWithIntroPage):
    template = "services/rcc_data_services_page.html"
    parent_page_types = ["services.ServicePage"]
    subpage_types = []
    max_count_per_parent = 1
    show_in_menus_default = True

    catalogue_notice = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
        verbose_name=_("Catalogue access notice"),
        help_text=_("Explain access restrictions, verification dates and archive status."),
    )
    data_groups = StreamField(
        [("group", local_blocks.RCCDataGroupBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Data service groups"),
    )
    data_request_page = models.ForeignKey(
        "wagtailcore.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Data request page"),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerWithIntroPage.content_panels,
        FieldPanel("catalogue_notice"),
        FieldPanel("data_groups"),
        PageChooserPanel("data_request_page"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        # Imported here to avoid coupling the services and products model modules
        # while still resolving the current Wagtail URL for each local archive.
        from climweb.pages.products.models import ProductPage

        product_urls = {}
        for key, slug in (
            ("rdt_product_url", "thunderstorm-and-nowcasting"),
            ("itd_product_url", "itd-and-itcz-monitoring"),
        ):
            product_page = ProductPage.objects.live().filter(slug=slug).first()
            product_urls[key] = (
                product_page.get_url(request=request) if product_page else ""
            )

        context.update(product_urls)
        return context

    class Meta:
        verbose_name = _("RCC Data Services Page")


class RCCClimateProductsPage(AbstractBannerWithIntroPage):
    template = "services/rcc_climate_products_page.html"
    parent_page_types = ["services.ServicePage"]
    subpage_types = []
    max_count_per_parent = 1
    show_in_menus_default = True

    introduction_title = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Introduction Title"),
        help_text=_("Optional introduction section title"),
    )
    introduction_text = RichTextField(
        blank=True,
        default="",
        features=SUMMARY_RICHTEXT_FEATURES,
        verbose_name=_("Introduction text"),
        help_text=_("Optional introduction section description"),
    )

    @cached_property
    def products(self):
        parent = self.get_parent().specific
        return parent.products if isinstance(parent, ServicePage) else []

    class Meta:
        verbose_name = _("RCC Climate Products Page")


class RCCClimateMonitoringPage(AbstractBannerWithIntroPage):
    template = "services/rcc_climate_monitoring_page.html"
    parent_page_types = ["services.ServicePage"]
    subpage_types = []
    max_count_per_parent = 1
    show_in_menus_default = True

    diagnostic_product_definitions = (
        {
            "key": "annual",
            "slugs": ("annual-state-of-the-climate-report",),
            "cadence": _("Annual assessment"),
            "title": _("Annual State of the Climate Report"),
            "summary": _(
                "Observed climate conditions, significant extremes, impacts "
                "and long-term trends across Africa."
            ),
        },
        {
            "key": "monthly",
            "slugs": ("monthly-climate-diagnostic-bulletin",),
            "cadence": _("Monthly diagnostics"),
            "title": _("Monthly Climate Diagnostic Bulletin"),
            "summary": _(
                "Rainfall totals, anomalies, percent of normal and rainy-day "
                "diagnostics for the continent."
            ),
        },
        {
            "key": "dekadal",
            "slugs": ("dekadal-weather-forecast", "dekadal-climate-bulletin"),
            "cadence": _("10-day assessment"),
            "title": _("Dekadal Climate Bulletin"),
            "summary": _(
                "Ten-day climate conditions and technical guidance supporting "
                "rapid regional assessment."
            ),
        },
    )

    rainfall_product_definitions = (
        {
            "key": "daily-rainfall",
            "slugs": ("daily-rainfall-monitoring",),
            "cadence": _("Daily monitoring"),
            "title": _("Daily Rainfall Monitoring"),
            "summary": _(
                "Observed rainfall totals and spatial patterns supporting "
                "day-to-day monitoring across Africa."
            ),
        },
        {
            "key": "seasonal-onset",
            "slugs": ("rainfall-and-seasonal-onset-monitoring",),
            "cadence": _("Seasonal tracking"),
            "title": _("Rainfall and Seasonal Onset Monitoring"),
            "summary": _(
                "Tracks rainfall progression and the onset of the growing "
                "season for climate-sensitive planning."
            ),
        },
        {
            "key": "five-day-rainfall",
            "slugs": ("five-day-rainfall-probability-forecast",),
            "cadence": _("Five-day outlook"),
            "title": _("5-Day Rainfall Probability Forecast"),
            "summary": _(
                "Short-range rainfall probabilities for anticipating wet and "
                "dry conditions."
            ),
        },
        {
            "key": "rainfall-exceedance",
            "slugs": ("seasonal-rainfall-probability-of-exceedance",),
            "cadence": _("Seasonal outlook"),
            "title": _("Seasonal Rainfall Probability of Exceedance"),
            "summary": _(
                "Probability guidance showing where seasonal rainfall may "
                "exceed decision-relevant thresholds."
            ),
        },
    )

    watch_product_definitions = (
        {
            "key": "climate-watch",
            "slugs": ("climate-watch-bulletin",),
            "cadence": _("Climate advisory"),
            "title": _("Climate Watch Bulletin"),
            "summary": _(
                "Climate information and advisories focused on significant "
                "anomalies, extremes and their potential impacts."
            ),
        },
        {
            "key": "atmospheric-analysis",
            "slugs": ("atmospheric-analysis",),
            "cadence": _("Synoptic analysis"),
            "title": _("Atmospheric Analysis"),
            "summary": _(
                "Analysis of large-scale circulation and atmospheric drivers "
                "affecting African climate."
            ),
        },
        {
            "key": "itd-itcz",
            "slugs": ("itd-and-itcz-monitoring",),
            "cadence": _("Position monitoring"),
            "title": _("ITD and ITCZ Monitoring"),
            "summary": _(
                "Operational monitoring of tropical convergence features that "
                "shape West African rainfall."
            ),
        },
    )

    cryosphere_product_definitions = (
        {
            "key": "cryosphere",
            "slugs": ("cryosphere-and-african-mountain-glaciers",),
            "cadence": _("Specialized monitoring"),
            "title": _("Cryosphere and African Mountain Glaciers"),
            "summary": _(
                "Evidence and assessments of glacier and cryosphere change in "
                "Africa's mountain environments."
            ),
        },
    )

    def _resolve_products(self, definitions, pages_by_slug):
        products = []
        for definition in definitions:
            page = next(
                (
                    pages_by_slug[slug]
                    for slug in definition["slugs"]
                    if slug in pages_by_slug
                ),
                None,
            )
            item = dict(definition)
            item["page"] = page
            item["latest"] = page.all_products.first() if page else None
            products.append(item)
        return products

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        product_groups = (
            self.diagnostic_product_definitions,
            self.rainfall_product_definitions,
            self.watch_product_definitions,
            self.cryosphere_product_definitions,
        )
        slugs = {
            slug
            for definitions in product_groups
            for definition in definitions
            for slug in definition["slugs"]
        }
        pages_by_slug = {
            page.slug: page
            for page in ProductPage.objects.live().filter(slug__in=slugs)
        }
        context["diagnostic_products"] = self._resolve_products(
            self.diagnostic_product_definitions,
            pages_by_slug,
        )
        context["rainfall_products"] = self._resolve_products(
            self.rainfall_product_definitions,
            pages_by_slug,
        )
        context["watch_products"] = self._resolve_products(
            self.watch_product_definitions,
            pages_by_slug,
        )
        context["cryosphere_product"] = self._resolve_products(
            self.cryosphere_product_definitions,
            pages_by_slug,
        )[0]
        return context

    class Meta:
        verbose_name = _("RCC Climate Monitoring Page")


class OnTheJobTrainingPage(AbstractBannerWithIntroPage):
    template = "services/on_the_job_training_page.html"
    parent_page_types = ["home.HomePage", "services.ServicePage"]
    subpage_types = []
    show_in_menus_default = True

    objectives = RichTextField(features=SUMMARY_RICHTEXT_FEATURES)
    eligibility = RichTextField(features=SUMMARY_RICHTEXT_FEATURES)
    duration = models.CharField(max_length=120, default="2-6 months")
    location = models.CharField(max_length=160, default="ACMAD Headquarters, Niamey, Niger")
    languages = models.CharField(max_length=120, default="English and French")
    benefits = RichTextField(features=SUMMARY_RICHTEXT_FEATURES)
    training_modules = StreamField(
        [("module", local_blocks.TrainingModuleBlock())],
        blank=True,
        use_json_field=True,
    )
    application_introduction = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
    )
    application_steps = StreamField(
        [("step", local_blocks.ApplicationStepBlock())],
        blank=True,
        use_json_field=True,
    )
    application_email = models.EmailField(default="secretariat@acmad.org")
    reports_introduction = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
    )
    visitor_reports = StreamField(
        [("report", local_blocks.VisitorReportBlock())],
        blank=True,
        use_json_field=True,
    )
    testimonials = StreamField(
        [("testimony", local_blocks.TrainingTestimonialBlock())],
        blank=True,
        use_json_field=True,
    )
    gallery = StreamField(
        [("item", local_blocks.TrainingGalleryItemBlock())],
        blank=True,
        use_json_field=True,
    )
    accommodation_introduction = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
    )
    accommodation_options = StreamField(
        [("accommodation", local_blocks.TrainingAccommodationBlock())],
        blank=True,
        use_json_field=True,
    )
    brochure = models.ForeignKey(
        "wagtaildocs.Document",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    PARTICIPANT_MAP_SCOPE_BOTH = "both"
    PARTICIPANT_MAP_SCOPE_OJT = "ojt"
    PARTICIPANT_MAP_SCOPE_SECONDMENT = "secondment"
    PARTICIPANT_MAP_SCOPE_CHOICES = (
        (PARTICIPANT_MAP_SCOPE_BOTH, _("On-the-job training and secondment")),
        (PARTICIPANT_MAP_SCOPE_OJT, _("On-the-job training only")),
        (PARTICIPANT_MAP_SCOPE_SECONDMENT, _("Secondment only")),
    )

    show_participant_map = models.BooleanField(
        default=False,
        verbose_name=_("Show participant map"),
        help_text=_("Display an Africa choropleth of participants per country, "
                    "built from the Capacity Building Participants register."),
    )
    participant_map_heading = models.CharField(
        max_length=120,
        default="Where our participants come from",
        verbose_name=_("Participant map heading"),
    )
    participant_map_introduction = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
        verbose_name=_("Participant map introduction"),
    )
    participant_map_scope = models.CharField(
        max_length=20,
        choices=PARTICIPANT_MAP_SCOPE_CHOICES,
        default=PARTICIPANT_MAP_SCOPE_BOTH,
        verbose_name=_("Participants to include"),
    )
    participant_map_date_from = models.DateField(
        null=True, blank=True, verbose_name=_("From date"),
        help_text=_("Optional. Only count engagements active on or after this date."),
    )
    participant_map_date_to = models.DateField(
        null=True, blank=True, verbose_name=_("To date"),
        help_text=_("Optional. Only count engagements that started on or before this date."),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerWithIntroPage.content_panels,
        MultiFieldPanel(
            [
                FieldPanel("objectives"),
                FieldPanel("eligibility"),
                FieldPanel("duration"),
                FieldPanel("location"),
                FieldPanel("languages"),
                FieldPanel("benefits"),
            ],
            heading=_("Programme overview"),
        ),
        FieldPanel("training_modules"),
        MultiFieldPanel(
            [
                FieldPanel("application_introduction"),
                FieldPanel("application_steps"),
                FieldPanel("application_email"),
            ],
            heading=_("How to apply"),
        ),
        MultiFieldPanel(
            [FieldPanel("reports_introduction"), FieldPanel("visitor_reports")],
            heading=_("Visitor reports"),
        ),
        FieldPanel("testimonials"),
        FieldPanel("gallery"),
        MultiFieldPanel(
            [
                FieldPanel("accommodation_introduction"),
                FieldPanel("accommodation_options"),
            ],
            heading=_("Accommodation"),
        ),
        FieldPanel("brochure"),
        MultiFieldPanel(
            [
                FieldPanel("show_participant_map"),
                FieldPanel("participant_map_heading"),
                FieldPanel("participant_map_introduction"),
                FieldPanel("participant_map_scope"),
                FieldPanel("participant_map_date_from"),
                FieldPanel("participant_map_date_to"),
            ],
            heading=_("Participant map"),
        ),
    ]

    class Meta:
        verbose_name = _("On-the-Job Training Page")

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        if self.show_participant_map:
            from climweb.base.models.participants import build_participant_map_context

            if self.participant_map_scope == self.PARTICIPANT_MAP_SCOPE_BOTH:
                categories = None
            else:
                categories = [self.participant_map_scope]

            context.update(build_participant_map_context(
                map_dom_id="ojt-participant-map",
                categories=categories,
                date_from=self.participant_map_date_from,
                date_to=self.participant_map_date_to,
                show_legend=True,
                request=request,
            ))

        return context


class ServiceApplication(Orderable):
    page = ParentalKey(ServicePage, on_delete=models.CASCADE, related_name="applications")
    application = models.ForeignKey("base.Application", on_delete=models.CASCADE, verbose_name=_("Application"))
