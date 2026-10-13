from django.conf import settings
from django.db import models
from django.core.files.storage import FileSystemStorage
from django.db.models import Count
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.fields import RichTextField
from wagtail.models import Page, Orderable
from wagtail.snippets.models import register_snippet

from climweb.base.models import AbstractBannerPage
from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES


@register_snippet
class Department(models.Model):
    name = models.CharField(max_length=100)
    desc = RichTextField(features=SUMMARY_RICHTEXT_FEATURES, null=True, blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    panels = [
        FieldPanel('name'),
        FieldPanel('desc'),
        FieldPanel('order')
    ]

    api_fields = [
        APIField('name'),
    ]

    def __str__(self):
        return f"{self.order}. {self.name}"

    class Meta:
        ordering = ['order']


class StaffPage(AbstractBannerPage):
    template = 'staff/staff_page.html'
    parent_page_types = ['organisation.OrganisationIndexPage']
    subpage_types = ['board.DirectorGeneralPage']
    show_in_menus_default = True

    max_count = 1

    introduction_heading = models.CharField(max_length=100, verbose_name=_('Introduction Heading'),
                                            help_text=_("Introduction section heading"), null=True, blank=True,
                                            default="Meet Our Staff")
    introduction_title = models.CharField(max_length=100, verbose_name=_('Introduction Title'),
                                          help_text=_("Introduction section title"), null=True, blank=True)
    introduction_text = RichTextField(features=SUMMARY_RICHTEXT_FEATURES, verbose_name=_('Introduction text'),
                                      help_text=_("Introduction section description"), null=True, blank=True, )

    content_panels = Page.content_panels + [
        *AbstractBannerPage.content_panels,
        MultiFieldPanel([
            FieldPanel('introduction_heading'),
            FieldPanel('introduction_title'),
            FieldPanel('introduction_text'),
        ], heading=_('Introduction Section')),
        InlinePanel('selected_staff', heading=_("Staff shown on this page"), label=_("Staff selection"), help_text=_("Select and order existing staff. Manage their details under Staff Profiles.")),
    ]

    @cached_property
    def current_staffmembers(self):
        # Lifecycle is outside page revisions: publishing an old draft must not
        # accidentally reinstate someone who has left.
        selected_ids = [entry.member_id for entry in self.selected_staff.all()]
        from django.db.models import Case, When, IntegerField
        return StaffMember.objects.filter(pk__in=selected_ids).exclude(
            employment__status__in=["retired", "left"]
        ).select_related("department", "photo", "profile_access__user").order_by(
            Case(*[When(pk=pk, then=order) for order, pk in enumerate(selected_ids)], output_field=IntegerField())
        )

    @cached_property
    def all_departments(self):
        # Annotate the queryset with the count of employees per department
        departments_with_staff_count = self.current_staffmembers.order_by().values('department__name').annotate(
            staffmembers_count=Count('department')).order_by('department__order')
        # Filter departments with at least one employee
        departments_with_staff = departments_with_staff_count.filter(staffmembers_count__gt=0)

        return departments_with_staff

    @cached_property
    def director_general_page(self):
        from climweb.pages.organisation_pages.board.models import DirectorGeneralPage

        return DirectorGeneralPage.objects.child_of(self).live().first()

    class Meta:
        verbose_name = _("Staff Page")


class StaffMember(Orderable):
    page = ParentalKey(StaffPage, on_delete=models.CASCADE, related_name="staffmembers")
    name = models.CharField(max_length=100, verbose_name=_("Staff member's name"),
                            help_text=_("First and Last names of Staff member"))
    role = models.CharField(max_length=100, verbose_name=_("Staff member's role"),
                            help_text=_("The role/position of the Staff member"))
    website = models.URLField(blank=True, verbose_name=_("Professional website"))
    linkedin = models.URLField(blank=True, verbose_name=_("LinkedIn profile"))
    github = models.URLField(blank=True, verbose_name=_("GitHub profile"))
    publications = models.URLField(blank=True, verbose_name=_("Publications URL"), help_text=_("Link to Google Scholar, ORCID or your publications page."))
    public_email = models.EmailField(blank=True, verbose_name=_("Public contact email"), help_text=_("Optional. Published on the website; separate from your private account email."))
    bio = RichTextField(features=SUMMARY_RICHTEXT_FEATURES, null=True, blank=True,
                        verbose_name=_("Staff member Biography"),
                        help_text=_("Optional Summary biography of the Staff member"))
    department = models.ForeignKey(Department, on_delete=models.PROTECT, blank=False, null=True,
                                   verbose_name=_("Staff member's Department"))
    photo = models.ForeignKey(
        'wagtailimages.Image',
        verbose_name=_("Staff member's Profile Image"),
        help_text=_("A high quality square image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
        FieldPanel("bio"),
        FieldPanel("department"),
        FieldPanel("photo"),
        FieldPanel("website"),
        FieldPanel("linkedin"),
        FieldPanel("github"),
        FieldPanel("publications"),
    ]

    class Meta:
        verbose_name = _("Staff Member")
        verbose_name_plural = _("Staff Members")
        ordering = ['sort_order']

    def __str__(self):
        return self.name

    @property
    def is_current_staff(self):
        return not StaffEmployment.objects.filter(member_id=self.pk).exclude(status="active").exists()

    @property
    def registered_email(self):
        access = getattr(self, "profile_access", None)
        return access.user.email if access else ""

    @property
    def is_director_general(self):
        normalized_role = " ".join(self.role.casefold().replace("-", " ").split())
        return "director general" in normalized_role or normalized_role == "dg"


class StaffPageSelection(Orderable):
    page = ParentalKey(StaffPage, on_delete=models.CASCADE, related_name="selected_staff")
    member = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="page_selections", verbose_name=_("Staff member"))

    panels = [FieldPanel("member")]

    class Meta:
        ordering = ["sort_order", "pk"]


class StaffEmployment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Current")
        RETIRED = "retired", _("Retired")
        LEFT = "left", _("Left")

    # Protect retained records/history against deletion through the inline editor.
    member = models.OneToOneField(StaffMember, on_delete=models.PROTECT, related_name="employment")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    effective_date = models.DateField()


class StaffEmploymentEvent(models.Model):
    employment = models.ForeignKey(StaffEmployment, on_delete=models.PROTECT, related_name="events")
    previous_status = models.CharField(max_length=12, choices=StaffEmployment.Status.choices)
    status = models.CharField(max_length=12, choices=StaffEmployment.Status.choices)
    effective_date = models.DateField()
    account_disabled = models.BooleanField(default=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="staff_employment_events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


class StaffProfileAccess(models.Model):
    """Account ownership lives outside the page's revisioned inline records."""

    member = models.OneToOneField(StaffMember, on_delete=models.CASCADE, related_name="profile_access")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile_access")
    invitation_digest = models.CharField(max_length=64, blank=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    profile_only = models.BooleanField(default=True)
    linked_at = models.DateTimeField(null=True, blank=True)
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="staff_accounts_linked")

    def __str__(self):
        return self.member.name


class StaffProfileUpdate(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SUBMITTED = "submitted", _("Awaiting review")
        APPROVED = "approved", _("Approved")
        CHANGES_REQUESTED = "changes_requested", _("Changes requested")
        WITHDRAWN = "withdrawn", _("Withdrawn on offboarding")

    access = models.ForeignKey(StaffProfileAccess, on_delete=models.CASCADE, related_name="updates")
    biography = models.TextField(blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    publications = models.URLField(blank=True)
    public_email = models.EmailField(blank=True)
    # Keep unapproved photos out of the public media library. Limit and re-encode
    # uploads in the form; the authenticated preview endpoint serves these bytes.
    photo_data = models.BinaryField(blank=True, default=bytes)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    source_fingerprint = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_staff_updates")
    reviewer_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        permissions = [("review_staff_profiles", "Can review staff profile submissions")]
        constraints = [
            models.UniqueConstraint(fields=["access"], condition=models.Q(status__in=["draft", "submitted"]), name="staff_one_open_profile_update"),
        ]


class StaffTrainingAssignment(models.Model):
    """A professional activity assignment made by HR for a staff member."""

    class ActivityType(models.TextChoices):
        TRAINING = "training", _("Training")
        WORKSHOP = "workshop", _("Workshop")
        EVENT = "event", _("Conference or event")
        MEETING = "meeting", _("Meeting")
        OTHER = "other", _("Other")

    class Status(models.TextChoices):
        NOMINATED = "nominated", _("Nominated")
        CONFIRMED = "confirmed", _("Confirmed")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    member = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="training_assignments")
    activity_type = models.CharField(max_length=16, choices=ActivityType.choices, default=ActivityType.TRAINING)
    title = models.CharField(max_length=200)
    organizer = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    report_due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOMINATED)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="staff_training_assignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-pk"]

    def __str__(self):
        return f"{self.member.name} — {self.title}"


def staff_report_upload_path(instance, filename):
    # Files are never linked directly; the authenticated download view serves them.
    report = instance.report
    return f"staff-training-reports/{report.assignment.member_id}/{report.assignment_id}/{filename}"


def staff_report_storage():
    # Use a dedicated root regardless of local/test STORAGES overrides.
    return FileSystemStorage(location=settings.PRIVATE_STAFF_REPORTS_ROOT)


class StaffTrainingReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SUBMITTED = "submitted", _("Awaiting review")
        APPROVED = "approved", _("Approved")
        CHANGES_REQUESTED = "changes_requested", _("Changes requested")

    assignment = models.OneToOneField(StaffTrainingAssignment, on_delete=models.CASCADE, related_name="report")
    title = models.CharField(max_length=220)
    summary = models.TextField()
    outcomes = models.TextField(blank=True)
    drive_file_url = models.URLField(blank=True, verbose_name=_("Google Drive file link"))
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_staff_training_reports",
    )
    reviewer_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]

    def __str__(self):
        return self.title


