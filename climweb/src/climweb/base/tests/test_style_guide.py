from django.test import Client, TestCase
from django.urls import reverse

from climweb.base.models import Theme
from climweb.base.utils import mix_with_white


class TestStyleGuideView(TestCase):
    def setUp(self):
        self.client = Client()

    def test_style_guide_returns_200_for_anonymous_user(self):
        response = self.client.get(reverse("style-guide"))
        self.assertEqual(response.status_code, 200)

    def test_tokens_json_returns_200_with_json_content_type(self):
        response = self.client.get(reverse("style-guide-tokens"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_tokens_json_contains_expected_keys(self):
        response = self.client.get(reverse("style-guide-tokens"))
        data = response.json()
        expected_keys = {"primary", "primary-light", "primary-medium", "background", "text", "border-radius", "box-shadow-elevation"}
        self.assertEqual(set(data.keys()), expected_keys)

    def test_tokens_json_uses_defaults_when_no_theme_configured(self):
        Theme.objects.all().delete()
        response = self.client.get(reverse("style-guide-tokens"))
        data = response.json()
        self.assertEqual(data["primary"], "#0C447C")
        self.assertEqual(data["text"], "#363636")

    def test_style_guide_returns_200_when_no_theme_configured(self):
        Theme.objects.all().delete()
        response = self.client.get(reverse("style-guide"))
        self.assertEqual(response.status_code, 200)

    def test_tokens_match_mix_with_white_when_theme_exists(self):
        Theme.objects.create(
            name="Test Theme",
            primary_hover_color="#1a6b3c",
            primary_color="#222222",
            border_radius=8,
            box_shadow=4,
            is_default=True,
        )
        response = self.client.get(reverse("style-guide-tokens"))
        data = response.json()
        self.assertEqual(data["primary"], "#1a6b3c")
        self.assertEqual(data["primary-light"], mix_with_white("#1a6b3c", 0.75))
        self.assertEqual(data["primary-medium"], mix_with_white("#1a6b3c", 0.50))
        self.assertEqual(data["background"], mix_with_white("#1a6b3c", 0.80))
        self.assertEqual(data["text"], "#222222")
        self.assertEqual(data["border-radius"], f"{8 * 0.06}em")
        self.assertEqual(data["box-shadow-elevation"], "4")

    def test_style_guide_html_contains_section_anchors(self):
        response = self.client.get(reverse("style-guide"))
        content = response.content.decode()
        for anchor in ["colors", "typography", "components", "for-developers"]:
            self.assertIn(f'id="{anchor}"', content, msg=f'Missing section anchor: id="{anchor}"')

    def test_acmad_portal_defaults_generate_expected_tokens(self):
        theme = Theme(name="ACMAD Portal")
        theme.apply_acmad_portal_defaults()

        tokens = theme.as_tokens()

        self.assertEqual(tokens["navy_950"], "#071f2e")
        self.assertEqual(tokens["green_700"], "#087a5a")
        self.assertEqual(tokens["yellow_400"], "#f4c84a")
        self.assertEqual(tokens["ink"], "#132a35")
        self.assertIn("DM Sans", tokens["body_font"])
        self.assertIn("Manrope", tokens["heading_font"])

    def test_restore_acmad_portal_defaults_is_applied_on_save(self):
        theme = Theme.objects.create(
            name="Reset Test",
            primary_hover_color="#111111",
            restore_acmad_portal_defaults=True,
        )

        theme.refresh_from_db()

        self.assertEqual(theme.primary_hover_color, "#087a5a")
        self.assertEqual(theme.header_background_color, "#071f2e")
        self.assertEqual(theme.body_font, "dm_sans")
        self.assertFalse(theme.restore_acmad_portal_defaults)

    def test_climweb_defaults_generate_expected_tokens(self):
        theme = Theme(name="ClimWeb Default")
        theme.apply_climweb_defaults()

        tokens = theme.as_tokens()

        self.assertEqual(tokens["navy_950"], "#176c9c")
        self.assertEqual(tokens["green_700"], "#176c9c")
        self.assertEqual(tokens["sand_50"], "#ffffff")
        self.assertEqual(tokens["ink"], "#363636")
        self.assertIn("Open Sans", tokens["body_font"])
        self.assertIn("Open Sans", tokens["heading_font"])

    def test_restore_climweb_defaults_is_applied_on_save(self):
        theme = Theme.objects.create(
            name="ClimWeb Reset Test",
            primary_hover_color="#111111",
            restore_climweb_defaults=True,
        )

        theme.refresh_from_db()

        self.assertEqual(theme.primary_hover_color, "#176c9c")
        self.assertEqual(theme.header_background_color, "#176c9c")
        self.assertEqual(theme.body_font, "open_sans")
        self.assertEqual(theme.border_radius, 12)
        self.assertFalse(theme.restore_climweb_defaults)
