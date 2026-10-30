from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from timezone_field import TimeZoneField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail_color_panel.fields import ColorField

from climweb.base.mixins import MetadataPageMixin
from .blocks import (
    CopDocumentBlock,
    CopGalleryImageBlock,
    CopPanelistBlock,
    CopPartnerBlock,
)


SUMMARY_FEATURES = getattr(settings, "SUMMARY_RICHTEXT_FEATURES")


class CopIndexPage(MetadataPageMixin, Page):
    template = "cop/cop_index_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types = ["cop.CopEditionPage"]
    max_count = 1
    show_in_menus = True

    introduction = RichTextField(
        blank=True,
        features=SUMMARY_FEATURES,
        verbose_name=_("Introduction"),
    )
    archive_heading = models.CharField(
        max_length=120,
        default="Previous COP editions",
        verbose_name=_("Archive heading"),
    )

    content_panels = Page.content_panels + [
        FieldPanel("introduction"),
        FieldPanel("archive_heading"),
    ]

    class Meta:
        verbose_name = _("COP landing page")

    @cached_property
    def editions(self):
        return CopEditionPage.objects.live().child_of(self).order_by(
            "-is_current", "-cop_number", "-start_date"
        )

    @cached_property
    def current_edition(self):
        return self.editions.filter(is_current=True).first()

    @cached_property
    def previous_editions(self):
        current = self.current_edition
        editions = CopEditionPage.objects.live().child_of(self).order_by(
            "-cop_number", "-start_date"
        )
        if current:
            editions = editions.exclude(pk=current.pk)
        return editions

    def get_meta_image(self):
        meta_image = super().get_meta_image()
        if not meta_image and self.current_edition:
            return self.current_edition.hero_image or self.current_edition.logo
        return meta_image


class CopEditionPage(MetadataPageMixin, Page):
    template = "cop/cop_edition_page.html"
    parent_page_types = ["cop.CopIndexPage"]
    subpage_types = ["cop.CopSideEventPage"]

    cop_number = models.PositiveSmallIntegerField(verbose_name=_("COP number"))
    is_current = models.BooleanField(
        default=False,
        verbose_name=_("Current COP"),
        help_text=_("Show this edition as the current COP on the landing page."),
    )
    start_date = models.DateField(verbose_name=_("Start date"))
    end_date = models.DateField(verbose_name=_("End date"))
    host_city = models.CharField(max_length=120, verbose_name=_("Host city"))
    host_country = models.CharField(max_length=120, verbose_name=_("Host country"))
    venue = models.CharField(max_length=180, blank=True, verbose_name=_("Venue"))
    official_website_url = models.URLField(blank=True, verbose_name=_("Official COP website"))

    acmad_participation = RichTextField(
        features=SUMMARY_FEATURES,
        verbose_name=_("ACMAD at this COP"),
    )
    about = RichTextField(blank=True, features=SUMMARY_FEATURES, verbose_name=_("About the COP"))
    objectives = RichTextField(blank=True, features=SUMMARY_FEATURES, verbose_name=_("Objectives"))
    expected_outcomes = RichTextField(
        blank=True,
        features=SUMMARY_FEATURES,
        verbose_name=_("Expected outcomes"),
    )

    logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("COP logo"),
    )
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Hero image"),
    )
    primary_color = ColorField(default="#0b5a46", verbose_name=_("Primary colour"))
    secondary_color = ColorField(default="#d6a83b", verbose_name=_("Secondary colour"))
    accent_color = ColorField(default="#e6f3ee", verbose_name=_("Accent colour"))
    text_on_primary_color = ColorField(default="#ffffff", verbose_name=_("Text on primary colour"))

    schedule_documents = StreamField(
        [("document", CopDocumentBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Schedules and programme documents"),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("cop_number"),
                FieldPanel("is_current"),
                FieldPanel("start_date"),
                FieldPanel("end_date"),
                FieldPanel("host_city"),
                FieldPanel("host_country"),
                FieldPanel("venue"),
                FieldPanel("official_website_url"),
            ],
            heading=_("Edition details"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("acmad_participation"),
                FieldPanel("about"),
                FieldPanel("objectives"),
                FieldPanel("expected_outcomes"),
                FieldPanel("schedule_documents"),
            ],
            heading=_("COP content"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("logo"),
                FieldPanel("hero_image"),
                FieldPanel("primary_color"),
                FieldPanel("secondary_color"),
                FieldPanel("accent_color"),
                FieldPanel("text_on_primary_color"),
            ],
            heading=_("COP visual theme"),
        ),
    ]

    class Meta:
        verbose_name = _("COP edition")

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": _("End date must be on or after the start date.")})

    @cached_property
    def side_events(self):
        return CopSideEventPage.objects.live().child_of(self).order_by(
            "start_datetime", "side_event_number", "title"
        )

    def get_meta_image(self):
        return super().get_meta_image() or self.hero_image or self.logo


