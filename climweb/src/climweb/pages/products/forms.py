import json
import re
from datetime import datetime

from django import forms
from wagtail import blocks
from wagtail.admin.forms import WagtailAdminModelForm

from climweb.pages.products.models import (
    ConfiguredProductImporter,
    ProductImportSourceConfig,
    ProductPage,
    ProductSubscriber,
)


class ProductSubscriptionForm(forms.Form):
    name = forms.CharField(max_length=255, required=False)
    email = forms.EmailField()
    sector = forms.ChoiceField(
        choices=ProductSubscriber.Sector.choices,
        initial=ProductSubscriber.Sector.AGRICULTURE,
        required=False,
    )
    organization_type = forms.ChoiceField(
        label="Type of Organisation",
        choices=ProductSubscriber.OrganizationType.choices,
        initial=ProductSubscriber.OrganizationType.PUBLIC_SECTOR,
        required=False,
    )
    organization_name = forms.CharField(
        label="Name of Organisation",
        max_length=255,
        required=False,
    )
    product_families = forms.MultipleChoiceField(
        label="Products",
        widget=forms.CheckboxSelectMultiple,
        help_text="Choose the product families you want to receive.",
    )
    consent = forms.BooleanField(
        label="I agree to receive ACMAD product notifications by email."
    )

    def __init__(self, *args, **kwargs):
        from .import_registry import get_product_import_definitions

        super().__init__(*args, **kwargs)
        self.fields["product_families"].choices = [
            (definition["key"], definition["label"])
            for definition in get_product_import_definitions()
            if not definition.get("is_archived")
        ]

def clean_email(self):
    email = self.cleaned_data.get("email")
    return email.strip().lower() if email else email


class ProductSubscriptionPreferencesForm(ProductSubscriptionForm):
    consent = None

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            return email.strip().lower()
        return email


class ProductImportRunForm(forms.Form):
    mode = forms.ChoiceField(
        choices=(
            ("preview", "Preview only (dry run)"),
            ("import", "Import and publish"),
        ),
        initial="preview",
    )
    from_date = forms.DateField(
        label="From date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    to_date = forms.DateField(
        label="To date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    limit = forms.IntegerField(
        min_value=1,
        max_value=1000,
        initial=100,
        help_text="Maximum issue dates or records to process.",
    )
    refresh_existing = forms.BooleanField(
        required=False,
        help_text="Redownload sources that were already imported.",
    )
    retry_failures = forms.BooleanField(
        required=False,
        help_text="Retry previously failed sources when supported.",
    )

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get("from_date")
        to_date = cleaned_data.get("to_date")
        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError(
                "From date cannot be later than to date."
            )
        return cleaned_data


class ProductImportScheduleForm(forms.Form):
    interval_hours = forms.IntegerField(
        label="Run every (hours)",
        min_value=1,
        max_value=720,
        help_text="Choose a value from 1 hour to 30 days (720 hours).",
        widget=forms.NumberInput(attrs={"min": 1, "max": 720}),
    )


