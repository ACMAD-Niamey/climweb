from wagtail.models import Site
from wagtail.test.utils import WagtailPageTestCase

from climweb.base.models import NavigationSettings
from climweb.pages.home.tests.factories import get_or_create_homepage


class FeaturedNavigationTests(WagtailPageTestCase):
    def test_highlighted_activity_link_is_rendered_after_main_menu(self):
        home = get_or_create_homepage()
        site = Site.objects.get(is_default_site=True)
        navigation, _ = NavigationSettings.objects.get_or_create(site=site)
        navigation.featured_navigation_enabled = True
        navigation.featured_navigation_label = "COP 31"
        navigation.featured_navigation_page = home
        navigation.save()

        response = self.client.get(home.url)

        self.assertContains(response, 'class="navbar-item nav-item-link nav-item-link--featured"')
        self.assertContains(response, "COP 31")

    def test_highlighted_activity_fields_are_editable(self):
        field_names = {field.name for field in NavigationSettings._meta.get_fields()}

        self.assertIn("featured_navigation_enabled", field_names)
        self.assertIn("featured_navigation_label", field_names)
        self.assertIn("featured_navigation_page", field_names)
        self.assertIn("featured_navigation_external_url", field_names)
