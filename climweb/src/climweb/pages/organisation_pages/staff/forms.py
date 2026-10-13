from io import BytesIO

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import (
    Department,
    StaffEmployment,
    StaffMember,
    StaffPage,
    StaffTrainingAssignment,
    StaffTrainingReport,
)


class StaffInvitationForm(forms.Form):
    member = forms.ModelChoiceField(queryset=StaffMember.objects.exclude(employment__status__in=["retired", "left"]).select_related("department").order_by("name"))
    email = forms.EmailField(max_length=150, help_text="Use the staff member's registered work email. This address is also published by the email icon on their public profile.")


class StaffAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Work email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "username"}))

    def clean_username(self):
        email = self.cleaned_data["username"].strip().lower()
        # Existing platform usernames need not be email addresses. Authenticate
        # through the configured backend with the account's original username.
        User = get_user_model()
        matches = list(User.objects.filter(email__iexact=email, staff_profile_access__isnull=False)[:2])
        if len(matches) > 1:
            raise forms.ValidationError("Unable to sign in with this email. Contact your administrator.")
        return matches[0].get_username() if matches else email
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not hasattr(user, "staff_profile_access"):
            raise forms.ValidationError("This login is for linked staff profile accounts only.", code="invalid_login")
        if not user.staff_profile_access.member.is_current_staff:
            raise forms.ValidationError("This staff profile is no longer active. Contact your administrator.", code="inactive")


class ExistingStaffUserField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        name = user.get_full_name() or user.get_username()
        return f"{name} — {user.email} (username: {user.get_username()})"


class StaffLinkUserForm(forms.Form):
    user = ExistingStaffUserField(
        queryset=get_user_model().objects.filter(is_active=True, staff_profile_access__isnull=True).exclude(email="").order_by("email"),
        label="Existing platform account",
        help_text="Only active accounts not already linked to a staff profile are listed. Check the name, email and username carefully.",
    )
    confirm = forms.BooleanField(label="I have verified this account belongs to this staff member and understand that its registered email will be shown publicly.")


class StaffPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return (user for user in super().get_users(email) if hasattr(user, "staff_profile_access") and user.staff_profile_access.member.is_current_staff)


class StaffOffboardingForm(forms.Form):
    status = forms.ChoiceField(choices=[(StaffEmployment.Status.RETIRED, "Retired"), (StaffEmployment.Status.LEFT, "Left")])
    effective_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}), help_text="Today or a past date. Offboarding takes effect immediately; future scheduling is not supported.")
    disable_account = forms.BooleanField(required=False, label="Also disable the entire linked platform account", help_text="Blocks all account access, including any CMS access. Leave unchecked to preserve other platform access.")
    confirm = forms.BooleanField(label="I confirm this staff member should be removed from the public team and lose profile access.")

    def clean_effective_date(self):
        value = self.cleaned_data["effective_date"]
        if value > timezone.localdate():
            raise forms.ValidationError("Choose today or a past date. Scheduled offboarding is not supported.")
        return value


class StaffReactivationForm(forms.Form):
    confirm = forms.BooleanField(label="Restore this staff member to the public team and allow profile access again.", help_text="A disabled platform account is not automatically enabled. Old invitations and withdrawn submissions remain invalid.")


class StaffProfileForm(forms.Form):
    biography = forms.CharField(required=False, max_length=15000, widget=forms.Textarea(attrs={"rows": 10}), help_text="Plain text; separate paragraphs with a blank line.")
    website = forms.URLField(required=False, label="Professional website")
    linkedin = forms.URLField(required=False, label="LinkedIn profile")
    github = forms.URLField(required=False, max_length=200, label="GitHub profile")
    publications = forms.URLField(required=False, max_length=200, label="Publications URL", help_text="Link to Google Scholar, ORCID or your publications page.")
    photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            "accept": "image/jpeg,image/png,image/webp",
            "data-photo-preview": "true",
        }),
        help_text="JPEG, PNG or WebP, up to 5 MB and 4096 × 4096 pixels. Check the circular preview before saving.",
    )
    discard_photo = forms.BooleanField(required=False, label="Discard my draft photo and keep the current public photo")

    def clean_photo(self):
        upload = self.cleaned_data.get("photo")
        if not upload:
            return None
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The photo must be no larger than 5 MB.")
        try:
            upload.seek(0)
            with Image.open(upload) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise forms.ValidationError("Please upload a JPEG, PNG or WebP photo.")
                if max(image.size) > 4096:
                    raise forms.ValidationError("Photo dimensions must not exceed 4096 pixels.")
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((1600, 1600))
                output = BytesIO()
                image.save(output, format="JPEG", quality=90)
                return output.getvalue()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise forms.ValidationError("The photo could not be read.") from exc


class StaffReviewForm(forms.Form):
    comment = forms.CharField(required=False, max_length=5000, widget=forms.Textarea(attrs={"rows": 3}))
    action = forms.ChoiceField(choices=[("approve", "Approve and publish"), ("request_changes", "Request changes")])

    def clean(self):
        data = super().clean()
        if data.get("action") == "request_changes" and not data.get("comment"):
            self.add_error("comment", "Explain what the staff member needs to change.")
        return data