class CopSideEventPage(MetadataPageMixin, Page):
    template = "cop/cop_side_event_page.html"
    parent_page_types = ["cop.CopEditionPage"]
    subpage_types = []

    side_event_number = models.PositiveSmallIntegerField(verbose_name=_("Side-event number"))
    start_datetime = models.DateTimeField(verbose_name=_("Start date and time"))
    end_datetime = models.DateTimeField(verbose_name=_("End date and time"))
    timezone = TimeZoneField(
        default="Africa/Niamey",
        choices_display="WITH_GMT_OFFSET",
        use_pytz=True,
        verbose_name=_("Timezone"),
    )
    venue = models.CharField(max_length=180, verbose_name=_("Venue or pavilion"))
    summary = RichTextField(features=SUMMARY_FEATURES, verbose_name=_("Summary"))
    description = RichTextField(blank=True, features=SUMMARY_FEATURES, verbose_name=_("Description"))
    objectives = RichTextField(blank=True, features=SUMMARY_FEATURES, verbose_name=_("Objectives"))
    participants = RichTextField(
        blank=True,
        features=SUMMARY_FEATURES,
        verbose_name=_("Participants and invited organisations"),
    )
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Featured image"),
    )
    concept_note = models.ForeignKey(
        "base.CustomDocumentModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Concept note"),
        help_text=_("Concept note for this side event, if available."),
    )
    presentations = StreamField(
        [("presentation", CopDocumentBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Presentation documents"),
    )
    additional_documents = StreamField(
        [("document", CopDocumentBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Other documents"),
    )
    panelists = StreamField(
        [("panelist", CopPanelistBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Panelists and speakers"),
    )
    gallery = StreamField(
        [("image", CopGalleryImageBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Picture gallery"),
    )
    partners = StreamField(
        [("partner", CopPartnerBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Partner organisations"),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("side_event_number"),
                FieldPanel("start_datetime"),
                FieldPanel("end_datetime"),
                FieldPanel("timezone"),
                FieldPanel("venue"),
                FieldPanel("featured_image"),
            ],
            heading=_("Side-event details"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("summary"),
                FieldPanel("description"),
                FieldPanel("objectives"),
                FieldPanel("participants"),
            ],
            heading=_("Content"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("concept_note"),
                FieldPanel("presentations"),
                FieldPanel("additional_documents"),
            ],
            heading=_("Documents"),
        ),
        FieldPanel("panelists"),
        FieldPanel("gallery"),
        FieldPanel("partners"),
    ]

    class Meta:
        verbose_name = _("COP side event")

    def clean(self):
        super().clean()
        if self.start_datetime and self.end_datetime and self.end_datetime <= self.start_datetime:
            raise ValidationError({
                "end_datetime": _("End time must be after the start time.")
            })

    @cached_property
    def cop_edition(self):
        parent = self.get_parent()
        return parent.specific if parent else None

    @property
    def local_start_datetime(self):
        return self.start_datetime.astimezone(self.timezone)

    @property
    def local_end_datetime(self):
        return self.end_datetime.astimezone(self.timezone)

    def get_meta_image(self):
        meta_image = super().get_meta_image() or self.featured_image
        if not meta_image and self.cop_edition:
            meta_image = self.cop_edition.hero_image or self.cop_edition.logo
        return meta_image