class StaffTrainingReportDocument(models.Model):
    report = models.ForeignKey(StaffTrainingReport, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=staff_report_upload_path, storage=staff_report_storage)
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at", "pk"]

    def __str__(self):
        return self.original_name


class StaffNotificationDelivery(models.Model):
    """Auditable, de-duplicated delivery record for staff workflow email."""

    class Event(models.TextChoices):
        TRAINING_ASSIGNED = "training_assigned", _("Activity assigned")
        REPORT_SUBMITTED = "report_submitted", _("Report submitted")
        REPORT_APPROVED = "report_approved", _("Report approved")
        REPORT_CHANGES_REQUESTED = "report_changes_requested", _("Report changes requested")
        REPORT_DUE_7_DAYS = "report_due_7_days", _("Report due in 7 days")
        REPORT_DUE_3_DAYS = "report_due_3_days", _("Report due in 3 days")
        REPORT_DUE_1_DAY = "report_due_1_day", _("Report due in 1 day")
        REPORT_OVERDUE = "report_overdue", _("Report overdue")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        FAILED = "failed", _("Failed")

    event = models.CharField(max_length=40, choices=Event.choices)
    assignment = models.ForeignKey(
        StaffTrainingAssignment,
        on_delete=models.CASCADE,
        related_name="notification_deliveries",
    )
    report = models.ForeignKey(
        StaffTrainingReport,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notification_deliveries",
    )
    recipient = models.EmailField()
    dedupe_key = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["status", "created_at"], name="staff_notif_status_created")]

    def __str__(self):
        return f"{self.get_event_display()} → {self.recipient}"
