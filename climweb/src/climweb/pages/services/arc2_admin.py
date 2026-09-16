from urllib.parse import quote

from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .arc2_importer import (
    catalogue_url_for,
    discover_countries,
    discover_stations,
    sync_schedule,
    validate_catalogue_url,
)
from .models import RCCARC2ImportConfig
from .tasks import create_rcc_arc2_run, execute_rcc_arc2_import


class ImportSettingsForm(forms.Form):
    catalogue_url = forms.URLField(max_length=700)
    stations = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)
    enabled = forms.BooleanField(required=False)
    interval_hours = forms.IntegerField(min_value=1, max_value=720)

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.fields["stations"].choices = [
            (name, name) for name in config.discovered_stations
        ]

    def clean_catalogue_url(self):
        url = self.cleaned_data["catalogue_url"].strip()
        validate_catalogue_url(url, self.config.country)
        return url

    def clean(self):
        data = super().clean()
        if data.get("enabled") and not data.get("stations"):
            self.add_error("stations", "Select at least one discovered station before enabling the schedule.")
        if data.get("enabled") and data.get("catalogue_url") != self.config.catalogue_url:
            self.add_error("enabled", "Disable the schedule while changing the source URL.")
        return data


def _country_redirect(country):
    return redirect(f"{reverse('rcc_arc2_imports')}?country={quote(country)}")


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_arc2_imports_view(request):
    RCCARC2ImportConfig.objects.get_or_create(
        country="Niger", defaults={"catalogue_url": catalogue_url_for("Niger")}
    )
    selected_country = request.POST.get("country") or request.GET.get("country") or "Niger"
    config = get_object_or_404(RCCARC2ImportConfig, country=selected_country)
    form = ImportSettingsForm(
        config=config,
        initial={
            "catalogue_url": config.catalogue_url,
            "stations": config.selected_stations,
            "enabled": config.enabled,
            "interval_hours": config.interval_hours,
        },
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "discover_countries":
            try:
                countries = discover_countries()
            except Exception as exc:
                messages.error(request, f"Country discovery failed: {exc}")
            else:
                RCCARC2ImportConfig.objects.bulk_create(
                    [
                        RCCARC2ImportConfig(country=country, catalogue_url=catalogue_url_for(country))
                        for country in countries
                    ],
                    ignore_conflicts=True,
                )
                messages.success(request, f"Found {len(countries)} ARC2 country directories.")
            return _country_redirect(config.country)
        if action == "discover":
            try:
                discovered = discover_stations(config.country, config.catalogue_url)
            except Exception as exc:
                config.discovery_error = str(exc)[:500]
                config.save(update_fields=["discovery_error"])
                messages.error(request, "Station discovery failed. Existing selections were kept.")
            else:
                config.discovered_stations = discovered
                config.discovered_at = timezone.now()
                config.discovery_error = ""
                config.save(update_fields=["discovered_stations", "discovered_at", "discovery_error"])
                messages.success(request, f"Discovered {len(discovered)} {config.country} ARC2 stations.")
            return _country_redirect(config.country)
        if action == "save":
            form = ImportSettingsForm(request.POST, config=config)
            if form.is_valid():
                url_changed = form.cleaned_data["catalogue_url"] != config.catalogue_url
                config.catalogue_url = form.cleaned_data["catalogue_url"]
                config.interval_hours = form.cleaned_data["interval_hours"]
                if url_changed:
                    config.selected_stations = []
                    config.discovered_stations = []
                    config.discovered_at = None
                    config.discovery_error = ""
                    config.enabled = False
                else:
                    config.selected_stations = form.cleaned_data["stations"]
                    config.enabled = form.cleaned_data["enabled"]
                config.save()
                sync_schedule(config)
                messages.success(
                    request,
                    "Source URL saved. Refresh its stations before importing."
                    if url_changed else "Import settings saved.",
                )
                return _country_redirect(config.country)
        elif action == "run":
            run = create_rcc_arc2_run(config.pk, "manual", request.user)
            if not run:
                messages.error(request, "Select stations first, or wait for this country's active run to finish.")
            else:
                try:
                    execute_rcc_arc2_import.delay(run.pk)
                except Exception as exc:
                    run.status = "failed"
                    run.results = [{"status": "failed", "error": f"Could not queue import: {exc}"[:500]}]
                    run.finished_at = timezone.now()
                    run.save(update_fields=["status", "results", "finished_at"])
                    messages.error(request, "The import could not be queued.")
                else:
                    messages.success(request, "Import queued.")
            return _country_redirect(config.country)
    return TemplateResponse(
        request,
        "services/arc2_imports.html",
        {
            "config": config,
            "configs": RCCARC2ImportConfig.objects.order_by("country"),
            "form": form,
            "runs": config.runs.select_related("requested_by")[:20],
        },
    )
