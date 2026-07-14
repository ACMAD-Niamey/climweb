import logging
from typing import Optional

from adminboundarymanager.models import AdminBoundarySettings
from django.conf import settings
from django.contrib.gis.db import models
from django.template.defaultfilters import truncatechars
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
if "forecastmanager" in settings.INSTALLED_APPS:
    from forecastmanager.forecast_settings import ForecastSetting
    from forecastmanager.models import City
from geomanager.models import RasterFileLayer, WmsLayer, VectorTileLayer
from modelcluster.models import ClusterableModel
from wagtail import blocks
from wagtail.admin.panels import MultiFieldPanel, FieldPanel, TabbedInterface, ObjectList, PageChooserPanel
from wagtail.api.v2.utils import get_full_url
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail_color_panel.fields import ColorField
from wagtailiconchooser.blocks import IconChooserBlock
from wagtailiconchooser.utils import get_svg_sprite_for_icons
from climweb.base.choosers import register_searchable_chooser

from climweb.base import blocks as climweb_blocks
from climweb.base.mixins import MetadataPageMixin
from climweb.base.registries import plugin_registry
from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES
from climweb.pages.events.models import EventPage
from climweb.pages.news.models import NewsPage
from climweb.pages.organisation_pages.partners.models import Partner
from climweb.pages.products.models import ProductItemPage, ProductPage
from climweb.pages.publications.models import PublicationPage
from climweb.pages.services.models import ServicePage
from climweb.pages.videos.models import YoutubePlaylist
from .blocks import AreaBoundaryBlock, AreaPolygonBlock

logger = logging.getLogger(__name__)

CLIMWEB_ADDITIONAL_APPS = getattr(settings, "CLIMWEB_ADDITIONAL_APPS", [])

HOME_SUBPAGE_TYPES = [
    'contact.ContactPage',
    'services.ServiceIndexPage',
    'products.ProductIndexPage',
    'feedback.FeedbackPage',
    'publications.PublicationsIndexPage',
    'news.NewsIndexPage',
    'mediacenter.MediaIndexPage',
    'organisation.OrganisationIndexPage',
    'events.EventIndexPage',
    'surveys.SurveyPage',
    'email_subscription.MailchimpMailingListSubscriptionPage',
    'email_subscription.MauticMailingListSubscriptionPage',
    'data_request.DataRequestPage',
    'flex_page.FlexPage',
    'stations.StationsPage',
    'satellite_imagery.SatelliteImageryPage',
    'glossary.GlossaryIndexPage',
    'webstories.WebStoryListPage',
    'dashboards.DashboardGalleryPage',
    'summer_school.SummerSchoolIndexPage',
]

if "forecastmanager" in settings.INSTALLED_APPS:
    HOME_SUBPAGE_TYPES += ['weather.WeatherDetailPage', 'cityclimate.CityClimateDataPage']

if "capcomposer.cap" in settings.INSTALLED_APPS:
    HOME_SUBPAGE_TYPES.append('cap.CapAlertListPage')



