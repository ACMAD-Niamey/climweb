from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class ClimsaOutputBlock(blocks.StructBlock):
    number = blocks.CharBlock(max_length=2, label=_("Output number"))
    title = blocks.CharBlock(max_length=120, label=_("Title"))
    description = blocks.TextBlock(max_length=260, label=_("Description"))
    page = blocks.PageChooserBlock(required=False, label=_("Internal page"))
    external_url = blocks.URLBlock(required=False, label=_("External URL"))
    image = ImageChooserBlock(required=False, label=_("Image"))

    class Meta:
        icon = "list-ul"
        label = _("Programme output")
