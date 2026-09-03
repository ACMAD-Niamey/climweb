from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable, Optional

from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_countries.fields import Country, CountryField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting

from climweb.base.boundary_utils import BOUNDARY_UPLOAD_EXTENSIONS


# Category of the capacity-building engagement. Stored values are lowercase and
# stable; labels are translatable. Mirrors the STATUS_CHOICES style used by
# RegionalClimateCentre / Product elsewhere in the codebase.
CATEGORY_OJT = "ojt"
CATEGORY_SECONDMENT = "secondment"
CATEGORY_CHOICES = (
    (CATEGORY_OJT, _("On-the-job training")),
    (CATEGORY_SECONDMENT, _("Secondment")),
)

# Gender is recorded so the map can show an aggregate split. "undisclosed" is the
# default so a record is never blocked on a value the programme office does not have.
GENDER_FEMALE = "female"
GENDER_MALE = "male"
GENDER_OTHER = "other"
GENDER_UNDISCLOSED = "undisclosed"
# Order genders are offered in the map filter UI / table columns.
GENDER_ORDER = (GENDER_FEMALE, GENDER_MALE, GENDER_OTHER, GENDER_UNDISCLOSED)

# 5-class sequential colour ramps for the choropleth (ColorBrewer, print- and
# colourblind-safe). The admin picks one by key in Participant map settings.
COLOR_SCHEMES = {
    "amber": ["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"],
    "blue": ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"],
    "green": ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"],
    "purple": ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"],
    "red": ["#fee5d9", "#fcae91", "#fb6a4a", "#de2d26", "#a50f15"],
    "teal": ["#edf8fb", "#b2e2e2", "#66c2a4", "#2ca25f", "#006d2c"],
    "grey": ["#f7f7f7", "#cccccc", "#969696", "#636363", "#252525"],
}
COLOR_SCHEME_CHOICES = (
    ("amber", _("Amber")),
    ("blue", _("Blue")),
    ("green", _("Green")),
    ("purple", _("Purple")),
    ("red", _("Red")),
    ("teal", _("Teal")),
    ("grey", _("Grey")),
)
GENDER_CHOICES = (
    (GENDER_FEMALE, _("Female")),
    (GENDER_MALE, _("Male")),
    (GENDER_OTHER, _("Other")),
    (GENDER_UNDISCLOSED, _("Prefer not to say")),
)


