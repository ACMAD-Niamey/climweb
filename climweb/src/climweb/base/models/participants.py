from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable, Optional

from django.core.validators import FileExtensionValidator
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

    panels = [
        FieldPanel("boundary_file"),
        FieldPanel("iso3_property"),
        FieldPanel("name_property"),
    ]

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
    by_country: dict,
    show_legend: bool = True,
    bounds=None,
) -> dict:
    """Shared template context for the participant map widget.

    Used by both ``ParticipantMapBlock`` and ``OnTheJobTrainingPage`` so the
    ``base/includes/participant_map.html`` partial always gets the same keys.
    """
    return {
        "map_dom_id": map_dom_id,
        "counts_dom_id": f"{map_dom_id}-data",
        "config_dom_id": f"{map_dom_id}-config",
        "participants_by_country": by_country,
        "total_participants": sum(item["total"] for item in by_country.values()),
        "participant_map_config": {
            "boundariesUrl": ParticipantMapSettings.boundaries_url(),
            "bounds": list(bounds) if bounds else DEFAULT_AFRICA_BOUNDS,
            "showLegend": bool(show_legend),
        },
    }
