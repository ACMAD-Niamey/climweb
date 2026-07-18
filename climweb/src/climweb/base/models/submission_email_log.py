from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class SubmissionEmailLog(models.Model):
    """Audit trail for ad-hoc emails sent to a batch of form submissions from
    the ratings-sorted submissions view (see submissions_ratings_view /
    compose_submission_email_view in climweb.base.views) - lets staff see
    who was emailed, when, with what content, and by whom.

    Submission models are generated per form page type (see SubmissionReview
    for the same reasoning), so the batch is recorded against a page + the
    submissions' own content_type rather than a FK to one concrete model.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    submission_ids = models.JSONField(default=list)
    recipients = models.JSONField(default=list, help_text=_("Email addresses actually sent to"))
    subject = models.CharField(max_length=255)
    body = models.TextField()
    attachment_names = models.JSONField(default=list, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='submission_email_logs',
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _('Submission Email Log')
        verbose_name_plural = _('Submission Email Logs')

    def __str__(self):
        return f"Email to {len(self.recipients)} recipient(s) — {self.subject}"