class HomePage(MetadataPageMixin, Page):
    BANNER_TYPES = (
        ('full', 'Full Banner'),
        ('half', 'Half Banner'),
        ('card', 'Card Banner')
    )
    
    template = "home/home_page.html"
    
    parent_page_type = [
        'wagtailcore.Page'
    ]
    max_count = 1
    
    pre_title = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Pre Title'),
                                 help_text=_("Text to show before the name of the institution. "
                                             "For example, if the institution is under a ministry, the ministry name "
                                             "can added here"))
    hero_title = models.CharField(max_length=100, verbose_name=_('Institution Name'),
                                  help_text=_("Full name of the institution"))
    hero_subtitle = models.CharField(blank=True, null=True, max_length=200, verbose_name=_('Tagline'),
                                     help_text=_("Can be the tagline or slogan of the institution"))
    hero_banner = models.ForeignKey("wagtailimages.Image", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+", verbose_name=_("Banner Image"))
    show_banner_video = models.BooleanField(default=False, verbose_name=_("Use YouTube Video as Banner"),
                                            help_text=_("If enabled, the YouTube video will be used as the banner background instead of the banner image"))
    banner_youtube_video_id = models.CharField(max_length=100, blank=True, null=True,
                                               verbose_name=_("YouTube Video ID"),
                                               help_text=_("YouTube Video ID. Only used if 'Use YouTube Video as Banner' is enabled."))
    hero_text_color = ColorField(blank=True, null=True, default="#f0f0f0", verbose_name=_("Banner Text Color"))
    hero_type = models.CharField(_("Banner Type"), max_length=50, choices=BANNER_TYPES, default='full')
    
    call_to_action_button_text = models.CharField(max_length=100, blank=True, null=True,
                                                  verbose_name=_('Call to action button text'))
    call_to_action_related_page = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_('Call to action related page')
    )

    call_to_action_button_text_2 = models.CharField(max_length=100, blank=True, null=True,
                                                   verbose_name=_('Call to action button text 2'))
    call_to_action_related_page_2 = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_('Call to action related page 2')
    )

    call_to_action_button_text_3 = models.CharField(max_length=100, blank=True, null=True,
                                                   verbose_name=_('Call to action button text 3'))
    call_to_action_related_page_3 = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_('Call to action related page 3')
    )
    
    show_city_forecast = models.BooleanField(default=True, verbose_name=_("Show city forecast section"))
    
    show_weather_watch = models.BooleanField(default=True, verbose_name=_("Show weather watch section"))
    weather_watch_header = models.CharField(max_length=100, default="Our Weather Watch",
                                            verbose_name=_("Weather Watch Section header"))
    show_mapviewer_cta = models.BooleanField(default=False, verbose_name=_("Show MapViewer button"))
    mapviewer_cta_title = models.CharField(max_length=100, blank=True, null=True, default='Explore on MapViewer',
                                           verbose_name=_('MapViewer Call to Action Title'))
    mapviewer_cta_url = models.URLField(blank=True, null=True, verbose_name=_("Mapviewer URL"), )

    # Weather Watch card content. These are hybrid fields: editors may fill them
    # in manually, or leave them blank to have the card derived from the latest
    # item of the linked source product (see weather_watch_card below).
    weather_watch_period = models.CharField(max_length=100, blank=True, null=True,
                                            verbose_name=_("Outlook period"),
                                            help_text=_("e.g. 10 – 16 July 2026. Leave blank to derive from the "
                                                        "latest item of the source product below"))
    weather_watch_outlook = RichTextField(blank=True, null=True, features=SUMMARY_RICHTEXT_FEATURES,
                                          verbose_name=_("Outlook summary"),
                                          help_text=_("Short outlook summary shown on the Weather Watch card. "
                                                      "Leave blank to derive from the source product below"))
    weather_watch_indicators = StreamField([
        ('indicator', blocks.StructBlock([
            ('label', blocks.CharBlock(max_length=30)),
            ('value', blocks.CharBlock(max_length=30)),
        ], label=_("Indicator"))),
    ], null=True, blank=True, use_json_field=True, max_num=3, verbose_name=_("Weather Watch indicators"))
    weather_watch_source_product = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Weather Watch source product")
    )

    featured_products = StreamField([
        ('product', blocks.StructBlock([
            ('page', blocks.PageChooserBlock(page_type=['products.ProductPage'])),
            ('custom_title', blocks.CharBlock(required=False, max_length=60)),
            ('custom_blurb', blocks.TextBlock(required=False, max_length=160)),
            ('icon', IconChooserBlock(required=False)),
        ], label=_("Product"))),
    ], null=True, blank=True, use_json_field=True, max_num=3, verbose_name=_("Featured Products"))

    services_strip = StreamField([
        ('item', blocks.StructBlock([
            ('icon', IconChooserBlock(default="layer-group")),
            ('title', blocks.CharBlock(max_length=50)),
            ('description', blocks.CharBlock(max_length=120)),
            ('page', blocks.PageChooserBlock(required=False)),
            ('external_url', blocks.URLBlock(required=False)),
        ], label=_("Item"))),
    ], null=True, blank=True, use_json_field=True, max_num=5, verbose_name=_("Services Strip"),
        help_text=_("Compact link strip below the cards. Leave empty to derive from Service pages."))

    youtube_playlist = models.ForeignKey(
        YoutubePlaylist,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Youtube Playlist")
    )
    
    feature_block = StreamField([
        ('feature_item', climweb_blocks.FeatureBlock()),
    ], null=True, blank=True, use_json_field=True, verbose_name=_("Feature block"))

    stats_bar = StreamField([
        ('stat', blocks.StructBlock([
            ('value', blocks.CharBlock(max_length=20, label=_("Value"), help_text=_("e.g. 47, 2.4M, 138"))),
            ('label', blocks.CharBlock(max_length=100, label=_("Label"), help_text=_("e.g. Regional Centers"))),
        ], label=_("Stat Item"))),
    ], null=True, blank=True, use_json_field=True, verbose_name=_("Stats Bar"),
        help_text=_("Displayed below the hero on non-meteorological sites. Add up to 4 items."),
        max_num=4)

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel("hero_banner"),
            FieldPanel('show_banner_video'),
            FieldPanel('banner_youtube_video_id'),
            FieldPanel('pre_title'),
            FieldPanel('hero_title'),
            FieldPanel('hero_subtitle'),
            FieldPanel('hero_type')
        ], heading=_("Banner Section")),
        MultiFieldPanel([
            FieldPanel('call_to_action_button_text'),
            FieldPanel('call_to_action_related_page'),
            FieldPanel('call_to_action_button_text_2'),
            FieldPanel('call_to_action_related_page_2'),
            FieldPanel('call_to_action_button_text_3'),
            FieldPanel('call_to_action_related_page_3'),
        ], heading=_("Banner Call to Action Buttons")),
        MultiFieldPanel([
            FieldPanel('show_city_forecast'),
        ], heading=_("City Forecast Section")) if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
        MultiFieldPanel([
            FieldPanel('show_weather_watch'),
            FieldPanel('weather_watch_header'),
            FieldPanel('weather_watch_period'),
            FieldPanel('weather_watch_outlook'),
            FieldPanel('weather_watch_indicators'),
            PageChooserPanel('weather_watch_source_product', 'products.ProductPage'),
            FieldPanel('show_mapviewer_cta'),
            FieldPanel('mapviewer_cta_title'),
            FieldPanel('mapviewer_cta_url')
        ], heading=_("Weather Watch Section")),
        MultiFieldPanel([
            FieldPanel('featured_products'),
        ], heading=_("Featured Products")) if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
        MultiFieldPanel([
            FieldPanel('services_strip'),
        ], heading=_("Services Strip")) if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
        MultiFieldPanel([
            FieldPanel('youtube_playlist'),
        ], heading=_("Media Section")),
        MultiFieldPanel([
            FieldPanel('feature_block'),
        ], heading=_("Addditional Information")),
        MultiFieldPanel([
            FieldPanel('stats_bar'),
        ], heading=_("Stats Bar")) if not settings.IS_METEOROLOGICAL else MultiFieldPanel(),
        
    ]
    
    
    class Meta:
        verbose_name = _("Home Page")
        verbose_name_plural = _("Home Pages")
    
    # Python 3.13 removed stacked @classmethod+@property. Compute subpage_types
    # eagerly at class definition time (plugin_registry is empty at startup
    # for bare dev environments, so the dynamic lookup adds nothing useful).
    subpage_types = HOME_SUBPAGE_TYPES + plugin_registry.get_plugin_subpage_types_for_page("homepage")
    
    def get_meta_image(self):
        if self.search_image:
            return self.search_image
        return self.hero_banner
    
    def save(self, *args, **kwargs):
        if not self.search_image and self.hero_banner:
            self.search_image = self.hero_banner
        
        if not self.seo_title and self.hero_title:
            self.seo_title = self.hero_title
        
        if not self.search_description and self.hero_subtitle:
            self.search_description = truncatechars(self.hero_subtitle, 160)
        
        return super().save(*args, **kwargs)
    
    def get_meta_description(self):
        if self.search_description:
            return self.search_description
        return self.hero_subtitle
    
    def get_meta_title(self):
        if self.seo_title:
            return self.seo_title
        return self.hero_title
    
    def get_context(self, request, *args, **kwargs):
        context = super(HomePage, self).get_context(request, *args, **kwargs)

        # Fetch once and reuse throughout — for_request caches per request, but
        # a single explicit fetch keeps the data flow obvious.
        home_map_settings = HomeMapSettings.for_request(request)

        if settings.IS_METEOROLOGICAL:
            # Met-mode homepage renders the Multi-Hazard map widget instead of
            # the legacy Vue home-map, so it only needs the catalog API config.
            if self.show_weather_watch:
                context["multi_hazard_api_base_url"] = home_map_settings.multi_hazard_api_base_url or ""
                context["multi_hazard_project_slug"] = home_map_settings.multi_hazard_project_slug
        else:
            # The alerts panel is part of the legacy weather watch map section
            # (only mounted by the non-met hero), so only expose its url when
            # the section is enabled in the admin.
            if self.show_weather_watch and "capcomposer.cap" in settings.INSTALLED_APPS:
                context["home_map_alerts_url"] = get_full_url(request, reverse("home_map_alerts"))

        abm_settings = AdminBoundarySettings.for_request(request)
        abm_extents = abm_settings.combined_countries_bounds
        context.update({
            "country_bounds": abm_extents,
        })
        
        if "forecastmanager" in settings.INSTALLED_APPS:
            forecast_setting = ForecastSetting.for_request(request)
            city_detail_page = forecast_setting.weather_detail_page

            if city_detail_page:
                city_detail_page = city_detail_page.specific
                all_city_detail_page_url = city_detail_page.get_full_url(request)
                city_detail_page_url = all_city_detail_page_url + city_detail_page.detail_page_base_url
                context.update({
                    "city_detail_page_url": city_detail_page_url,
                })

            city_search_url = get_full_url(request, reverse("cities-list"))
            context.update({
                "city_search_url": city_search_url,
            })
        
        if not settings.IS_METEOROLOGICAL and self.show_weather_watch:
            # Only the non-met hero's Vue home-map consumes this settings feed;
            # the met homepage renders the multi-hazard widget instead.
            map_settings_url = get_full_url(request, reverse("home-map-settings"))
            context.update({
                "home_map_settings_url": map_settings_url,
            })

        if "forecastmanager" in settings.INSTALLED_APPS:
            context["home_weather_widget_url"] = get_full_url(request, reverse("home-weather-widget"))

            if self.show_city_forecast:
                from climweb.pages.weather.utils import get_city_forecast_detail_data

                default_city = forecast_setting.default_city
                if not default_city:
                    default_city = City.objects.first()

                if default_city:
                    forecast_periods_count = forecast_setting.periods.count()
                    multi_period = forecast_periods_count > 1
                    widget_data = get_city_forecast_detail_data(
                        default_city, multi_period=multi_period, request=request, for_home_widget=True
                    )

                    widget_context = {
                        "city": default_city,
                        "show_condition_label": forecast_setting.show_conditions_label_on_widget,
                        "use_period_labels": forecast_setting.use_period_labels,
                        "city_search_url": context.get("city_search_url"),
                        **widget_data,
                    }

                    if city_detail_page:
                        try:
                            widget_context["city_detail_page_url"] = (
                                city_detail_page.get_full_url(request)
                                + city_detail_page.reverse_subpage(
                                    "daily_table_for_city", kwargs={"city_slug": default_city.slug}
                                )
                            )
                        except Exception:
                            pass

                    home_map_settings = HomeMapSettings.for_request(request)
                    if home_map_settings.show_forecast_attribution and forecast_setting.enable_auto_forecast:
                        widget_context.update({
                            "external_source_attribution": str(
                                _("Forecast Data Source: %(forecast_source)s") % {"forecast_source": "Yr.no"}
                            ),
                            "external_source_url": "https://www.yr.no",
                        })

                    if forecast_setting.weather_reports_page:
                        widget_context["weather_reports_page_url"] = forecast_setting.weather_reports_page.get_full_url(request)

                    if not widget_data.get("city_forecasts_by_date"):
                        context["home_weather_widget_no_data"] = True
                    else:
                        template_name = (
                            'weather/widgets/location_forecast_multiple_slider.html'
                            if multi_period
                            else 'weather/widgets/location_forecast_single_slider.html'
                        )
                        try:
                            context["home_weather_widget_html"] = render_to_string(
                                template_name, widget_context, request=request
                            )
                        except Exception:
                            pass
        
        if self.youtube_playlist:
            context['youtube_playlist_url'] = self.youtube_playlist.get_playlist_items_api_url(request)
        
        if not settings.IS_METEOROLOGICAL:
            # SVG sprite for the non-met hero's Vue home-map icons only.
            home_map_layer_icons = [
                "warning",
                "heavy-rain",
                "layer-group"
            ]

            if home_map_settings.map_layers:
                icons = [layer_block.value.get("icon") for layer_block in home_map_settings.map_layers]
                home_map_layer_icons.extend(icons)

            context.update({
                "home_map_layer_svg_sprite": get_svg_sprite_for_icons(home_map_layer_icons)
            })
        
        context['IS_METEOROLOGICAL'] = settings.IS_METEOROLOGICAL
        return context

    @cached_property
    def partners(self):
        # get the first 6 partners that should be visible on the homepage
        partners = Partner.objects.filter(visible_on_homepage=True, logo__isnull=False)[:6]
        return partners
    
    @cached_property
    def latest_updates(self):
        updates = []
        
        # get latest news, publication, crop monitor, seasonal forecast, food security statement,
        news = NewsPage.objects.live().filter(is_visible_on_homepage=True).order_by('-date').first()
        events = EventPage.objects.live().filter(is_visible_on_homepage=True).order_by('-date_from').first()
        
        if events is None:
            events = EventPage.objects.live().order_by('-date_from').first()
        
        if news is None:
            news = NewsPage.objects.live().order_by('-date').first()
        
        publications = PublicationPage.objects.live().filter(is_visible_on_homepage=True).order_by(
            '-publication_date').first()
        
        if publications is None:
            publications = PublicationPage.objects.live().order_by('-publication_date').first()
        
        if news:
            updates.append(news)
        if events:
            updates.append(events)
        if publications:
            updates.append(publications)
        
        return updates
    
    @cached_property
    def services(self):
        services = ServicePage.objects.live()
        return services

    def _weather_watch_indicators_list(self) -> list[dict]:
        """
        Flatten the indicators StreamField into plain dicts so templates don't
        need to know about StreamField internals.
        """
        indicators: list[dict] = []
        if self.weather_watch_indicators:
            for block in self.weather_watch_indicators:
                indicators.append({
                    "label": block.value.get("label"),
                    "value": block.value.get("value"),
                })
        return indicators

    @cached_property
    def weather_watch_card(self) -> Optional[dict]:
        """
        Data for the homepage Weather Watch card.

        Hybrid resolution: manually entered admin fields always win, so editors
        keep full control of the card wording. If they left the fields blank,
        we fall back to deriving the card from the latest live item of the
        linked source product, which keeps the card fresh without manual edits.
        Returns None when there is nothing to show, so templates can hide the card.
        """
        indicators = self._weather_watch_indicators_list()

        source_page = None
        source_url: Optional[str] = None
        if self.weather_watch_source_product:
            # Page-tree lookups can fail on unsaved previews or if the linked
            # page was deleted/unpublished, so never let them break the homepage.
            try:
                source_page = self.weather_watch_source_product.specific
                source_url = source_page.url
            except Exception:
                logger.warning("Failed to resolve weather watch source product for homepage %s", self.pk,
                               exc_info=True)
                source_page = None

        # (a) Admin-entered content takes precedence
        if self.weather_watch_period or self.weather_watch_outlook:
            return {
                "period": self.weather_watch_period,
                "outlook_html": self.weather_watch_outlook,
                "indicators": indicators,
                "date": timezone.now().date(),
                "link_url": source_url,
            }

        # (b) Derive from the latest live item of the source product
        if source_page is not None:
            latest_item = None
            try:
                latest_item = (
                    ProductItemPage.objects.live().child_of(source_page).order_by("-date").first()
                )
            except Exception:
                logger.warning("Failed to query latest product item for homepage weather watch card",
                               exc_info=True)

            if latest_item:
                # Build a human friendly period such as "10 Jul – 16 Jul 2026".
                # When there is no validity end date, show just the start date.
                if latest_item.valid_until:
                    period = "{start} – {end}".format(
                        start=date_format(latest_item.date, "j M"),
                        end=date_format(latest_item.valid_until, "j M Y"),
                    )
                else:
                    period = date_format(latest_item.date, "j M Y")

                return {
                    "period": period,
                    "outlook_html": latest_item.listing_summary or latest_item.title,
                    "indicators": indicators,
                    "date": latest_item.date,
                    "link_url": source_url,
                }

        # (c) Nothing configured and nothing derivable
        return None

    @cached_property
    def featured_products_list(self) -> list[dict]:
        """
        Products for the homepage Featured Products card.

        Manual picks from the featured_products StreamField come first because
        editors curated their order. Products flagged with is_featured_on_homepage
        then fill any remaining slots, so the card stays populated even when
        no manual curation was done. Capped at 3 to fit the card layout.
        """
        max_items = 3
        items: list[dict] = []
        seen_page_ids: set[int] = set()

        def build_entry(page: ProductPage, custom_title: Optional[str] = None,
                        custom_blurb: Optional[str] = None, icon: Optional[str] = None) -> dict:
            description = custom_blurb
            if not description:
                try:
                    # ProductPage inherits AbstractIntroPage.get_meta_description,
                    # which falls back to introduction text/title — a good blurb source.
                    description = truncatechars(page.get_meta_description() or "", 120)
                except Exception:
                    description = ""

            if not icon:
                # Fall back to the icon of the product's primary service, which
                # gives a sensible visual without requiring per-product setup.
                try:
                    icon = page.service.icon or "layer-group"
                except Exception:
                    icon = "layer-group"

            return {
                "title": custom_title or page.title,
                "description": description,
                "icon": icon,
                "url": page.url,
            }

        # 1. Manual picks, in editor-defined order
        if self.featured_products:
            for block in self.featured_products:
                if len(items) >= max_items:
                    break
                value = block.value
                page = value.get("page")
                if not page or not page.live:
                    continue
                try:
                    page = page.specific
                except Exception:
                    logger.warning("Failed to resolve featured product page for homepage %s", self.pk,
                                   exc_info=True)
                    continue
                if page.pk in seen_page_ids:
                    continue
                seen_page_ids.add(page.pk)
                items.append(build_entry(
                    page,
                    custom_title=value.get("custom_title"),
                    custom_blurb=value.get("custom_blurb"),
                    icon=value.get("icon"),
                ))

        # 2. Fill remaining slots with flagged products, ordered by tree path
        #    for a stable, predictable order.
        if len(items) < max_items:
            try:
                flagged = ProductPage.objects.live().filter(is_featured_on_homepage=True).order_by("path")
                for page in flagged:
                    if len(items) >= max_items:
                        break
                    if page.pk in seen_page_ids:
                        continue
                    seen_page_ids.add(page.pk)
                    items.append(build_entry(page))
            except Exception:
                logger.warning("Failed to query flagged featured products for homepage %s", self.pk,
                               exc_info=True)

        return items

    @cached_property
    def services_strip_items(self) -> list[dict]:
        """
        Items for the compact services strip below the homepage cards.

        The manual StreamField wins when set, so editors can fully customize
        the strip. Otherwise we derive from the first Service pages so the
        strip works out of the box for existing sites.
        """
        items: list[dict] = []

        if self.services_strip:
            for block in self.services_strip:
                value = block.value
                page = value.get("page")
                url = "#"
                if page and page.live:
                    url = page.url or "#"
                elif value.get("external_url"):
                    url = value.get("external_url")
                items.append({
                    "icon": value.get("icon") or "layer-group",
                    "title": value.get("title"),
                    "description": value.get("description"),
                    "url": url,
                })
            return items

        # Derive from Service pages. Wrapped defensively because page-tree and
        # related-object lookups should never take the whole homepage down.
        try:
            for service_page in self.services[:5]:
                try:
                    icon = service_page.service.icon or "layer-group"
                except Exception:
                    icon = "layer-group"

                try:
                    description = truncatechars(service_page.get_meta_description() or "", 90)
                except Exception:
                    description = ""

                items.append({
                    "icon": icon,
                    "title": service_page.banner_title or service_page.title,
                    "description": description,
                    "url": service_page.url,
                })
        except Exception:
            logger.warning("Failed to derive services strip items for homepage %s", self.pk, exc_info=True)

        return items


