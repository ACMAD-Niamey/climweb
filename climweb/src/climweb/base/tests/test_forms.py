from django import forms
from django.test import SimpleTestCase

from climweb.base.forms import CustomFormBuilder


class TestCustomFormBuilderDateField(SimpleTestCase):
    def test_create_date_field_attaches_datepicker_widget_class(self):
        builder = CustomFormBuilder(fields=[])

        date_field = builder.create_date_field(field=None, options={})

        self.assertIsInstance(date_field, forms.DateField)
        self.assertEqual(date_field.widget.attrs.get("class"), "datepicker-field")

    def test_create_date_field_respects_explicit_widget(self):
        # A caller-supplied widget must win over our default, matching the
        # existing create_multiline_field precedent (base/forms.py). Django's
        # Field.__init__ deepcopies the widget, so compare by type/attrs
        # rather than identity.
        builder = CustomFormBuilder(fields=[])
        explicit_widget = forms.DateInput(attrs={"class": "custom"})

        date_field = builder.create_date_field(field=None, options={"widget": explicit_widget})

        self.assertEqual(date_field.widget.attrs.get("class"), "custom")
