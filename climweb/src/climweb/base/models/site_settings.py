from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from loguru import logger
from wagtail.admin.panels import (
    PageChooserPanel,
    MultiFieldPanel,
    FieldPanel,
    TabbedInterface,
    ObjectList,
    FieldRowPanel
)
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.fields import RichTextField, StreamField
from wagtail_color_panel.edit_handlers import NativeColorPanel
from wagtail_color_panel.fields import ColorField
from wagtailcache.cache import clear_cache

from climweb.base.blocks import (
    FooterNavigationItemBlock,
    HeaderUtilityLinkBlock,
    LanguageItemBlock,
    NavigationItemBlock,
    SocialMediaBlock,
)
from climweb.base.constants import LANGUAGE_CHOICES, LANGUAGE_CHOICES_DICT, COUNTRY_CHOICES
from climweb.base.utils import get_country_info, mix_with_white


@register_setting
class OrganisationSetting(BaseSiteSetting):
    country = models.CharField(max_length=100, blank=True, null=True, choices=COUNTRY_CHOICES,
                               verbose_name=_("Country"))
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Organisation Name"))
    
    phone = models.CharField(max_length=255, blank=True, null=True, help_text=_("Phone Number"),
                             verbose_name=_("Phone number"))
    email = models.EmailField(blank=True, null=True, max_length=254, help_text=_("Email address"),
                              verbose_name=_("Email address"))
    address = RichTextField(max_length=250, blank=True, null=True, help_text=_("Postal Address"),
                            verbose_name=_("Postal address"))
    
    social_media_accounts = StreamField([
        ('social_media_account', SocialMediaBlock()),
    ], blank=True, null=True, use_json_field=True)
    
    # logo
    logo = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                             verbose_name=_("Organisation Logo"))
    country_flag = models.ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+",
                                     verbose_name=_("Country Flag"))
    
    favicon = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text="Does not need to be any larger than 200x200 pixels. A 1:1 (square) image ratio is best here "
                  "- If the image is not square, it will be scaled to a square."
    )
    
    footer_logo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Footer Logo"),
        help_text=_("Logo that appears on the footer"),
    )
    
    cms_logo = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("CMS Logo"),
        help_text=_("Logo that appears on the CMS. Should be a whit transparent logo preferably"),
    )
    
    page_not_found_error_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Page not Found Image"),
        help_text=_("Image shown on error 404 page"),
    )
    
    server_error_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Server Error Image"),
        help_text=_("Image shown on error 500 error page"),
    )
    
    panels = [
        FieldPanel("name"),
        FieldPanel('country'),
        MultiFieldPanel(
            [
                FieldPanel("logo"),
                FieldPanel("country_flag"),
                FieldPanel("favicon"),
                FieldPanel("footer_logo"),
                FieldPanel("cms_logo"),
            ],
            heading=_("Logo")
        ),
        FieldPanel("social_media_accounts"),
        MultiFieldPanel(
            [
                FieldPanel("page_not_found_error_image"),
                FieldPanel("server_error_image"),
            ],
            heading=_("Error Images")
        ),
        
        MultiFieldPanel([
            FieldPanel("address"),
        ], heading=_("Address Settings")),
        MultiFieldPanel([
            FieldPanel("email"),
            FieldPanel("phone"),
        ], heading=_("Contact Settings")),
    ]
    
    class Meta:
        verbose_name = _("Organisation Settings")
    
    @cached_property
    def country_info(self):
        if self.country:
            return get_country_info(self.country)


