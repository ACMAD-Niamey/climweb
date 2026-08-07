from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock
from wagtailiconchooser.blocks import IconChooserBlock

from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES


class TrainerLinkBlock(blocks.StructBlock):
    icon = IconChooserBlock(required=False, label="Icon")
    text = blocks.CharBlock(max_length=60, required=False, help_text="e.g. LinkedIn, Personal website, Google Scholar")
    url = blocks.URLBlock(help_text="Link URL")

    class Meta:
        icon = "link"
        label = "Link"


class TrainerBlock(blocks.StructBlock):
    TRAINER_ROLE_CHOICES = (
        ("lead_facilitator", "Lead Facilitator"),
        ("facilitator", "Facilitator"),
        ("instructor", "Instructor"),
        ("guest_trainer", "Guest Trainer"),
        ("other", "Other"),
    )
    name = blocks.CharBlock(max_length=255, help_text="Name of trainer")
    image = ImageChooserBlock(required=False, help_text="Select/upload image")
    organisation = blocks.CharBlock(max_length=255, required=False,
                                    help_text="Organisation working for or representing")
    position = blocks.CharBlock(max_length=255, required=False, help_text="Position in organisation")
    bio = blocks.RichTextBlock(required=False, help_text="Full bio, shown in a popup when a visitor "
                                                          "clicks the trainer's card", label="Full bio")
    role = blocks.ChoiceBlock(choices=TRAINER_ROLE_CHOICES, required=False,
                              help_text="Select Role. Leave blank if normal trainer")
    custom_role_name = blocks.CharBlock(max_length=100, required=False, label="Custom role name",
                                        help_text="Only used when Role above is set to \"Other\"")
    module_taught = blocks.CharBlock(max_length=255, required=False, help_text="Trainer's session/module focus")
    links = blocks.ListBlock(TrainerLinkBlock(), required=False, label="Links",
                             help_text="LinkedIn, personal page, Google Scholar, etc. - each with its own icon, "
                                       "label and URL.")

    class Meta:
        icon = "placeholder"
        label = "Trainers"


class ScheduleRoleBlock(blocks.StructBlock):
    SCHEDULE_ROLE_CHOICES = (
        ("lecturer", "Lecturer"),
        ("facilitator", "Facilitator"),
    )
    name = blocks.CharBlock(max_length=255, help_text="Name of person", label="Name of person")
    image = ImageChooserBlock(required=False, help_text="Select/upload image")
    role = blocks.ChoiceBlock(choices=SCHEDULE_ROLE_CHOICES, required=False, default="lecturer",
                              help_text="Select Role")


class ScheduleSessionBlock(blocks.StructBlock):
    SESSION_TYPE_CHOICES = (
        ("foundation", "Foundation"),
        ("sectoral", "Sectoral"),
    )
    start_time = blocks.DateTimeBlock(help_text="Session Start Time")
    end_time = blocks.DateTimeBlock(help_text="Session End Time")
    image = ImageChooserBlock(required=False, help_text="Session Image")
    title = blocks.TextBlock(help_text="Session title")
    detail = blocks.RichTextBlock(required=False, help_text="Detail", features=SUMMARY_RICHTEXT_FEATURES)
    session_type = blocks.ChoiceBlock(choices=SESSION_TYPE_CHOICES, required=False,
                                      help_text="Foundation or Sectoral module")
    roles = blocks.ListBlock(ScheduleRoleBlock())

    class Meta:
        icon = "placeholder"
        label = "Schedule Session"


class CohortBlock(blocks.StructBlock):
    year = blocks.CharBlock(max_length=20, help_text="Cohort year, e.g. 2025")
    location = blocks.CharBlock(max_length=255, required=False)
    photo = ImageChooserBlock(required=False, help_text="Cohort group photo")
    stat_1_value = blocks.CharBlock(max_length=20, required=False)
    stat_1_label = blocks.CharBlock(max_length=60, required=False, help_text="e.g. Training")
    stat_2_value = blocks.CharBlock(max_length=20, required=False)
    stat_2_label = blocks.CharBlock(max_length=60, required=False, help_text="e.g. Projects")
    stat_3_value = blocks.CharBlock(max_length=20, required=False)
    stat_3_label = blocks.CharBlock(max_length=60, required=False, help_text="e.g. Alumni")
    highlights_link_text = blocks.CharBlock(max_length=60, required=False,
                                            default="View highlights and achievements")
    highlights_page = blocks.PageChooserBlock(required=False, label="Highlights - Internal Page")
    highlights_external_url = blocks.URLBlock(required=False, label="Highlights - External URL",
                                              help_text="If provided, the internal page link is ignored")

    class Meta:
        icon = "placeholder"
        label = "Cohort"


class SummerSchoolPartnerBlock(blocks.StructBlock):
    ROLE_CHOICES = (
        ("sponsor", "Sponsor"),
        ("organizer", "Organizer"),
        ("partner", "Partner"),
    )
    name = blocks.CharBlock(max_length=150, help_text="Organisation name")
    logo = ImageChooserBlock(help_text="Organisation logo")
    website_url = blocks.URLBlock(required=False, help_text="Link to the organisation's website")
    role = blocks.ChoiceBlock(choices=ROLE_CHOICES, default="partner", help_text="Sponsor, Organizer, or Partner")

    class Meta:
        icon = "group"
        label = "Sponsor / Organizer / Partner"