register_searchable_chooser(WmsLayer)
register_searchable_chooser(VectorTileLayer)


class BaseLayerBlock(blocks.StructBlock):
    layer = blocks.CharBlock()  # placeholder for the actual layer chooser block, implemented in the subclasses
    icon = IconChooserBlock(required=False, default="layer-group", label=_("Icon"))
    display_name = blocks.CharBlock(max_length=100, required=False,
                                    help_text=_("Name to display on the map. "
                                                "Leave blank to use the original layer name"))
    enabled = blocks.BooleanBlock(default=True, required=False, label=_("Enabled"))
    default = blocks.BooleanBlock(default=False, required=False, label=_("Show on map by default ?"),
                                  help_text=_("You can only select one layer to be shown on the map by default. "
                                              "If multiple layers are selected, only the first one will be shown"))


class RasterFileLayerBlock(BaseLayerBlock):
    layer = climweb_blocks.UUIDModelChooserBlock(RasterFileLayer, icon="map")


class WMSLayerBlock(BaseLayerBlock):
    layer = climweb_blocks.UUIDModelChooserBlock(WmsLayer, icon="map")


class VectorTileLayerBlock(BaseLayerBlock):
    layer = climweb_blocks.UUIDModelChooserBlock(VectorTileLayer, icon="map")