@register_setting(icon="cogs")
class IntegrationSettings(BaseSiteSetting):
    youtube_api = models.CharField(verbose_name=_("Youtube API Key"), max_length=50, blank=True, help_text=_(
        "To set up Youtube API Key refer to ")+"https://developers.google.com/youtube/v3/getting-started")
    
    ga_tracking_id = models.CharField(
        blank=True,
        max_length=255,
        verbose_name=_('GA Tracking ID'),
        help_text=_('Your Google Analytics tracking ID (begins with "UA-")'),
    )
    ga_track_button_clicks = models.BooleanField(
        default=False,
        verbose_name=_('Track button clicks'),
        help_text=_(
            'Track all button clicks using Google Analytics event tracking, '
            'Event tracking details can be specified in each button’s advanced settings options.'), )
    
    track_internally = models.BooleanField(
        default=True,
        verbose_name=_('Track pages internally'),
        help_text=_(
            'Track   all pages internally. This will enable the internal analytics dashboard, '
            'alongside Google Analytics, if also enabled'), )
    
    google_site_verification_key = models.CharField(max_length=255, blank=True, null=True,
                                                    verbose_name=_("Google Site Verification Key"), )
    
    edit_handler = TabbedInterface([
        ObjectList([
            FieldPanel('youtube_api')
        ], heading=_("Youtube Integration")),
        ObjectList([
            FieldPanel('ga_tracking_id'),
            FieldPanel('ga_track_button_clicks'),
            FieldPanel('track_internally'),
        ], heading=_("Google Analytics")),
        ObjectList([
            FieldPanel('google_site_verification_key'),
        ], heading=_("Google Search")),
    ])
    
    class Meta:
        verbose_name = _("Integration Settings")


@register_setting(icon="site")
class LanguageSettings(BaseSiteSetting):
    default_language = models.CharField(max_length=10, blank=True, null=True, choices=LANGUAGE_CHOICES, default="en",
                                        verbose_name=_("Default Language"))
    languages = StreamField([
        ('languages', LanguageItemBlock())
    ], blank=True, null=True, use_json_field=True, verbose_name=_("languages"))
    
    panels = [
        FieldPanel('default_language'),
        FieldPanel('languages')
    ]
    
    @cached_property
    def google_languages(self):
        languages = []
        default = LANGUAGE_CHOICES_DICT.get(self.default_language)
        languages.append(default)
        for lang in self.languages:
            languages.append(lang.value.lang_val())
        return languages
    
    class Meta:
        verbose_name = _("Google Translate Languages")
    
    @cached_property
    def included_languages(self):
        return [lang["language"] for lang in self.google_languages]


