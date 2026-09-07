from django.core.exceptions import ObjectDoesNotExist

from climweb.base.models import Theme
from climweb.base.utils import mix_with_white


DEFAULT_THEME_TOKENS = {
    "navy_950": "#0C447C",
    "navy_900": "#363636",
    "navy_800": "#0C447C",
    "green_700": "#0C447C",
    "green_600": "#0C447C",
    "green_100": mix_with_white("#0C447C", 0.80),
    "yellow_400": "#f4c84a",
    "yellow_300": "#f8d66f",
    "blue_100": mix_with_white("#0C447C", 0.80),
    "sand_50": "#ffffff",
    "white": "#ffffff",
    "ink": "#363636",
    "muted": "#61727b",
    "line": "#dce4e5",
    "danger": "#b93535",
    "shadow_sm": "0 8px 28px rgba(9, 42, 55, 0.08)",
    "shadow_lg": "0 24px 70px rgba(2, 24, 35, 0.20)",
    "body_font": '"Open Sans", "Noto Sans Arabic", Arial, sans-serif',
    "heading_font": '"Open Sans", "Noto Sans Arabic", Arial, sans-serif',
    "border_radius": "12px",
    "box_shadow_elevation": "1",
}


def _theme_context(tokens, theme_name=None):
    return {
        "theme_name": theme_name,
        "theme_tokens": tokens,
        # Compatibility aliases used throughout existing ClimWeb templates.
        "primary_color": tokens["green_700"],
        "text_color": tokens["ink"],
        "background_color": tokens["green_100"],
        "secondary_color": tokens["sand_50"],
        "border_radius": tokens["border_radius"],
        "box_shadow": f'elevation-{tokens["box_shadow_elevation"]}',
    }


def theme(request):
    try:
        default_theme = Theme.objects.get(is_default=True)
        return _theme_context(default_theme.as_tokens(), default_theme.name)
    except ObjectDoesNotExist:
        return _theme_context(DEFAULT_THEME_TOKENS.copy())