class ProductImportSourceConfigForm(forms.ModelForm):
    allowed_extensions = forms.CharField(
        label="Allowed file extensions",
        help_text="Comma-separated extensions, for example: .png, .jpg",
    )
    request_headers = forms.CharField(
        required=False,
        label="Request headers (JSON)",
        help_text='Optional JSON object, for example: {"Accept": "text/html"}',
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = ProductImportSourceConfig
        fields = (
            "source_type",
            "source_url",
            "source_system",
            "allowed_extensions",
            "filename_pattern",
            "date_format",
            "history_url_pattern",
            "request_headers",
        )
        widgets = {
            "filename_pattern": forms.Textarea(attrs={"rows": 2}),
            "history_url_pattern": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            "filename_pattern": (
                "Regular expression containing a named 'date' group."
            ),
            "date_format": "Python date format matching the captured date.",
            "history_url_pattern": (
                "Regular expression used to find historical archive pages."
            ),
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        instance = kwargs.get("instance")
        if instance and instance.pk:
            initial = {
                **initial,
                "allowed_extensions": ", ".join(instance.allowed_extensions),
                "request_headers": json.dumps(
                    instance.request_headers, indent=2, sort_keys=True
                ),
            }
        elif initial:
            initial = {
                **initial,
                "allowed_extensions": ", ".join(
                    initial.get("allowed_extensions", [])
                ),
                "request_headers": json.dumps(
                    initial.get("request_headers", {}), indent=2, sort_keys=True
                ),
            }
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

    def clean_allowed_extensions(self):
        values = [
            value.strip().lower()
            for value in self.cleaned_data["allowed_extensions"].split(",")
            if value.strip()
        ]
        if not values:
            raise forms.ValidationError("Enter at least one file extension.")
        invalid = [value for value in values if not re.fullmatch(r"\.[a-z0-9]+", value)]
        if invalid:
            raise forms.ValidationError(
                "Extensions must begin with a dot, for example .png."
            )
        return list(dict.fromkeys(values))

    def clean_request_headers(self):
        raw_value = self.cleaned_data.get("request_headers", "").strip()
        if not raw_value:
            return {}
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Enter valid JSON: {exc.msg}.") from exc
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in value.items()
        ):
            raise forms.ValidationError(
                "Headers must be a JSON object containing string values."
            )
        return value

    def clean(self):
        cleaned_data = super().clean()
        pattern = cleaned_data.get("filename_pattern")
        date_format = cleaned_data.get("date_format")
        if pattern:
            try:
                compiled = re.compile(pattern)
            except re.error as exc:
                self.add_error("filename_pattern", f"Invalid regular expression: {exc}")
            else:
                if "date" not in compiled.groupindex:
                    self.add_error(
                        "filename_pattern",
                        "The expression must contain a named (?P<date>...) group.",
                    )
        history_pattern = cleaned_data.get("history_url_pattern")
        if history_pattern:
            try:
                re.compile(history_pattern)
            except re.error as exc:
                self.add_error(
                    "history_url_pattern", f"Invalid regular expression: {exc}"
                )
        if date_format:
            try:
                sample = datetime(2026, 8, 10).strftime(date_format)
                datetime.strptime(sample, date_format)
            except (TypeError, ValueError):
                self.add_error(
                    "date_format",
                    "Enter a valid date format, such as %Y%m%d.",
                )
        return cleaned_data


class ConfiguredProductImporterForm(forms.ModelForm):
    source_type = forms.ChoiceField(
        choices=ProductImportSourceConfig.SOURCE_TYPE_CHOICES,
        label="Source type",
    )
    source_url = forms.URLField(label="Source URL", max_length=1000)
    source_system = forms.CharField(label="Source name", max_length=255)
    allowed_extensions = forms.CharField(
        label="Allowed file extensions",
        help_text="Comma-separated PDF/image extensions, for example: .pdf, .jpg",
    )
    filename_pattern = forms.CharField(
        label="Filename pattern",
        help_text="Regular expression containing a named (?P<date>...) group.",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    date_format = forms.CharField(
        initial="%Y%m%d",
        label="Date format",
        help_text="Python date format matching the captured date, for example %Y%m%d.",
    )
    history_url_pattern = forms.CharField(
        required=False,
        label="Historical archive pattern",
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    request_headers = forms.CharField(
        required=False,
        initial="{}",
        label="Request headers (JSON)",
        help_text="Optional non-secret HTTP headers. Credentials must not be stored here.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    class Meta:
        model = ConfiguredProductImporter
        fields = (
            "label",
            "key",
            "product_page",
            "product_item_type",
            "status",
            "default_interval_hours",
        )
        help_texts = {
            "status": "Save as draft until the source preview has been checked.",
            "default_interval_hours": "Automatic check interval from 1 hour to 30 days.",
        }

    def __init__(self, *args, source_config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            choice
            for choice in ConfiguredProductImporter.STATUS_CHOICES
            if choice[0] != ConfiguredProductImporter.STATUS_ARCHIVED
        ]
        if self.instance and self.instance.pk:
            self.fields["key"].disabled = True
            self.fields["key"].help_text = (
                "The importer key is permanent because import history and schedules use it."
            )
            values = source_config or self.instance.default_source_config
            if values:
                self.initial.update(
                    {
                        "source_type": values.get("source_type"),
                        "source_url": values.get("source_url"),
                        "source_system": values.get("source_system"),
                        "allowed_extensions": ", ".join(
                            values.get("allowed_extensions", [])
                        ),
                        "filename_pattern": values.get("filename_pattern"),
                        "date_format": values.get("date_format"),
                        "history_url_pattern": values.get(
                            "history_url_pattern", ""
                        ),
                        "request_headers": json.dumps(
                            values.get("request_headers", {}),
                            indent=2,
                            sort_keys=True,
                        ),
                    }
                )

    def clean_allowed_extensions(self):
        values = [
            value.strip().lower()
            for value in self.cleaned_data["allowed_extensions"].split(",")
            if value.strip()
        ]
        supported = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}
        if not values:
            raise forms.ValidationError("Enter at least one file extension.")
        invalid = [value for value in values if value not in supported]
        if invalid:
            raise forms.ValidationError(
                "Only PDF and image files are supported: .pdf, .jpg, .jpeg, "
                ".png, .gif and .webp."
            )
        return list(dict.fromkeys(values))

    def clean_request_headers(self):
        raw_value = self.cleaned_data.get("request_headers", "").strip()
        if not raw_value:
            return {}
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Enter valid JSON: {exc.msg}.") from exc
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in value.items()
        ):
            raise forms.ValidationError(
                "Headers must be a JSON object containing string values."
            )
        sensitive = {"authorization", "cookie", "proxy-authorization", "x-api-key"}
        if sensitive.intersection(key.lower() for key in value):
            raise forms.ValidationError(
                "Authentication secrets cannot be stored in this form."
            )
        return value

    def clean(self):
        cleaned_data = super().clean()
        pattern = cleaned_data.get("filename_pattern")
        if pattern:
            try:
                compiled = re.compile(pattern)
            except re.error as exc:
                self.add_error("filename_pattern", f"Invalid regular expression: {exc}")
            else:
                if "date" not in compiled.groupindex:
                    self.add_error(
                        "filename_pattern",
                        "The expression must contain a named (?P<date>...) group.",
                    )
        history_pattern = cleaned_data.get("history_url_pattern")
        if history_pattern:
            try:
                re.compile(history_pattern)
            except re.error as exc:
                self.add_error(
                    "history_url_pattern", f"Invalid regular expression: {exc}"
                )
        date_format = cleaned_data.get("date_format")
        if date_format:
            try:
                sample = datetime(2026, 8, 10).strftime(date_format)
                datetime.strptime(sample, date_format)
            except (TypeError, ValueError):
                self.add_error(
                    "date_format",
                    "Enter a valid date format, such as %Y%m%d.",
                )
        product_page = cleaned_data.get("product_page")
        item_type = cleaned_data.get("product_item_type")
        if (
            product_page
            and item_type
            and item_type.category.product_id != product_page.product_id
        ):
            self.add_error(
                "product_item_type",
                "Select a product type belonging to the destination product page.",
            )
        return cleaned_data

    def clean_key(self):
        key = self.cleaned_data["key"]
        from climweb.pages.products.import_registry import PRODUCT_IMPORTS_BY_KEY

        if key in PRODUCT_IMPORTS_BY_KEY:
            raise forms.ValidationError(
                "This key is reserved by a built-in importer."
            )
        return key

    @property
    def source_values(self):
        return {
            field: self.cleaned_data[field]
            for field in (
                "source_type",
                "source_url",
                "source_system",
                "allowed_extensions",
                "filename_pattern",
                "date_format",
                "history_url_pattern",
                "request_headers",
            )
        }


class ProductLayerForm(WagtailAdminModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")

        if instance:
            products_item_types = instance.product.product_item_types
            map_layers_field = self.fields.get("map_layers")

            for block_type, block in map_layers_field.block.child_blocks.items():
                block_name = "product_type"
                product_type_block = block.child_blocks.get(block_name)
                if product_type_block:
                    label = product_type_block.label or block_name
                    map_layers_field.block.child_blocks[block_type].child_blocks[block_name] = blocks.ChoiceBlock(
                        required=False, choices=products_item_types)
                    map_layers_field.block.child_blocks[block_type].child_blocks[block_name].name = block_name
                    map_layers_field.block.child_blocks[block_type].child_blocks[block_name].label = label

    class Meta:
        model = ProductPage
        fields = ["map_layers"]
