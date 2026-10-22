from wagtail.test.utils import WagtailPageTestCase

from climweb.base.form_utils import effective_clean_name
from climweb.pages.home.tests.factories import get_or_create_homepage
from .factories import ContactUsPageFactory


class TestContactUsPageDateFieldDatepicker(WagtailPageTestCase):
    @classmethod
    def setUpTestData(cls):
        home_page = get_or_create_homepage()
        cls.page = ContactUsPageFactory(parent=home_page)
        cls.date_field = cls.page.contact_us_form_fields.create(
            label="Preferred date", field_type="date", required=True, sort_order=0,
        )
        cls.text_field = cls.page.contact_us_form_fields.create(
            label="Name", field_type="singleline", required=True, sort_order=1,
        )
        # ParentalKey children created via the reverse manager stay in-memory
        # until the parent ClusterableModel is saved - without this, the live
        # request (which re-fetches the page fresh from the DB) sees none of
        # the fields above.
        cls.page.save()

    def test_date_field_renders_datepicker_widget_and_assets(self):
        resp = self.client.get(self.page.get_url())
        content = resp.content.decode()

        self.assertIn("datepicker-field", content)
        self.assertIn("new Datepicker(", content)
        # Static files are served through ManifestStaticFilesStorage (hashed
        # filenames), so match the stable prefix rather than the raw name.
        self.assertRegex(content, r'src="[^"]*/static/js/datepicker\.min[^"]*\.js"')
        self.assertRegex(content, r'href="[^"]*/static/css/datepicker-bulma\.min[^"]*\.css"')

    def test_non_date_field_does_not_render_datepicker(self):
        resp = self.client.get(self.page.get_url())
        content = resp.content.decode()

        name_field_id = f"id_{effective_clean_name(self.text_field)}"
        date_field_id = f"id_{effective_clean_name(self.date_field)}"

        # The plain text field's own <input> must not carry the datepicker hook.
        self.assertNotIn(f'id="{name_field_id}" class="input datepicker', content)
        self.assertIn(f'id="{date_field_id}"', content)