@register_setting(icon="map")
class HomeMapSettings(BaseSiteSetting, ClusterableModel):
    DATE_FORMAT_CHOICES = (
        ("yyyy-MM-dd HH:mm", _("Hour minute:second - (E.g 2023-01-01 00:00)")),
        ("iii d HH:mm", _("Day of Week Day - (E.g Tue 25 08:00)")),
        ("yyyy-MM-dd", _("Day - (E.g 2023-01-01)")),
    )
    
    show_warnings_layer = models.BooleanField(default=True, verbose_name=_("Show CAP Warnings Layer"))
    warnings_layer_display_name = models.CharField(max_length=100, default=_("Weather Warnings"),
                                                   verbose_name=_("CAP Warnings Layer Display Name"))
    show_location_forecast_layer = models.BooleanField(default=True, verbose_name=_("Show Location forecast Layer"))
    location_forecast_layer_display_name = models.CharField(max_length=100, default=_("Location Forecast"),
                                                            verbose_name=_("Location Forecast Layer Display Name"))
    location_forecat_date_display_format = models.CharField(max_length=100, choices=DATE_FORMAT_CHOICES,
                                                            default="yyyy-MM-dd HH:mm",
                                                            help_text=_("Location Forecast Date Display Format"))
    forecast_cluster = models.BooleanField(default=False, verbose_name=_("Cluster Location Forecast Points"), )
    forecast_cluster_min_points = models.PositiveIntegerField(default=2, null=True, blank=True,
                                                              verbose_name=_("Cluster Minimum number of Points"),
                                                              help_text=_("Minimum number of points necessary to form"
                                                                          " a cluster if clustering is enabled"))
    forecast_cluster_radius = models.PositiveIntegerField(default=50, null=True, blank=True,
                                                          verbose_name=_("Cluster Radius"),
                                                          help_text=_("Radius of each cluster if clustering is "
                                                                      "enabled"))
    show_forecast_attribution = models.BooleanField(default=False, verbose_name=_("Show Location Forecast Attribution"))
    zoom_locations = StreamField([
        ("boundary_block", AreaBoundaryBlock(label=_("Admin Boundary"))),
        ("polygon_block", AreaPolygonBlock(label=_("Draw Polygon"))),
    ], use_json_field=True, blank=True)
    
    map_layers = StreamField([
        ('raster_file_layer', RasterFileLayerBlock(label=_("Raster Layer"), icon="map")),
        ('wms_layer', WMSLayerBlock(label=_("WMS Layer"), icon="map")),
        ('vector_tile_layer', VectorTileLayerBlock(label=_("Vector Tile Layer"), icon="map")),
    ], null=True, blank=True, max_num=5, verbose_name=_("Map Layers"))
    
    show_level_1_boundaries = models.BooleanField(default=False, verbose_name=_("Show Level 1 Boundaries"))
    use_geomanager_basemaps = models.BooleanField(default=False, verbose_name=_("Use Geomanager Basemaps, if set"))
    multi_hazard_api_base_url = models.URLField(
        blank=True,
        null=True,
        verbose_name=_("Multi-Hazard API base URL"),
        help_text=_("Base URL for the Multi-Hazard catalog API, for example https://multi-hazard.acmad.org"),
    )
    multi_hazard_project_slug = models.CharField(
        max_length=100,
        blank=True,
        default="multi-hazard",
        verbose_name=_("Multi-Hazard project slug"),
    )
    
    edit_handler = TabbedInterface([
        ObjectList([
            FieldPanel("map_layers"),
        ], heading=_("Geomanager Map Layers")),
        ObjectList([
            MultiFieldPanel([
                FieldPanel("show_level_1_boundaries"),
                FieldPanel("use_geomanager_basemaps"),
            ], heading=_("Boundary Settings"), ),
            MultiFieldPanel([
                FieldPanel("multi_hazard_api_base_url"),
                FieldPanel("multi_hazard_project_slug"),
            ], heading=_("Multi-Hazard Map")) if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
            MultiFieldPanel([
                FieldPanel("show_warnings_layer"),
                FieldPanel("warnings_layer_display_name"),
            ], heading=_("CAP Warnings Layer")) if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
            
            MultiFieldPanel([
                FieldPanel("show_forecast_attribution"),
                FieldPanel("show_location_forecast_layer"),
                FieldPanel("location_forecast_layer_display_name"),
                FieldPanel("location_forecat_date_display_format"),
                FieldPanel("forecast_cluster"),
                FieldPanel("forecast_cluster_min_points"),
                FieldPanel("forecast_cluster_radius"),
            ], heading=_("Location Forecast Layer")) if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
            
            FieldPanel("zoom_locations") if settings.IS_METEOROLOGICAL else MultiFieldPanel(),
        ], heading=_("Map Settings")),
        
    ])


    