class StaffCreateForm(StaffProfileForm):
    # Reuse the profile upload validation, but there is no existing photo to discard.
    discard_photo = None
    team_page = forms.ModelChoiceField(queryset=StaffPage.objects.live(), label="Our Team page")
    name = forms.CharField(max_length=100, label="Full name")
    role = forms.CharField(max_length=100, label="Official job title")
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    send_invitation = forms.BooleanField(required=False, initial=True, label="Send an invitation to manage this profile")
    email = forms.EmailField(required=False, max_length=150, label="Work email", help_text="Required only when sending an invitation. Use an email not already assigned to another account.")
    field_order = ["team_page", "name", "role", "department", "biography", "photo", "website", "linkedin", "github", "publications", "send_invitation", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pages = list(self.fields["team_page"].queryset[:2])
        if len(pages) == 1:
            self.fields["team_page"].initial = pages[0].pk

    def clean(self):
        data = super().clean()
        if data.get("send_invitation"):
            email = (data.get("email") or "").strip().lower()
            if not email:
                self.add_error("email", "Enter a work email to send an invitation, or uncheck the invitation option.")
            else:
                User = get_user_model()
                if User.objects.filter(email__iexact=email).exists() or User.objects.filter(**{f"{User.USERNAME_FIELD}__iexact": email}).exists():
                    self.add_error("email", "An account already uses this email address. Create the staff record without an invitation, then choose Link existing user on Staff Profiles.")
                data["email"] = email
        return data


class StaffEditForm(StaffProfileForm):
    discard_photo = None
    name = forms.CharField(max_length=100, label="Full name")
    role = forms.CharField(max_length=100, label="Official job title")
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    source_fingerprint = forms.CharField(widget=forms.HiddenInput)
    field_order = ["name", "role", "department", "biography", "photo", "website", "linkedin", "github", "publications", "source_fingerprint"]


class StaffTrainingAssignmentForm(forms.Form):
    member = forms.ModelMultipleChoiceField(
        queryset=StaffMember.objects.none(),
        label="Staff members",
        help_text="Search for and select one or more staff members for this activity.",
        widget=forms.SelectMultiple(
            attrs={
                "data-searchable-multiselect": "true",
                "data-search-placeholder": "Search staff by name…",
            }
        ),
    )
    activity_type = forms.ChoiceField(label="Activity type", choices=StaffTrainingAssignment.ActivityType.choices)
    title = forms.CharField(max_length=200)
    organizer = forms.CharField(max_length=200, required=False)
    location = forms.CharField(max_length=200, required=False)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    report_due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    status = forms.ChoiceField(choices=StaffTrainingAssignment.Status.choices, initial=StaffTrainingAssignment.Status.NOMINATED)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["member"].queryset = StaffMember.objects.exclude(
            employment__status__in=[StaffEmployment.Status.RETIRED, StaffEmployment.Status.LEFT]
        ).select_related("department").order_by("name")

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
            self.add_error("end_date", "The end date cannot be before the start date.")
        if data.get("report_due_date") and data.get("end_date") and data["report_due_date"] < data["end_date"]:
            self.add_error("report_due_date", "The report due date cannot be before the activity ends.")
        return data

    def save(self, assigned_by):
        values = {
            key: self.cleaned_data[key]
            for key in ["activity_type", "title", "organizer", "location", "description", "start_date", "end_date", "report_due_date", "status"]
        }
        return [
            StaffTrainingAssignment.objects.create(member=member, assigned_by=assigned_by, **values)
            for member in self.cleaned_data["member"]
        ]


class StaffTrainingReportForm(forms.ModelForm):
    class Meta:
        model = StaffTrainingReport
        fields = ["title", "summary", "outcomes", "document", "drive_file_url"]
        labels = {"outcomes": "Key outcomes and follow-up actions"}
        help_texts = {
            "document": "Optional PDF, Word (DOC/DOCX), PowerPoint (PPT/PPTX) or OpenDocument file, up to 10 MB.",
            "drive_file_url": "Optional link to the report in the organization's Google Drive.",
        }
        widgets = {"summary": forms.Textarea(attrs={"rows": 7}), "outcomes": forms.Textarea(attrs={"rows": 5})}

    def clean_document(self):
        upload = self.cleaned_data.get("document")
        if not upload:
            return upload
        if upload.size > 10 * 1024 * 1024:
            raise forms.ValidationError("The report document must be no larger than 10 MB.")
        allowed = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.presentation",
        }
        if getattr(upload, "content_type", "") not in allowed:
            raise forms.ValidationError("Upload a PDF, Word, PowerPoint or OpenDocument file.")
        return upload


class StaffTrainingReportReviewForm(forms.Form):
    action = forms.ChoiceField(choices=[("approve", "Approve report"), ("request_changes", "Request changes")])
    comment = forms.CharField(required=False, max_length=5000, widget=forms.Textarea(attrs={"rows": 4}))

    def clean(self):
        data = super().clean()
        if data.get("action") == "request_changes" and not data.get("comment"):
            self.add_error("comment", "Explain the changes the staff member should make.")
        return data
