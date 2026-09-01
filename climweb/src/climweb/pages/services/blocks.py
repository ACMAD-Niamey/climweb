from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtailiconchooser.blocks import IconChooserBlock

from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES


class SectorLinkBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=160)
    description = blocks.TextBlock(required=False)
    url = blocks.URLBlock(max_length=500)
    link_label = blocks.CharBlock(max_length=40, default=_("Open resource"))

    class Meta:
        icon = "link"
        label = _("External tool or resource")


class SectorMeetingBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=200)
    details = blocks.TextBlock(required=False)
    url = blocks.URLBlock(max_length=500, required=False)

    class Meta:
        icon = "date"
        label = _("Meeting or activity")


class SectorServiceBlock(blocks.StructBlock):
    anchor = blocks.CharBlock(
        max_length=60,
        help_text=_("Short URL-safe name, for example agriculture or health."),
    )
    title = blocks.CharBlock(max_length=120)
    icon = IconChooserBlock(required=False, default="globe")
    summary = blocks.TextBlock()
    aim = blocks.RichTextBlock(
        required=False,
        features=SUMMARY_RICHTEXT_FEATURES,
        label=_("Aim and approach"),
    )
    risks = blocks.ListBlock(
        blocks.CharBlock(max_length=160), required=False, label=_("Key climate risks")
    )
    climate_services = blocks.ListBlock(
        blocks.CharBlock(max_length=200),
        required=False,
        label=_("Climate services and information needs"),
    )
    activities = blocks.ListBlock(
        blocks.CharBlock(max_length=200),
        required=False,
        label=_("Activities and expected outcomes"),
    )
    institutions = blocks.ListBlock(
        blocks.CharBlock(max_length=200),
        required=False,
        label=_("Participating institutions"),
    )
    rules_of_procedure = blocks.RichTextBlock(
        required=False,
        features=SUMMARY_RICHTEXT_FEATURES,
        label=_("Rules of procedure"),
        help_text=_("Governance, chair, secretariat and meeting arrangements stated in the TOR."),
    )
    platform_composition = blocks.ListBlock(
        blocks.CharBlock(max_length=200),
        required=False,
        label=_("Platform composition"),
    )
    tor_documents = blocks.ListBlock(
        SectorLinkBlock(),
        required=False,
        label=_("Terms of Reference documents"),
    )
    products = blocks.ListBlock(
        blocks.PageChooserBlock(page_type=["products.ProductPage"]),
        required=False,
        label=_("Related products"),
    )
    external_tools = blocks.ListBlock(
        SectorLinkBlock(), required=False, label=_("External tools and resources")
    )
    meetings = blocks.ListBlock(
        SectorMeetingBlock(), required=False, label=_("Meetings and activities")
    )

    class Meta:
        template = "services/blocks/sector_service.html"
        icon = "folder-open-inverse"
        label = _("Sector")
