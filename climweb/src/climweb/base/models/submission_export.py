import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def generate_export_token():
    # Looked up directly from the download URL (see download_submission_export_view
    # in climweb.base.views) - unguessable so the token itself is the access
    # control, not just an incrementing pk.
    return secrets.token_urlsafe(32)


class SubmissionExportJob(models.Model):
    """Tracks one background zip export of a form page's submissions (see
    generate_submission_export in climweb.base.tasks). Submission models are
    generated per form page type (see SubmissionReview for the same
    reasoning), so this is recorded against the generic Page rather than a
    FK to one concrete submission model.
    """
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_READY = 'ready'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_PENDING, _('Pending')),
        (STATUS_PROCESSING, _('Processing')),
        (STATUS_READY, _('Ready')),
        (STATUS_FAILED, _('Failed')),
    )

    page = models.ForeignKey(
        'wagtailcore.Page', on_delete=models.CASCADE, related_name='submission_export_jobs',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submission_export_jobs',
    )
    token = models.CharField(max_length=64, unique=True, default=generate_export_token, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    file_name = models.CharField(max_length=255, blank=True, help_text=_("Relative to PRIVATE_EXPORTS_ROOT"))
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    submission_count = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Submission Export Job')
        verbose_name_plural = _('Submission Export Jobs')

    def __str__(self):
        return f"Export of '{self.page}' requested by {self.requested_by} ({self.status})"

    def mark_processing(self):
        self.status = self.STATUS_PROCESSING
        self.save(update_fields=['status'])

    def mark_ready(self, file_name, file_size, submission_count, retention_hours):
        self.status = self.STATUS_READY
        self.file_name = file_name
        self.file_size = file_size
        self.submission_count = submission_count
        self.completed_at = timezone.now()
        self.expires_at = self.completed_at + timezone.timedelta(hours=retention_hours)
        self.save(update_fields=[
            'status', 'file_name', 'file_size', 'submission_count', 'completed_at', 'expires_at',
        ])

    def mark_failed(self, error_message):
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