class Theme(models.Model):
    FONT_CHOICES = (
        ("open_sans", _("Open Sans")),
        ("dm_sans", _("DM Sans")),
        ("manrope", _("Manrope")),
        ("system", _("System font")),
    )

    ACMAD_PORTAL_DEFAULTS = {
        "primary_hover_color": "#087a5a",
        "primary_color": "#132a35",
        "secondary_color": "#f8f7f3",
        "header_background_color": "#071f2e",
        "heading_color": "#0b2b3d",
        "secondary_dark_color": "#123e52",
        "primary_hover_state_color": "#0b946b",
        "primary_light_color": "#dff4eb",
        "accent_color": "#f4c84a",
        "accent_hover_color": "#f8d66f",
        "info_background_color": "#e8f2f5",
        "surface_color": "#ffffff",
        "muted_text_color": "#61727b",
        "border_color": "#dce4e5",
        "danger_color": "#b93535",
        "body_font": "dm_sans",
        "heading_font": "manrope",
        "shadow_sm": "0 8px 28px rgba(9, 42, 55, 0.08)",
        "shadow_lg": "0 24px 70px rgba(2, 24, 35, 0.20)",
        "border_radius": 5,
        "box_shadow": 8,
    }

    CLIMWEB_DEFAULTS = {
        "primary_hover_color": "#176c9c",
        "primary_color": "#363636",
        "secondary_color": "#ffffff",
        "header_background_color": "#176c9c",
        "heading_color": "#363636",
        "secondary_dark_color": "#0c447c",
        "primary_hover_state_color": "#0c447c",
        "primary_light_color": "#e6f1fb",
        "accent_color": "#3e8ed0",
        "accent_hover_color": "#226296",
        "info_background_color": "#e6f1fb",
        "surface_color": "#ffffff",
        "muted_text_color": "#5d6572",
        "border_color": "#d3d3d3",
        "danger_color": "#f14668",
        "body_font": "open_sans",
        "heading_font": "open_sans",
        "shadow_sm": "0 1px 3px 0 rgba(0, 0, 0, 0.25)",
        "shadow_lg": "0 4px 12px rgba(0, 0, 0, 0.15)",
        "border_radius": 12,
        "box_shadow": 6,
    }

    FONT_STACKS = {
        "open_sans": '"Open Sans", "Noto Sans Arabic", Arial, sans-serif',
        "dm_sans": '"DM Sans", "Noto Sans Arabic", Arial, sans-serif',
        "manrope": '"Manrope", "Noto Sans Arabic", Arial, sans-serif',
        "system": '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    }

    is_default = models.BooleanField(default=False, verbose_name=_("Is Default Theme"),
                                     help_text=_("Enable if this is the default theme"))
    name = models.CharField(blank=False, verbose_name=_("Theme Name"), max_length=250, null=True)
    primary_hover_color = ColorField(blank=True, null=True, default="#176c9c",
                                     help_text=_("Main interactive and button color"),
                                     verbose_name=_("Primary brand color"))
    primary_color = ColorField(blank=True, null=True, default="#363636",
                               help_text=_("Default color for body copy"), verbose_name=_("Body text color"))
    secondary_color = ColorField(blank=True, null=True, default="#ffffff",
                                 help_text=_("Default page background"), verbose_name=_("Page background color"))
    header_background_color = ColorField(
        blank=True, null=True, verbose_name=_("Header and footer background")
    )
    heading_color = ColorField(blank=True, null=True, verbose_name=_("Heading and navigation color"))
    secondary_dark_color = ColorField(blank=True, null=True, verbose_name=_("Secondary dark color"))
    primary_hover_state_color = ColorField(
        blank=True, null=True, verbose_name=_("Primary hover color")
    )
    primary_light_color = ColorField(blank=True, null=True, verbose_name=_("Primary light background"))
    accent_color = ColorField(blank=True, null=True, verbose_name=_("Accent color"))
    accent_hover_color = ColorField(blank=True, null=True, verbose_name=_("Accent hover color"))
    info_background_color = ColorField(blank=True, null=True, verbose_name=_("Information background"))
    surface_color = ColorField(blank=True, null=True, verbose_name=_("Card and navigation surface"))
    muted_text_color = ColorField(blank=True, null=True, verbose_name=_("Muted text color"))
    border_color = ColorField(blank=True, null=True, verbose_name=_("Border color"))
    danger_color = ColorField(blank=True, null=True, verbose_name=_("Danger and error color"))
    body_font = models.CharField(
        max_length=20, choices=FONT_CHOICES, default="open_sans", verbose_name=_("Body font")
    )
    heading_font = models.CharField(
        max_length=20, choices=FONT_CHOICES, default="open_sans", verbose_name=_("Heading font")
    )
    shadow_sm = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name=_("Small shadow"),
        help_text=_("CSS box-shadow used for cards and dropdowns."),
    )
    shadow_lg = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name=_("Large shadow"),
        help_text=_("CSS box-shadow used for overlays and featured panels."),
    )
    restore_acmad_portal_defaults = models.BooleanField(
        default=False,
        verbose_name=_("Restore ACMAD Portal defaults on save"),
        help_text=_("Replace this theme's colors, fonts, radius, and shadows with the ACMAD Portal preset."),
    )
    restore_climweb_defaults = models.BooleanField(
        default=False,
        verbose_name=_("Restore ClimWeb defaults on save"),
        help_text=_("Replace this theme's colors, fonts, radius, and shadows with the original ClimWeb preset."),
    )
    border_radius = models.IntegerField(validators=[MinValueValidator(0),
                                                    MaxValueValidator(20)], verbose_name=_("Border radius (px)"),
                                        help_text=_("Minimum 0 and Maximum 20 pixels"), default=12)
    box_shadow = models.IntegerField(validators=[MinValueValidator(1),
                                                 MaxValueValidator(24)], verbose_name=_("Box shadow"),
                                     help_text=_("Elevation value minimum 1 and maximum 24"), default=6)
    
    edit_handler = TabbedInterface([
        ObjectList([
            FieldPanel('name'),
            FieldPanel('is_default'),
        ], heading=_("Information")),
        ObjectList([
            FieldRowPanel([
                NativeColorPanel('primary_hover_color'),
                NativeColorPanel('primary_hover_state_color'),
            ]),
            FieldRowPanel([
                NativeColorPanel('header_background_color'),
                NativeColorPanel('secondary_dark_color'),
            ]),
            FieldRowPanel([
                NativeColorPanel('heading_color'),
                NativeColorPanel('primary_color'),
            ]),
            FieldRowPanel([
                NativeColorPanel('accent_color'),
                NativeColorPanel('accent_hover_color'),
            ]),
        ], heading=_("Brand Colors")),
        ObjectList([
            FieldRowPanel([
                NativeColorPanel('secondary_color'),
                NativeColorPanel('surface_color'),
            ]),
            FieldRowPanel([
                NativeColorPanel('primary_light_color'),
                NativeColorPanel('info_background_color'),
            ]),
            FieldRowPanel([
                NativeColorPanel('muted_text_color'),
                NativeColorPanel('border_color'),
            ]),
            NativeColorPanel('danger_color'),
        ], heading=_("Supporting Colors")),
        ObjectList([
            FieldPanel('body_font'),
            FieldPanel('heading_font'),
        ], heading=_("Typography")),
        ObjectList([
            FieldPanel('border_radius'),
            FieldPanel('box_shadow'),
            FieldPanel('shadow_sm'),
            FieldPanel('shadow_lg')],
            heading=_("Borders and Box Shadow")),
        ObjectList([
            FieldPanel('restore_acmad_portal_defaults'),
            FieldPanel('restore_climweb_defaults'),
        ], heading=_("Defaults")),
    
    ])
    
    class Meta:
        verbose_name = _("Theme")
    
    def __str__(self) -> str:
        return self.name if not self.is_default else f"{self.name} (Default)"

    def apply_acmad_portal_defaults(self):
        for field, value in self.ACMAD_PORTAL_DEFAULTS.items():
            setattr(self, field, value)

    def apply_climweb_defaults(self):
        for field, value in self.CLIMWEB_DEFAULTS.items():
            setattr(self, field, value)

    def as_tokens(self):
        primary = self.primary_hover_color or "#0C447C"
        text = self.primary_color or "#363636"
        return {
            "navy_950": self.header_background_color or primary,
            "navy_900": self.heading_color or text,
            "navy_800": self.secondary_dark_color or primary,
            "green_700": primary,
            "green_600": self.primary_hover_state_color or primary,
            "green_100": self.primary_light_color or mix_with_white(primary, 0.80),
            "yellow_400": self.accent_color or "#f4c84a",
            "yellow_300": self.accent_hover_color or "#f8d66f",
            "blue_100": self.info_background_color or mix_with_white(primary, 0.80),
            "sand_50": self.secondary_color or "#ffffff",
            "white": self.surface_color or "#ffffff",
            "ink": text,
            "muted": self.muted_text_color or "#61727b",
            "line": self.border_color or "#dce4e5",
            "danger": self.danger_color or "#b93535",
            "shadow_sm": self.shadow_sm or "0 8px 28px rgba(9, 42, 55, 0.08)",
            "shadow_lg": self.shadow_lg or "0 24px 70px rgba(2, 24, 35, 0.20)",
            "body_font": self.FONT_STACKS.get(self.body_font, self.FONT_STACKS["open_sans"]),
            "heading_font": self.FONT_STACKS.get(self.heading_font, self.FONT_STACKS["open_sans"]),
            "border_radius": f"{self.border_radius * 0.06}em",
            "box_shadow_elevation": str(self.box_shadow),
        }
    
    def save(self, *args, **kwargs):
        if self.restore_acmad_portal_defaults:
            self.apply_acmad_portal_defaults()
            self.restore_acmad_portal_defaults = False

        if self.restore_climweb_defaults:
            self.apply_climweb_defaults()
            self.restore_climweb_defaults = False

        themes = Theme.objects.all().exclude(pk=self.pk)
        
        # when i default is enabled, disbale any other default theme
        if self.is_default:
            themes.update(
                is_default=False
            )
        
        super(Theme, self).save(*args, **kwargs)


