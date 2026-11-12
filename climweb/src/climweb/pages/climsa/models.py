from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, PageChooserPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from climweb.base.mixins import MetadataPageMixin
from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES

from .blocks import ClimsaOutputBlock


def default_climsa_outputs():
    return [
        {
            "type": "output",
            "value": {
                "number": "0",
                "title": "Continental Steering Committees",
                "description": "Coordination and oversight of the continental ClimSA programme at ACMAD.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "1",
                "title": "Structured user interaction",
                "description": "Stronger interfaces between users, researchers and climate-service providers.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "2",
                "title": "Climate service provision",
                "description": "Reliable regional and national climate services for priority sectors.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "3",
                "title": "Access to climate information",
                "description": "Improved access to climate data, information, products and services.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "4",
                "title": "Capacity development",
                "description": "Enhanced capacity to generate and apply relevant climate information.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "5",
                "title": "Climate-informed decisions",
                "description": "Climate services mainstreamed into regional and national decision-making.",
            },
        },
    ]


def default_climsa_about_outputs():
    return [
        {
            "type": "output",
            "value": {
                "number": "1",
                "title": "Structured user interaction",
                "description": (
                    "Establishing structured user interfaces for agriculture, water, "
                    "health, and disaster management."
                ),
            },
        },
        {
            "type": "output",
            "value": {
                "number": "2",
                "title": "Climate service provision",
                "description": "Enhancing the generation and delivery of climate services.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "3",
                "title": "Access to climate information",
                "description": "Improving access to climate data and information.",
            },
        },
        {
            "type": "output",
            "value": {
                "number": "4",
                "title": "Capacity development",
                "description": (
                    "Building capacity to generate and utilize climate products effectively."
                ),
            },
        },
        {
            "type": "output",
            "value": {
                "number": "5",
                "title": "Climate-informed decisions",
                "description": (
                    "Integrating climate services into policy and decision-making processes."
                ),
            },
        },
    ]


DEFAULT_PROGRAMME_INTRODUCTION = (
    "<p>Climate change and environmental issues are central to the 2030 Agenda for "
    "Sustainable Development and the Paris Agreement on Climate Change. Achieving "
    "sustainable development and mitigating climate change are interconnected goals "
    "that must be pursued simultaneously. Reliable, science-based climate information "
    "is essential to build resilience and effectively manage climate risks, enabling "
    "countries and regions within the OACPS to adapt to the changing climate.</p>"
)


DEFAULT_ABOUT_OVERVIEW = (
    "<p>Climate change and environmental issues are central to the 2030 Agenda for "
    "Sustainable Development and the Paris Agreement on Climate Change. Achieving "
    "sustainable development and mitigating climate change are interconnected goals "
    "that must be pursued simultaneously.</p>"
    "<p>Reliable, science-based climate information is essential to build resilience "
    "and effectively manage climate risks, enabling countries and regions within the "
    "OACPS to adapt to the changing climate. The Intra-ACP Climate Services and related "
    "Applications (ClimSA) is a key initiative funded by the 11th European Development "
    "Fund.</p>"
    "<p>The programme supports the entire climate information services value chain by "
    "providing technical and financial assistance, infrastructure and capacity building. "
    "ClimSA aims to enhance the accessibility and use of climate information and "
    "applications for decision-making across the six regions of the OACPS through eight "
    "Regional Climate Centres.</p>"
    "<p>In March 2021, ACMAD launched a continental-scale project under the ClimSA "
    "programme with support from the African Union Commission as Contracting Authority. "
    "The project focuses on generating and applying climate services in agriculture, "
    "water, health and disaster risk reduction.</p>"
)


