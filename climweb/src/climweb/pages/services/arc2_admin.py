from urllib.parse import quote

from django import forms
from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .arc2_importer import (
    CATALOGUE_URL,
    discover_countries,
    discover_stations,
    station_id,
    sync_schedule,
    validate_catalogue_root,
)
from .models import RCCARC2ImportConfig
from .tasks import create_rcc_arc2_run, execute_rcc_arc2_import


class ImportSettingsForm(forms.Form):
    catalogue_url = forms.URLField(max_length=700)
    enabled = forms.BooleanField(required=False)
    interval_hours = forms.IntegerField(min_value=1, max_value=720)
    import_all_stations = forms.BooleanField(required=False)

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    def clean_catalogue_url(self):
        url = self.cleaned_data["catalogue_url"].strip()
        validate_catalogue_root(url)
        return url

    def clean(self):
        data = super().clean()
        if data.get("enabled") and data.get("catalogue_url") != self.config.catalogue_url:
            self.add_error("enabled", "Disable the schedule while changing the source URL.")
        if data.get("enabled") and not (data.get("import_all_stations") or self.config.selected_stations):
            self.add_error("enabled", "Select stations or enable all-station imports first.")
        return data


class StationSelectionForm(forms.Form):
    stations = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, *args, config, country, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stations"].choices = [
            (value, value.split("/", 1)[1])
            for value in config.discovered_stations
            if value.startswith(f"{country}/")
        ]


def _redirect(country=None):
    url = reverse("rcc_arc2_imports")
    return redirect(f"{url}?country={quote(country)}" if country else url)


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_arc2_imports_view(request):
    config, _ = RCCARC2ImportConfig.objects.get_or_create(
        singleton_key="arc2", defaults={"catalogue_url": CATALOGUE_URL}
    )
    requested_country = request.POST.get("country") or request.GET.get("country")
    countries = config.discovered_countries
    if request.POST.get("country") and requested_country not in countries:
        messages.error(request, "Choose a discovered country first.")
        return _redirect()
    default_country = "Niger" if "Niger" in countries else (countries[0] if countries else None)
    country = requested_country if requested_country in countries else default_country
    settings_form = ImportSettingsForm(
        config=config,
        initial={
            "catalogue_url": config.catalogue_url,
            "enabled": config.enabled,
            "interval_hours": config.interval_hours,
            "import_all_stations": config.import_all_stations,
        },
    )
    station_form = StationSelectionForm(
        config=config,
        country=country or "",
        initial={"stations": [s for s in config.selected_stations if country and s.startswith(f"{country}/")]},
    )
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "discover_countries":
            try:
                discovered = discover_countries(config.catalogue_url)
            except Exception as exc:
                config.discovery_error = str(exc)[:500]
                config.save(update_fields=["discovery_error"])
                messages.error(request, "Country discovery failed. Existing selections were kept.")
            else:
                config.discovered_countries = discovered
                config.discovered_at = timezone.now()
                config.discovery_error = ""
                config.save(update_fields=["discovered_countries", "discovered_at", "discovery_error"])
                messages.success(request, f"Discovered {len(discovered)} ARC2 countries.")
            return _redirect(country)
        if action == "discover_stations":
            if not country:
                messages.error(request, "Refresh countries first.")
            else:
                try:
                    stations = discover_stations(country, config.catalogue_url)
                except Exception as exc:
                    config.discovery_error = str(exc)[:500]
                    config.save(update_fields=["discovery_error"])
                    messages.error(request, f"Station discovery failed for {country}.")
                else:
                    fresh = {station_id(country, station) for station in stations}
                    config.discovered_stations = sorted(
                        {s for s in config.discovered_stations if not s.startswith(f"{country}/")} | fresh
                    )
                    config.selected_stations = [
                        s for s in config.selected_stations if not s.startswith(f"{country}/") or s in fresh
                    ]
                    config.discovery_error = ""
                    config.save(update_fields=["discovered_stations", "selected_stations", "discovery_error"])
                    sync_schedule(config)
                    messages.success(request, f"Discovered {len(stations)} {country} stations.")
            return _redirect(country)
        if action == "save_settings":
            settings_form = ImportSettingsForm(request.POST, config=config)
            if settings_form.is_valid():
                url_changed = settings_form.cleaned_data["catalogue_url"] != config.catalogue_url
                config.catalogue_url = settings_form.cleaned_data["catalogue_url"]
                config.interval_hours = settings_form.cleaned_data["interval_hours"]
                if url_changed:
                    config.enabled = False
                    config.import_all_stations = False
                    config.discovered_countries = []
                    config.discovered_stations = []
                    config.selected_stations = []
                    config.discovered_at = None
                    config.discovery_error = ""
                else:
                    config.enabled = settings_form.cleaned_data["enabled"]
                    config.import_all_stations = settings_form.cleaned_data["import_all_stations"]
                config.save()
                sync_schedule(config)
                messages.success(
                    request,
                    "Source URL saved. Refresh countries before importing."
                    if url_changed else "ARC2 importer settings saved.",
                )
                return _redirect()
        if action == "save_stations" and country:
            station_form = StationSelectionForm(request.POST, config=config, country=country)
            if station_form.is_valid():
                selected = [s for s in config.selected_stations if not s.startswith(f"{country}/")]
                selected += station_form.cleaned_data["stations"]
                if config.enabled and not config.import_all_stations and not selected:
                    station_form.add_error("stations", "Disable the schedule before clearing its final station.")
                else:
                    config.selected_stations = sorted(set(selected))
                    config.save(update_fields=["selected_stations"])
                    sync_schedule(config)
                    messages.success(request, f"{country} station selection saved.")
                    return _redirect(country)
        if action == "run":
            run = create_rcc_arc2_run(config.pk, "manual", request.user)
            if not run:
                messages.error(request, "Enable all stations or select stations, and wait for any active run to finish.")
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
                    messages.success(request, "ARC2 import queued.")
            return _redirect()
    run_rows = []
    for run in config.runs.select_related("requested_by")[:20]:
        failed = [item for item in run.results if item.get("status") == "failed"]
        run_rows.append({"run": run, "completed": len(run.results), "failed": len(failed), "errors": failed[:10]})
    return TemplateResponse(
        request,
        "services/arc2_imports.html",
        {
            "config": config,
            "country": country,
            "settings_form": settings_form,
            "station_form": station_form,
            "country_station_count": sum(s.startswith(f"{country}/") for s in config.discovered_stations) if country else 0,
            "country_selected_count": sum(s.startswith(f"{country}/") for s in config.selected_stations) if country else 0,
            "run_rows": run_rows,
        },
    )