@register_setting
class NavigationSettings(BaseSiteSetting):
    main_menu = StreamField([
        ("navigation_item", NavigationItemBlock()),
    ], use_json_field=True, blank=True, null=True)
    header_utility_links = StreamField(
        [("utility_link", HeaderUtilityLinkBlock())],
        use_json_field=True,
        blank=True,
        null=True,
        verbose_name=_("Header utility links"),
        help_text=_("Add, reorder, enable, or disable links shown in the header utility bar."),
    )
    footer_menu = StreamField([
        ("navigation_item", FooterNavigationItemBlock()),
    ], use_json_field=True, blank=True, null=True)
    
    panels = [
        FieldPanel("main_menu"),
        FieldPanel("header_utility_links"),
        FieldPanel("footer_menu"),
    ]
    
    class Meta:
        verbose_name = _("Navigation Setting")
        verbose_name_plural = _("Navigation Settings")


@register_setting
class ImportantPages(BaseSiteSetting):
    mailing_list_signup_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("Mailing list sign up page"))
    contact_us_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("Contact us page"))
    all_products_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All products page"))
    all_projects_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All projects page"))
    all_news_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All news page"))
    all_publications_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All publications page"))
    all_videos_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All videos page"))
    all_applications_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All applications page"))
    all_events_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All events page"))
    all_partners_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All partners page"))
    all_tenders_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All tenders page"))
    all_vacancies_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("All vacancies page"))
    feedback_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("Feedback page"))
    cap_warnings_list_page = models.ForeignKey(
        'wagtailcore.Page', blank=True, null=True, on_delete=models.SET_NULL, related_name='+',
        verbose_name=_("CAP Warnings List page"))
    
    panels = [
        PageChooserPanel('mailing_list_signup_page'),
        PageChooserPanel('contact_us_page'),
        PageChooserPanel('feedback_page'),
        PageChooserPanel('all_products_page'),
        PageChooserPanel('all_projects_page'),
        PageChooserPanel('all_tenders_page'),
        PageChooserPanel('all_vacancies_page'),
        PageChooserPanel('all_news_page'),
        PageChooserPanel('all_publications_page'),
        PageChooserPanel('all_videos_page'),
        PageChooserPanel('all_applications_page'),
        PageChooserPanel('all_events_page'),
        PageChooserPanel('all_partners_page'),
    ]

    if settings.IS_METEOROLOGICAL:
        panels += [
            PageChooserPanel('cap_warnings_list_page'),
        ]
    
    class Meta:
        verbose_name = _("Important Pages")
        verbose_name_plural = _("Important Pages")


# clear wagtail cache on saving the following models
@receiver(post_save, sender=OrganisationSetting)
@receiver(post_save, sender=IntegrationSettings)
@receiver(post_save, sender=LanguageSettings)
@receiver(post_save, sender=Theme)
@receiver(post_save, sender=NavigationSettings)
@receiver(post_save, sender=ImportantPages)
def handle_clear_wagtail_cache(sender, **kwargs):
    logger.debug("[WAGTAIL_CACHE]: Clearing cache")
    clear_cache()