class ClimsaHomePage(MetadataPageMixin, Page):
    template = "climsa/climsa_home_page.html"
    parent_page_types = ["home.HomePage"]
    subpage_types = ["climsa.ClimsaAboutPage", "flex_page.FlexPage"]
    max_count = 1
    show_in_menus_default = True

    climsa_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("ClimSA logo"),
        help_text=_("Displayed on the right side of the CLIMSA header."),
    )
    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Hero image"),
    )
    hero_kicker = models.CharField(
        max_length=100,
        blank=True,
        default="Intra-ACP Climate Services and Related Applications Programme",
        verbose_name=_("Hero kicker"),
    )
    hero_heading = models.CharField(
        max_length=180,
        default="Advancing climate services for informed decision-making in Africa",
        verbose_name=_("Hero heading"),
    )
    hero_description = models.TextField(
        max_length=500,
        blank=True,
        default=(
            "Connecting climate science, regional expertise and user needs to strengthen "
            "resilience across African regions."
        ),
        verbose_name=_("Hero description"),
    )
    introduction_heading = models.CharField(
        max_length=150,
        default="About the Programme",
        verbose_name=_("Introduction heading"),
    )
    introduction = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
        default=DEFAULT_PROGRAMME_INTRODUCTION,
        verbose_name=_("Introduction"),
    )
    programme_partners_logo = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Programme partners logo"),
        help_text=_("Displayed alongside the About the Programme introduction."),
    )
    outputs = StreamField(
        [("output", ClimsaOutputBlock())],
        blank=True,
        use_json_field=True,
        default=default_climsa_outputs,
        max_num=6,
        verbose_name=_("Programme outputs"),
    )

    about_page = models.ForeignKey(
        "wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("About Us page"),
    )
    activities_page = models.ForeignKey(
        "wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("Activities page"),
    )
    products_page = models.ForeignKey(
        "wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("Products page"),
    )
    news_page = models.ForeignKey(
        "wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("News page"),
    )
    publications_page = models.ForeignKey(
        "wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("Publications page"),
    )
    events_page = models.ForeignKey(
        "wagtailcore.Page", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+", verbose_name=_("Events page"),
    )

    featured_products = StreamField(
        [("product", blocks.PageChooserBlock(page_type=["products.ProductPage"]))],
        blank=True,
        use_json_field=True,
        max_num=7,
        verbose_name=_("Featured CLIMSA products"),
    )
    featured_news = StreamField(
        [("news", blocks.PageChooserBlock(page_type=["news.NewsPage"]))],
        blank=True,
        use_json_field=True,
        max_num=6,
        verbose_name=_("Featured CLIMSA news"),
    )
    featured_events = StreamField(
        [("event", blocks.PageChooserBlock(page_type=["events.EventPage"]))],
        blank=True,
        use_json_field=True,
        max_num=6,
        verbose_name=_("Featured CLIMSA events"),
    )
    featured_publications = StreamField(
        [("publication", blocks.PageChooserBlock(page_type=["publications.PublicationPage"]))],
        blank=True,
        use_json_field=True,
        max_num=6,
        verbose_name=_("Featured CLIMSA publications"),
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [
                FieldPanel("climsa_logo"),
                FieldPanel("hero_image"),
                FieldPanel("hero_kicker"),
                FieldPanel("hero_heading"),
                FieldPanel("hero_description"),
            ],
            heading=_("Brand and hero"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("introduction_heading"),
                FieldPanel("introduction"),
                FieldPanel("programme_partners_logo"),
            ],
            heading=_("Programme introduction"),
        ),
        FieldPanel("outputs"),
        MultiFieldPanel(
            [
                PageChooserPanel("about_page"),
                PageChooserPanel("activities_page"),
                PageChooserPanel("products_page"),
                PageChooserPanel("news_page"),
                PageChooserPanel("publications_page"),
                PageChooserPanel("events_page"),
            ],
            heading=_("CLIMSA navigation destinations"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("featured_products"),
                FieldPanel("featured_news"),
                FieldPanel("featured_events"),
                FieldPanel("featured_publications"),
            ],
            heading=_("Curated homepage content"),
        ),
    ]

    class Meta:
        verbose_name = _("CLIMSA Home Page")
        verbose_name_plural = _("CLIMSA Home Pages")

    @staticmethod
    def _live_selected_pages(stream_value):
        selected = []
        for block in stream_value:
            page = block.value
            if page and page.live:
                selected.append(page.specific)
        return selected

    @cached_property
    def selected_products(self):
        return self._live_selected_pages(self.featured_products)

    @cached_property
    def selected_news(self):
        return self._live_selected_pages(self.featured_news)

    @cached_property
    def selected_events(self):
        return self._live_selected_pages(self.featured_events)

    @cached_property
    def selected_publications(self):
        return self._live_selected_pages(self.featured_publications)

    def get_meta_image(self):
        return super().get_meta_image() or self.hero_image

    def get_meta_description(self):
        return super().get_meta_description() or self.hero_description


class ClimsaAboutPage(MetadataPageMixin, Page):
    template = "climsa/climsa_about_page.html"
    parent_page_types = ["climsa.ClimsaHomePage"]
    subpage_types = []
    max_count_per_parent = 1
    show_in_menus_default = True

    hero_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Hero image"),
        help_text=_("Optional page-specific hero background image."),
    )
    introduction_heading = models.CharField(
        max_length=150,
        default="About the programme",
        verbose_name=_("Introduction heading"),
    )
    introduction = RichTextField(
        blank=True,
        features=SUMMARY_RICHTEXT_FEATURES,
        default=DEFAULT_ABOUT_OVERVIEW,
        verbose_name=_("Programme overview"),
    )
    outputs_heading = models.CharField(
        max_length=150,
        default="ACMAD's five project outputs",
        verbose_name=_("Outputs heading"),
    )
    outputs = StreamField(
        [("output", ClimsaOutputBlock())],
        blank=True,
        use_json_field=True,
        default=default_climsa_about_outputs,
        max_num=5,
        verbose_name=_("Project outputs"),
    )
    factsheet_heading = models.CharField(
        max_length=150,
        default="Read the ClimSA Programme Factsheet",
        verbose_name=_("Factsheet heading"),
    )
    factsheet_description = models.TextField(
        max_length=300,
        blank=True,
        default=(
            "Explore the programme's goals, beneficiaries, implementing partners and "
            "expected results."
        ),
        verbose_name=_("Factsheet description"),
    )
    factsheet_url = models.URLField(
        blank=True,
        default=(
            "https://www.climsa.org/application/files/4316/3040/3721/"
            "ClimSA_Factsheet_LAY_V4_220321.pdf"
        ),
        verbose_name=_("Factsheet URL"),
    )

    content_panels = Page.content_panels + [
        FieldPanel("hero_image"),
        MultiFieldPanel(
            [
                FieldPanel("introduction_heading"),
                FieldPanel("introduction"),
            ],
            heading=_("Programme overview"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("outputs_heading"),
                FieldPanel("outputs"),
            ],
            heading=_("Project outputs"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("factsheet_heading"),
                FieldPanel("factsheet_description"),
                FieldPanel("factsheet_url"),
            ],
            heading=_("Programme factsheet"),
        ),
    ]

    class Meta:
        verbose_name = _("CLIMSA About Page")

    def get_meta_image(self):
        return super().get_meta_image() or self.hero_image

    def get_meta_description(self):
        return super().get_meta_description() or self.factsheet_description
