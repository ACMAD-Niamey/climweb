from django.db import models
from django.utils.translation import gettext_lazy
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.admin.panels import MultiFieldPanel, FieldPanel
from wagtail.admin.widgets.slug import SlugInput
from wagtail.api.v2.utils import get_full_url
from wagtail.fields import StreamField
from wagtailcache.cache import WagtailCacheMixin
from wagtailmetadata.models import MetadataPageMixin as BaseMetadataPageMixin


class MetadataPageMixin(BaseMetadataPageMixin, WagtailCacheMixin):
    class Meta:
        abstract = True

    promote_panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug", widget=SlugInput),
                FieldPanel("seo_title"),
                FieldPanel("search_description"),
                FieldPanel('search_image'),
            ],
            gettext_lazy("For search engines"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("show_in_menus"),
            ],
            gettext_lazy("For site menus"),
        ),
    ]

    def get_meta_image_url(self, request):
        meta_image = self.get_meta_image_rendition()
        if meta_image:
            return get_full_url(request, meta_image.url)
        return None


class FormPageReviewSettingsMixin(models.Model):
    """Adds submission-review settings to any Wagtail form page sitewide:
    whether staff can rate/comment on submissions (see SubmissionReview +
    submission_review_view in climweb.base), and who receives the automated
    weekly submission-count digest.

    Deliberately does NOT carry a closing-date field itself - a page type
    that wants the pre-deadline summary email either already has its own
    deadline-like field (e.g. SummerSchoolApplicationPage.application_deadline,
    which overrides get_submissions_closing_date() directly - see that model)
    or mixes in FormPageClosingDateMixin below for a generic one. Baking the
    field into this mixin unconditionally left it as a dead, unusable DB
    column on any page that took the "already has a field" path.
    """
    class Meta:
        abstract = True

    enable_submission_ratings = models.BooleanField(
        default=False,
        verbose_name=_("Enable ratings & comments on submissions"),
        help_text=_("If off, staff can only view submissions - the rating/comment "
                    "section is hidden entirely from the review screen."),
    )
    notification_emails = StreamField(
        [('email', blocks.EmailBlock(label=_("Email address")))],
        blank=True, use_json_field=True,
        verbose_name=_("Notification emails"),
        help_text=_("Receives a weekly submission-count digest, and (if a closing "
                    "date is configured) a summary the day before it closes."),
    )

    submission_review_settings_panels = [
        MultiFieldPanel([
            FieldPanel('enable_submission_ratings'),
            FieldPanel('notification_emails'),
        ], heading=_("Submission Review & Notifications")),
    ]

    def get_submissions_closing_date(self):
        """None by default (pre-deadline summary email disabled) - override
        directly (see SummerSchoolApplicationPage) or mix in
        FormPageClosingDateMixin for a generic field-backed implementation."""
        return None

    def get_notification_emails(self):
        return [block.value for block in self.notification_emails if block.value]


class FormPageClosingDateMixin(models.Model):
    """Generic 'submissions closing date' field for form pages that don't
    already have their own deadline-like field. Pages that DO (e.g.
    SummerSchoolApplicationPage.application_deadline) should override
    get_submissions_closing_date() on FormPageReviewSettingsMixin instead of
    also mixing this in, to avoid a second, redundant date field.
    """
    class Meta:
        abstract = True

    submissions_closing_date = models.DateField(
        null=True, blank=True,
        verbose_name=_("Submissions closing date"),
        help_text=_("If set, a summary + link to view submissions is emailed to "
                    "the notification emails above one day before this date."),
    )

    closing_date_panels = [
        FieldPanel('submissions_closing_date'),
    ]

    def get_submissions_closing_date(self):
        return self.submissions_closing_date
