from django.utils.translation import gettext_lazy as _

from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock


class TimelineBlock(blocks.StructBlock):
    year = blocks.CharBlock(max_length=5)

    milestones = blocks.ListBlock(
        blocks.StructBlock([
            ('period', blocks.CharBlock(max_length=50, required=False,
                                        help_text=_("This can be the month of the year or the exact date. "
                                                  "Leave blank if not known"))),
            ('description', blocks.TextBlock(help_text=_("Describe the milestone"), required=False)),
            ('document', DocumentChooserBlock(
                required=False,
                label=_("Featured supporting document"),
                help_text=_("The milestone title opens this document"),
            )),
            ('additional_documents', blocks.ListBlock(
                DocumentChooserBlock(),
                required=False,
                label=_("Additional supporting documents"),
                help_text=_("Add as many additional documents as needed"),
            )),
        ]))

    class Meta:
        template = 'timeline_block.html'
        icon = 'placeholder'
        label = "Timeline"


class MaterialsDownloadBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=20)
    thumbnail = ImageChooserBlock()

    documents = blocks.ListBlock(
        blocks.StructBlock([
            ('title', blocks.CharBlock()),
            ('document', DocumentChooserBlock())
        ]))

    class Meta:
        template = 'materials_block.html'
        icon = 'placeholder'
        label = "Downloadable materials"
