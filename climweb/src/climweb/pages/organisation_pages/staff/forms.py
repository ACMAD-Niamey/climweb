from io import BytesIO

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Department, StaffEmployment, StaffMember, StaffPage


class StaffInvitationForm(forms.Form):
    member = forms.ModelChoiceField(queryset=StaffMember.objects.exclude(employment__status__in=["retired", "left"]).select_related("department").order_by("name"))
    email = forms.EmailField(max_length=150, help_text="Use the staff member's registered work email. This address is also published by the email icon on their public profile.")


class StaffAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Work email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "username"}))

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not hasattr(user, "staff_profile_access"):
            raise forms.ValidationError("This login is for invited staff profile accounts only.", code="invalid_login")
        if not user.staff_profile_access.member.is_current_staff:
            raise forms.ValidationError("This staff profile is no longer active. Contact your administrator.", code="inactive")


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
    photo = forms.ImageField(required=False, help_text="JPEG, PNG or WebP, up to 5 MB and 4096 × 4096 pixels.")
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
                    self.add_error("email", "An account already uses this email address. Use a different email, or create the staff record without an invitation.")
                data["email"] = email
        return data


class StaffEditForm(StaffProfileForm):
    discard_photo = None
    name = forms.CharField(max_length=100, label="Full name")
    role = forms.CharField(max_length=100, label="Official job title")
    department = forms.ModelChoiceField(queryset=Department.objects.all())
    source_fingerprint = forms.CharField(widget=forms.HiddenInput)
    field_order = ["name", "role", "department", "biography", "photo", "website", "linkedin", "github", "publications", "source_fingerprint"]
