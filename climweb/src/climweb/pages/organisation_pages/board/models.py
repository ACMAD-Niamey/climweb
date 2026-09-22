from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page

from climweb.base.models import AbstractBannerPage
from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES


class BoardPage(AbstractBannerPage):
    template = "board/board_page.html"
    parent_page_types = ["organisation.OrganisationIndexPage"]
    subpage_types = ["board.BoardPresidentPage"]
    show_in_menus_default = True
    max_count = 1

    introduction_heading = models.CharField(
        max_length=100,
        blank=True,
        default=_("Our governance"),
        verbose_name=_("Introduction heading"),
    )
    introduction_title = models.CharField(
        max_length=150,
        blank=True,
        default=_("Meet the Board of Governors"),
        verbose_name=_("Introduction title"),
    )
    introduction_text = RichTextField(
        features=SUMMARY_RICHTEXT_FEATURES,
        blank=True,
        verbose_name=_("Introduction text"),
    )

    content_panels = Page.content_panels + [
        *AbstractBannerPage.content_panels,
        MultiFieldPanel(
            [
                FieldPanel("introduction_heading"),
                FieldPanel("introduction_title"),
                FieldPanel("introduction_text"),
            ],
            heading=_("Introduction section"),
        ),
        InlinePanel(
            "board_members",
            heading=_("Board members"),
            label=_("Board member"),
            help_text=_("Add and drag board members into the order in which they should appear."),
        ),
    ]

    @cached_property
    def president_page(self):
        return BoardPresidentPage.objects.child_of(self).live().first()

    class Meta:
        verbose_name = _("Board of Governors Page")


class BoardMember(Orderable):
    page = ParentalKey(BoardPage, on_delete=models.CASCADE, related_name="board_members")
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    role = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("Role or position"),
        help_text=_("For example: Governor for Ghana or Permanent Secretary."),
    )
    country = models.CharField(max_length=100, blank=True, verbose_name=_("Country"))
    biography = RichTextField(
        features=SUMMARY_RICHTEXT_FEATURES,
        blank=True,
        verbose_name=_("Short biography"),
    )
    photo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Portrait"),
        help_text=_("A high-quality square portrait works best."),
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
        FieldPanel("country"),
        FieldPanel("biography"),
        FieldPanel("photo"),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Board member")
        verbose_name_plural = _("Board members")

    def __str__(self):
        return self.name


class BoardPresidentPage(AbstractBannerPage):
    template = "board/board_president_page.html"
    parent_page_types = ["board.BoardPage"]
    subpage_types = []
    show_in_menus_default = False
    max_count_per_parent = 1

    name = models.CharField(max_length=100, verbose_name=_("President's name"))
    role = models.CharField(
        max_length=150,
        default=_("President of the Board of Governors"),
        verbose_name=_("Title"),
    )
    country = models.CharField(max_length=100, blank=True, verbose_name=_("Country"))
    photo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Portrait"),
        help_text=_("A high-quality portrait, ideally at least 900px wide."),
    )
    biography = RichTextField(verbose_name=_("Biography"))
    vision = RichTextField(verbose_name=_("Vision for ACMAD"))
    video_url = models.URLField(
        blank=True,
        verbose_name=_("Video URL"),
        help_text=_("Paste a YouTube or Vimeo URL. It will be embedded on the page."),
    )
    video_title = models.CharField(
        max_length=150,
        blank=True,
        default=_("A message from the President"),
        verbose_name=_("Video heading"),
    )
    video_caption = models.TextField(blank=True, verbose_name=_("Video caption"))

    content_panels = Page.content_panels + [
        *AbstractBannerPage.content_panels,
        MultiFieldPanel(
            [FieldPanel("name"), FieldPanel("role"), FieldPanel("country"), FieldPanel("photo")],
            heading=_("President profile"),
        ),
        FieldPanel("biography"),
        FieldPanel("vision"),
        MultiFieldPanel(
            [FieldPanel("video_title"), FieldPanel("video_url"), FieldPanel("video_caption")],
            heading=_("President's video"),
        ),
    ]

    class Meta:
        verbose_name = _("Board President Page")
