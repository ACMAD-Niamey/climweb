from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
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


class TrainingModuleBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=160)
    description = blocks.TextBlock()

    class Meta:
        icon = "pick"
        label = _("Training module")


class RCCTrainingProgrammeBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=180)
    description = blocks.TextBlock()
    icon = IconChooserBlock(required=False, default="graduation-cap")
    page = blocks.PageChooserBlock(required=False)
    external_url = blocks.URLBlock(required=False, max_length=500)
    link_label = blocks.CharBlock(
        max_length=60,
        required=False,
        default=_("Explore programme"),
    )

    class Meta:
        icon = "pick"
        label = _("Training programme or activity")


class RCCTrainingResourceBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=220)
    description = blocks.TextBlock(required=False)
    document = DocumentChooserBlock(required=False)
    external_url = blocks.URLBlock(required=False, max_length=500)
    resource_type = blocks.CharBlock(
        max_length=60,
        required=False,
        default=_("Document"),
    )

    class Meta:
        icon = "doc-full"
        label = _("Training resource")


class RCCTrainingResourceGroupBlock(blocks.StructBlock):
    anchor = blocks.CharBlock(
        max_length=60,
        help_text=_("Short URL-safe name, for example data-rescue."),
    )
    title = blocks.CharBlock(max_length=180)
    description = blocks.TextBlock(required=False)
    icon = IconChooserBlock(required=False, default="doc-full")
    resources = blocks.ListBlock(
        RCCTrainingResourceBlock(),
        required=False,
    )

    class Meta:
        icon = "folder-open-inverse"
        label = _("Training resource group")


class RCCTrainingVideoBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=180)
    description = blocks.TextBlock(required=False)
    youtube_id = blocks.CharBlock(
        max_length=24,
        help_text=_("The value after v= in the YouTube URL."),
    )
    video_url = blocks.URLBlock(max_length=500)

    class Meta:
        icon = "media"
        label = _("Training video")


class RCCRecommendedFunctionBlock(blocks.StructBlock):
    activity = blocks.CharBlock(max_length=180)
    output_title = blocks.CharBlock(max_length=180, label=_("Product or output"))
    description = blocks.TextBlock()
    icon = IconChooserBlock(required=False, default="globe")
    topics = blocks.ListBlock(
        blocks.CharBlock(max_length=100),
        required=False,
        label=_("Topics"),
    )
    related_page = blocks.PageChooserBlock(required=False)
    external_url = blocks.URLBlock(required=False, max_length=500)
    link_label = blocks.CharBlock(max_length=60, required=False)

    class Meta:
        icon = "tasks"
        label = _("Highly recommended function")


class ApplicationStepBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=120)
    description = blocks.RichTextBlock(features=SUMMARY_RICHTEXT_FEATURES)

    class Meta:
        icon = "list-ol"
        label = _("Application step")


class VisitorReportBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=180)
    visitor_name = blocks.CharBlock(max_length=120)
    country_or_institution = blocks.CharBlock(max_length=160, required=False)
    date = blocks.DateBlock(required=False)
    summary = blocks.TextBlock(required=False)
    document = DocumentChooserBlock(required=True)

    class Meta:
        icon = "doc-full"
        label = _("Visitor report")


class TrainingTestimonialBlock(blocks.StructBlock):
    name = blocks.CharBlock(max_length=120)
    organisation = blocks.CharBlock(max_length=160, required=False)
    quote = blocks.TextBlock()
    photo = ImageChooserBlock(required=False)

    class Meta:
        icon = "openquote"
        label = _("Trainee testimony")


class TrainingGalleryItemBlock(blocks.StructBlock):
    media_type = blocks.ChoiceBlock(
        choices=(("image", _("Image")), ("video", _("Video"))),
        default="image",
    )
    image = ImageChooserBlock(required=False)
    video_url = blocks.URLBlock(required=False, help_text=_("YouTube or Vimeo URL"))
    caption = blocks.CharBlock(max_length=180, required=False)

    class Meta:
        icon = "image"
        label = _("Gallery item")


class RCCForumPhotoBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    caption = blocks.CharBlock(max_length=220, required=False)
    credit = blocks.CharBlock(max_length=160, required=False)

    class Meta:
        icon = "image"
        label = _("Forum photo")


class RCCForumDocumentBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=220, required=False)
    date = blocks.DateBlock(required=False)
    document = DocumentChooserBlock(required=True)

    class Meta:
        icon = "doc-full"
        label = _("Forum document")


class TrainingAccommodationBlock(blocks.StructBlock):
    name = blocks.CharBlock(max_length=160)
    description = blocks.TextBlock(required=False)
    address = blocks.CharBlock(max_length=220, required=False)
    website = blocks.URLBlock(required=False)
    contact = blocks.CharBlock(max_length=120, required=False)
    image = ImageChooserBlock(required=False)

    class Meta:
        icon = "home"
        label = _("Accommodation option")


class RCCDatasetBlock(blocks.StructBlock):
    ACCESS_OPEN = "open"
    ACCESS_EXTERNAL = "external"
    ACCESS_REQUEST = "request"
    ACCESS_ARCHIVE = "archive"

    title = blocks.CharBlock(max_length=180)
    description = blocks.TextBlock(required=False)
    coverage = blocks.CharBlock(max_length=120, required=False)
    formats = blocks.CharBlock(
        max_length=100,
        required=False,
        help_text=_("For example NetCDF, CSV, PNG or catalogue."),
    )
    access_type = blocks.ChoiceBlock(
        choices=(
            (ACCESS_OPEN, _("Open access")),
            (ACCESS_EXTERNAL, _("External login required")),
            (ACCESS_REQUEST, _("Available by request")),
            (ACCESS_ARCHIVE, _("Legacy or archive")),
        ),
        default=ACCESS_REQUEST,
    )
    access_url = blocks.URLBlock(max_length=500, required=False)
    local_dataset_key = blocks.CharBlock(
        max_length=80,
        required=False,
        help_text=_("Key for an RCC-hosted dataset page. When set, this replaces the external access URL."),
    )
    source = blocks.CharBlock(max_length=120, required=False)
    last_verified = blocks.DateBlock(required=False)

    class Meta:
        icon = "database"
        label = _("Dataset or data service")


class RCCDataGroupBlock(blocks.StructBlock):
    anchor = blocks.CharBlock(
        max_length=60,
        help_text=_("Short URL-safe name, for example observations or models."),
    )
    title = blocks.CharBlock(max_length=140)
    summary = blocks.TextBlock()
    icon = IconChooserBlock(required=False, default="database")
    datasets = blocks.ListBlock(RCCDatasetBlock(), label=_("Datasets and services"))

    class Meta:
        icon = "folder-open-inverse"
        label = _("Data service group")
