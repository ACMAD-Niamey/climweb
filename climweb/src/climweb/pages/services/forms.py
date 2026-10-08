from django import forms
from django.utils import timezone

from .models import MeteorologicalService, TrainingProposal, TrainingTopic


class TrainingProposalForm(forms.ModelForm):
    consent = forms.BooleanField(
        label=(
            "I confirm that the information is accurate and consent to ACMAD "
            "using it to assess this training proposal."
        ),
    )
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Leave this field empty",
    )

    class Meta:
        model = TrainingProposal
        fields = (
            "full_name",
            "email",
            "phone",
            "country",
            "organisation",
            "job_title",
            "programme_type",
            "proposal_title",
            "professional_background",
            "objectives",
            "expected_outcomes",
            "preferred_start_date",
            "preferred_end_date",
            "nomination_letter",
            "cv",
            "supporting_document",
            "consent",
        )
        widgets = {
            "professional_background": forms.Textarea(attrs={"rows": 4}),
            "objectives": forms.Textarea(attrs={"rows": 5}),
            "expected_outcomes": forms.Textarea(attrs={"rows": 5}),
            "preferred_start_date": forms.DateInput(attrs={"type": "date"}),
            "preferred_end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organisation"].queryset = MeteorologicalService.objects.filter(
            is_active=True
        )
        self.fields["proposal_title"].queryset = TrainingTopic.objects.all()

    def clean_website(self):
        value = self.cleaned_data.get("website", "")
        if value:
            raise forms.ValidationError("Invalid submission.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        minimum_lengths = {
            "full_name": 2,
            "country": 2,
            "job_title": 2,
            "professional_background": 20,
            "objectives": 20,
            "expected_outcomes": 20,
        }
        for field_name, minimum_length in minimum_lengths.items():
            value = cleaned_data.get(field_name)
            if isinstance(value, str):
                value = value.strip()
                cleaned_data[field_name] = value
                if len(value) < minimum_length:
                    self.add_error(
                        field_name,
                        f"Enter at least {minimum_length} characters.",
                    )

        start_date = cleaned_data.get("preferred_start_date")
        end_date = cleaned_data.get("preferred_end_date")
        programme_type = cleaned_data.get("programme_type")
        if start_date and start_date < timezone.localdate():
            self.add_error(
                "preferred_start_date",
                "The preferred start date cannot be in the past.",
            )
        if start_date and end_date and start_date > end_date:
            self.add_error(
                "preferred_end_date",
                "The preferred end date cannot be earlier than the start date.",
            )
        if start_date and end_date and end_date >= start_date:
            maximum_days = (
                183
                if programme_type == TrainingProposal.PROGRAMME_OJT
                else 366
            )
            if (end_date - start_date).days > maximum_days:
                self.add_error(
                    "preferred_end_date",
                    "The requested period is longer than this programme allows.",
                )
        return cleaned_data
