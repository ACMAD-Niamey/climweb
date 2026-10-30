from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES


class CopDocumentBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=220)
    document = DocumentChooserBlock()
    description = blocks.CharBlock(max_length=300, required=False)

    class Meta:
        icon = "doc-full"
        label = "Document"


class CopGalleryImageBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    caption = blocks.CharBlock(max_length=255, required=False)
    credit = blocks.CharBlock(max_length=160, required=False)

    class Meta:
        icon = "image"
        label = "Gallery image"


class CopPanelistBlock(blocks.StructBlock):
    ROLE_CHOICES = (
        ("moderator", "Moderator"),
        ("panelist", "Panelist"),
        ("speaker", "Speaker"),
        ("discussant", "Discussant"),
    )

    name = blocks.CharBlock(max_length=255)
    image = ImageChooserBlock(required=False)
    organisation = blocks.CharBlock(max_length=255, required=False)
    position = blocks.CharBlock(max_length=255, required=False)
    role = blocks.ChoiceBlock(choices=ROLE_CHOICES, default="panelist")
    topic_title = blocks.CharBlock(max_length=255, required=False, label="Presentation topic")
    bio = blocks.RichTextBlock(
        required=False,
        features=SUMMARY_RICHTEXT_FEATURES,
        label="Short biography",
    )

    class Meta:
        icon = "user"
        label = "Panelist / speaker"


class CopPartnerBlock(blocks.StructBlock):
    name = blocks.CharBlock(max_length=180)
    logo = ImageChooserBlock(required=False)
    website_url = blocks.URLBlock(required=False)

    class Meta:
        icon = "group"
        label = "Partner organisation"

