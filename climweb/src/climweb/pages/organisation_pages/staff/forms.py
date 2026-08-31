from io import BytesIO

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import StaffMember


class StaffInvitationForm(forms.Form):
    member = forms.ModelChoiceField(queryset=StaffMember.objects.select_related("department").order_by("name"))
    email = forms.EmailField(max_length=150, help_text="Use the staff member's individual work email address.")


class StaffAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Work email", widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "username"}))

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not hasattr(user, "staff_profile_access"):
            raise forms.ValidationError("This login is for invited staff profile accounts only.", code="invalid_login")


class StaffPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return (user for user in super().get_users(email) if hasattr(user, "staff_profile_access"))


class StaffProfileForm(forms.Form):
    biography = forms.CharField(required=False, max_length=15000, widget=forms.Textarea(attrs={"rows": 10}), help_text="Plain text; separate paragraphs with a blank line.")
    website = forms.URLField(required=False, label="Professional website")
    linkedin = forms.URLField(required=False, label="LinkedIn profile")
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
