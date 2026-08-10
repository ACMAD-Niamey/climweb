from django import forms
from wagtail import blocks
from wagtail.admin.forms import WagtailAdminModelForm

from climweb.pages.products.models import ProductPage


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
