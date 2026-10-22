from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
from django.utils.translation import gettext_lazy as _


class ExternalLinkBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=255)
    link = blocks.URLBlock(max_length=255)

    class Meta:
        template = "external_link_block.html"
        icon = "placeholder"


class GalleryImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(label=_("Image"))
    caption = blocks.CharBlock(
        required=False,
        max_length=255,
        label=_("Caption"),
        help_text=_("Optional caption or image source credit"),
    )

    class Meta:
        icon = "image"
        label = _("Image")


class GalleryUploadedVideoBlock(blocks.StructBlock):
    video = DocumentChooserBlock(
        label=_("Video file"),
        help_text=_("Upload or select a video file, for example MP4 or WebM"),
    )
    caption = blocks.CharBlock(
        required=False,
        max_length=255,
        label=_("Caption"),
    )
    poster = ImageChooserBlock(
        required=False,
        label=_("Poster image"),
        help_text=_("Optional preview image displayed before the video plays"),
    )

    class Meta:
        icon = "media"
        label = _("Uploaded video")


class GalleryHostedVideoBlock(blocks.StructBlock):
    url = blocks.URLBlock(
        label=_("Video URL"),
        help_text=_("YouTube, Vimeo, or another hosted video URL"),
    )
    title = blocks.CharBlock(
        required=False,
        max_length=255,
        label=_("Title"),
    )
    thumbnail = ImageChooserBlock(
        required=False,
        label=_("Thumbnail"),
        help_text=_("Optional preview image"),
    )

    class Meta:
        icon = "link"
        label = _("Hosted video")


class MosaicImageGalleryBlock(blocks.StructBlock):
    title = blocks.CharBlock(
        required=False,
        max_length=255,
        label=_("Gallery title"),
        help_text=_("Optional heading displayed above the gallery"),
    )
    grid_style = blocks.ChoiceBlock(
        choices=[
            ("grid", _("Uniform Grid – all images same height")),
            ("masonry", _("Masonry – images keep natural proportions")),
        ],
        default="masonry",
        label=_("Layout style"),
    )
    columns = blocks.ChoiceBlock(
        choices=[
            ("2", _("2 columns")),
            ("3", _("3 columns")),
            ("4", _("4 columns")),
        ],
        default="3",
        label=_("Columns"),
    )
    images = blocks.ListBlock(GalleryImageBlock(), required=False, label=_("Images"))
    videos = blocks.StreamBlock(
        [
            ("video", GalleryUploadedVideoBlock()),
            ("hosted_video", GalleryHostedVideoBlock()),
        ],
        required=False,
        label=_("Videos"),
        help_text=_("Add uploaded or hosted videos to this gallery"),
    )

    class Meta:
        template = "news/blocks/mosaic_gallery_block.html"
        icon = "media"
        label = _("Image and Video Gallery")
