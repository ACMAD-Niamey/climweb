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
    submission_review_view in climweb.base), who receives the automated
    weekly submission-count digest and (if a closing date is set) the
    pre-deadline summary email, and that closing date itself.

    A page type that already has its own deadline-like field (e.g.
    SummerSchoolApplicationPage.application_deadline) should override
    get_submissions_closing_date() to return that field instead of adding
    a second, redundant one - see that model for the pattern.
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
                    "date is set below) a summary the day before it closes."),
    )
    submissions_closing_date = models.DateField(
        null=True, blank=True,
        verbose_name=_("Submissions closing date"),
        help_text=_("If set, a summary + link to view submissions is emailed to "
                    "the notification emails above one day before this date."),
    )

    submission_review_settings_panels = [
        MultiFieldPanel([
            FieldPanel('enable_submission_ratings'),
            FieldPanel('notification_emails'),
            FieldPanel('submissions_closing_date'),
        ], heading=_("Submission Review & Notifications")),
    ]

    def get_submissions_closing_date(self):
        return self.submissions_closing_date

    def get_notification_emails(self):
        return [block.value for block in self.notification_emails if block.value]
