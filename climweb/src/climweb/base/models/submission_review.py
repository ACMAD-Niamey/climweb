from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class SubmissionReview(models.Model):
    """A staff reviewer's comment/rating on a single Wagtail form submission.

    Every Wagtail form page type generates its own submission model
    dynamically (there is no single shared submissions table across the
    site), so a submission is referenced generically via content_type +
    object_id rather than a FK to one concrete model. This lets the same
    review feature work for any form page (events, data requests, summer
    school applications, ...).
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    submission = GenericForeignKey('content_type', 'object_id')

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submission_reviews',
    )
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("Rating"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]
        verbose_name = _('Submission Review')
        verbose_name_plural = _('Submission Reviews')

    def __str__(self):
        return f"{self.reviewer} review of submission #{self.object_id}"