class CapacityBuildingParticipant(models.Model):
    """A single person who took part in an ACMAD capacity-building engagement.

    This is a back-office register maintained by staff (not a public form). It is
    the data source for the auto-generated participant choropleth. Individual
    names are held here for programme administration only and are never exposed on
    the map or in any page context - see ``aggregate_by_country``.
    """

    full_name = models.CharField(
        max_length=200,
        verbose_name=_("Full name"),
        help_text=_("For programme records only. Never shown on the public map."),
    )
    country = CountryField(
        verbose_name=_("Country"),
        help_text=_("Country of the participant's National Meteorological "
                    "and Hydrological Service."),
    )
    institution = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Institution / NMHS"),
    )
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        default=GENDER_UNDISCLOSED,
        verbose_name=_("Gender"),
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_OJT,
        verbose_name=_("Category"),
    )
    start_date = models.DateField(verbose_name=_("Start date"))
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("End date"),
        help_text=_("Leave empty if the engagement is still ongoing."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Include on maps"),
        help_text=_("Untick to keep the record but exclude it from published counts."),
    )
    notes = models.TextField(blank=True, verbose_name=_("Internal notes"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("full_name"),
                FieldPanel("country"),
                FieldPanel("institution"),
                FieldPanel("gender"),
            ],
            heading=_("Participant"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("category"),
                FieldPanel("start_date"),
                FieldPanel("end_date"),
            ],
            heading=_("Engagement"),
        ),
        MultiFieldPanel(
            [FieldPanel("is_active"), FieldPanel("notes")],
            heading=_("Visibility"),
        ),
    ]

    class Meta:
        ordering = ("-start_date", "full_name")
        verbose_name = _("Capacity Building Participant")
        verbose_name_plural = _("Capacity Building Participants")
        indexes = [
            models.Index(fields=["country", "category", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.country.name})"

    @classmethod
    def aggregate_by_country(
        cls,
        categories: Optional[Iterable[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """Return per-country participant counts, keyed by ISO alpha-3 code.

        The returned structure is deliberately name-free - it is safe to hand
        straight to a template / JSON payload::

            {
                "KEN": {
                    "iso_a2": "KE",
                    "name": "Kenya",
                    "total": 4,
                    "by_gender": {"female": 3, "male": 1},
                    "by_category": {"ojt": 3, "secondment": 1},
                },
                ...
            }

        ``categories`` limits to the given category codes (``None`` = all).
        ``date_from`` / ``date_to`` keep only engagements whose
        ``[start_date, end_date]`` interval overlaps the window (an empty
        ``end_date`` counts as still ongoing).
        """
        qs = cls.objects.filter(is_active=True)

        if categories:
            qs = qs.filter(category__in=list(categories))

        if date_to is not None:
            qs = qs.filter(start_date__lte=date_to)
        if date_from is not None:
            qs = qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=date_from))

        rows = qs.values_list("country", "gender", "category")

        buckets: dict[str, dict] = {}
        for country_code, gender, category in rows:
            country = Country(country_code)
            iso_a3 = country.alpha3 or country_code
            bucket = buckets.get(iso_a3)
            if bucket is None:
                bucket = buckets[iso_a3] = {
                    "iso_a2": country_code,
                    "name": country.name or country_code,
                    "total": 0,
                    "by_gender": defaultdict(int),
                    "by_category": defaultdict(int),
                }
            bucket["total"] += 1
            bucket["by_gender"][gender] += 1
            bucket["by_category"][category] += 1

        # Freeze the defaultdicts so the result serialises cleanly.
        for bucket in buckets.values():
            bucket["by_gender"] = dict(bucket["by_gender"])
            bucket["by_category"] = dict(bucket["by_category"])

        return buckets

    @classmethod
    def map_dataset(
        cls,
        categories: Optional[Iterable[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """Name-free dataset that lets the frontend re-aggregate on the client
        as the viewer toggles gender / category / year filters::

            {
              "countries": {"KEN": {"iso_a2": "KE", "name": "Kenya"}, ...},
              "cells": [{"iso3", "gender", "category", "year", "count"}, ...],
              "years": [2024, 2025, 2026],
              "genders": ["female", "male"],        # only those present, in display order
              "categories": ["ojt", "secondment"],  # only those present
            }

        The ``year`` dimension is the engagement's **start year** (intake year),
        so every participant appears in exactly one cell per country - counts are
        never double-counted when the year filter is off.
        """
        qs = cls.objects.filter(is_active=True)
        if categories:
            qs = qs.filter(category__in=list(categories))
        if date_to is not None:
            qs = qs.filter(start_date__lte=date_to)
        if date_from is not None:
            qs = qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=date_from))

        countries: dict[str, dict] = {}
        counts: dict[tuple, int] = defaultdict(int)
        for country_code, gender, category, start in qs.values_list(
            "country", "gender", "category", "start_date"
        ):
            country = Country(country_code)
            iso_a3 = country.alpha3 or country_code
            countries.setdefault(
                iso_a3, {"iso_a2": country_code, "name": country.name or country_code}
            )
            counts[(iso_a3, gender, category, start.year)] += 1

        cells = [
            {"iso3": iso3, "gender": g, "category": c, "year": y, "count": n}
            for (iso3, g, c, y), n in sorted(counts.items())
        ]
        present = set(counts)
        return {
            "countries": countries,
            "cells": cells,
            "years": sorted({key[3] for key in present}),
            "genders": [g for g in GENDER_ORDER if any(key[1] == g for key in present)],
            "categories": [
                c for c in (CATEGORY_OJT, CATEGORY_SECONDMENT)
                if any(key[2] == c for key in present)
            ],
        }


@register_setting(name="participant-map-settings")
class ParticipantMapSettings(BaseSiteSetting):
    """Optional per-site override of the country boundaries used by the
    participant choropleth. When no file is uploaded the bundled Africa
    boundaries (``base/static/base/data/africa.json``) are served instead.
    """

    boundary_file = models.FileField(
        upload_to="participant_map/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(list(BOUNDARY_UPLOAD_EXTENSIONS))],
        verbose_name=_("Country boundaries file"),
        help_text=_(
            "Optional. A GeoJSON (.geojson / .json) file or a zipped shapefile "
            "(.zip) of country polygons. Leave empty to use the built-in Africa "
            "boundaries."
        ),
    )
    iso3_property = models.CharField(
        max_length=60,
        default="iso_a3",
        verbose_name=_("ISO alpha-3 property"),
        help_text=_("Name of the feature property holding the ISO-3166-1 alpha-3 "
                    "country code (e.g. iso_a3, ISO_A3, ADM0_A3, gid_0)."),
    )
    name_property = models.CharField(
        max_length=60,
        default="name",
        blank=True,
        verbose_name=_("Country name property"),
        help_text=_("Name of the feature property holding the country name."),
    )
    color_scheme = models.CharField(
        max_length=20,
        choices=COLOR_SCHEME_CHOICES,
        default="amber",
        verbose_name=_("Map colour scheme"),
        help_text=_("Sequential colour ramp used to shade countries by participant count."),
    )
    no_data_color = models.CharField(
        max_length=7,
        default="#e9edf0",
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", _("Enter a 6-digit hex colour, e.g. #e9edf0."))],
        verbose_name=_("“No participants” colour"),
        help_text=_("Hex colour for countries with no participants in the current view."),
    )

    panels = [
        MultiFieldPanel(
            [FieldPanel("color_scheme"), FieldPanel("no_data_color")],
            heading=_("Appearance"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("boundary_file"),
                FieldPanel("iso3_property"),
                FieldPanel("name_property"),
            ],
            heading=_("Country boundaries"),
        ),
    ]

    def color_ramp(self) -> list:
        return COLOR_SCHEMES.get(self.color_scheme, COLOR_SCHEMES["amber"])

    class Meta:
        verbose_name = _("Participant map settings")

    def clean(self):
        super().clean()
        # Fail early with a helpful message rather than silently falling back to
        # the bundled boundaries when the upload cannot be parsed.
        if self.boundary_file:
            from django.core.exceptions import ValidationError

            from climweb.base.boundary_utils import load_boundary_upload

            try:
                load_boundary_upload(
                    self.boundary_file,
                    self.iso3_property or "iso_a3",
                    self.name_property or "name",
                )
            except ValidationError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise ValidationError({"boundary_file": str(exc)})

    @staticmethod
    def boundaries_url() -> str:
        # Deliberately relative: the boundaries endpoint is always same-origin as
        # the page that fetches it, and an absolute canonical-domain URL would
        # trip CORS when the site is viewed on another host (e.g. in dev).
        return reverse("participant-map-boundaries")


# West, south, east, north - a comfortable frame around continental Africa.
DEFAULT_AFRICA_BOUNDS = [-26.0, -38.0, 64.0, 40.0]


def build_participant_map_context(
    map_dom_id: str,
    categories: Optional[Iterable[str]] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    show_legend: bool = True,
    bounds=None,
    request=None,
) -> dict:
    """Shared template context for the participant map widget.

    Used by both ``ParticipantMapBlock`` and ``OnTheJobTrainingPage`` so the
    ``base/includes/participant_map.html`` partial always gets the same keys.
    ``categories`` / ``date_from`` / ``date_to`` set the outer bound of the data
    that is loaded; the viewer can filter further within it on the client.
    """
    from django.utils.translation import gettext

    categories = list(categories) if categories else None
    fallback = CapacityBuildingParticipant.aggregate_by_country(categories, date_from, date_to)
    dataset = CapacityBuildingParticipant.map_dataset(categories, date_from, date_to)

    if request is not None:
        map_settings = ParticipantMapSettings.for_request(request)
    else:
        from wagtail.models import Site

        site = Site.objects.filter(is_default_site=True).first() or Site.objects.first()
        map_settings = (
            ParticipantMapSettings.for_site(site) if site else ParticipantMapSettings()
        )

    return {
        "map_dom_id": map_dom_id,
        "counts_dom_id": f"{map_dom_id}-data",
        "dataset_dom_id": f"{map_dom_id}-dataset",
        "config_dom_id": f"{map_dom_id}-config",
        # Server-rendered, unfiltered - the no-JS fallback table + the headline count.
        "participants_by_country": fallback,
        "total_participants": sum(item["total"] for item in fallback.values()),
        "participant_map_dataset": dataset,
        "participant_map_config": {
            "boundariesUrl": ParticipantMapSettings.boundaries_url(),
            "bounds": list(bounds) if bounds else DEFAULT_AFRICA_BOUNDS,
            "showLegend": bool(show_legend),
            "colors": {
                "ramp": map_settings.color_ramp(),
                "noData": map_settings.no_data_color or "#e9edf0",
            },
            "labels": {
                "gender": {code: gettext(str(label)) for code, label in GENDER_CHOICES},
                "category": {code: gettext(str(label)) for code, label in CATEGORY_CHOICES},
            },
            "text": {
                "all": gettext("All"),
                "gender": gettext("Gender"),
                "category": gettext("Category"),
                "year": gettext("Year"),
                "country": gettext("Country"),
                "participants": gettext("Participants"),
                "showing": gettext("Showing %(count)s participants"),
                "reset": gettext("Reset filters"),
            },
        },
    }
