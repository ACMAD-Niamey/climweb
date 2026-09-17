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
from . import cpc_importer
from .models import (
    RCCARC2ImportConfig, RCCCPCImportConfig, RCCDatasetAsset,
    RCCSeasonalMapAsset, RCCSeasonalMapImportConfig,
    RCCEIN15Asset, RCCEIN15ImportConfig,
)
from .tasks import (
    create_rcc_arc2_run, create_rcc_cpc_run, execute_rcc_arc2_import, execute_rcc_cpc_import,
)


IMPORTERS = {
    "arc2": {
        "label": "ARC2",
        "title": "ARC2 daily station rainfall",
        "model": RCCARC2ImportConfig,
        "catalogue_url": CATALOGUE_URL,
        "discover_countries": discover_countries,
        "discover_stations": discover_stations,
        "validate": validate_catalogue_root,
        "sync_schedule": sync_schedule,
        "create_run": create_rcc_arc2_run,
        "execute": execute_rcc_arc2_import,
        "route": "rcc_arc2_imports",
    },
    "cpc-unified": {
        "label": "CPC-Unified",
        "title": "CPC-Unified estimated daily rainfall",
        "model": RCCCPCImportConfig,
        "catalogue_url": cpc_importer.CATALOGUE_URL,
        "discover_countries": cpc_importer.discover_countries,
        "discover_stations": cpc_importer.discover_stations,
        "validate": cpc_importer.validate_catalogue_root,
        "sync_schedule": cpc_importer.sync_schedule,
        "create_run": create_rcc_cpc_run,
        "execute": execute_rcc_cpc_import,
        "route": "rcc_cpc_imports",
    },
}


class ImportSettingsForm(forms.Form):
    catalogue_url = forms.URLField(max_length=700)
    enabled = forms.BooleanField(required=False)
    interval_hours = forms.IntegerField(min_value=1, max_value=720)
    import_all_stations = forms.BooleanField(required=False)

    def __init__(self, *args, config, validate=validate_catalogue_root, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.validate = validate

    def clean_catalogue_url(self):
        url = self.cleaned_data["catalogue_url"].strip()
        self.validate(url)
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


def _redirect(country=None, route="rcc_arc2_imports"):
    url = reverse(route)
    return redirect(f"{url}?country={quote(country)}" if country else url)


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_imports_view(request):
    rows = []
    for key, importer in IMPORTERS.items():
        config = importer["model"].objects.filter(singleton_key=key).first()
        assets = RCCDatasetAsset.objects.filter(
            key__startswith=f"{key}-", synced_at__isnull=False
        ).exclude(object_name="")
        rows.append({
            "label": importer["title"],
            "source": importer["label"],
            "description": f"{importer['label']} station rainfall",
            "url": reverse(importer["route"]),
            "configured": config is not None,
            "enabled": bool(config and config.enabled),
            "interval_hours": config.interval_hours if config else None,
            "import_all_stations": bool(config and config.import_all_stations),
            "selected_count": len(config.selected_stations) if config else 0,
            "imported_count": assets.count(),
            "last_imported": assets.order_by("-synced_at").values_list("synced_at", flat=True).first(),
            "last_run": config.runs.first() if config else None,
        })
    map_config = RCCSeasonalMapImportConfig.objects.filter(singleton_key="seasonal-maps").first()
    map_assets = RCCSeasonalMapAsset.objects.all()
    rows.append({
        "label": "Seasonal rainfall climatology maps",
        "description": "Archived PNG maps · provisional RCC placement",
        "url": reverse("rcc_seasonal_map_imports"),
        "configured": map_config is not None,
        "enabled": bool(map_config and map_config.enabled),
        "interval_hours": map_config.interval_hours if map_config else None,
        "import_all_maps": bool(map_config and map_config.import_all_maps),
        "selected_count": len(map_config.selected_maps) if map_config else 0,
        "imported_count": map_assets.count(),
        "last_imported": map_assets.order_by("-synced_at").values_list("synced_at", flat=True).first(),
        "last_run": map_config.runs.first() if map_config else None,
        "is_map": True,
    })
    ein15_config = RCCEIN15ImportConfig.objects.filter(singleton_key="ein15").first()
    ein15_assets = RCCEIN15Asset.objects.all()
    rows.append({
        "label": "EIN15 regional model output",
        "description": "Archived NetCDF simulation files · selected import only",
        "url": reverse("rcc_ein15_imports"),
        "configured": ein15_config is not None,
        "enabled": bool(ein15_config and ein15_config.enabled),
        "interval_hours": ein15_config.interval_hours if ein15_config else None,
        "selected_count": len(ein15_config.selected_files) if ein15_config else 0,
        "imported_count": ein15_assets.count(),
        "last_imported": ein15_assets.order_by("-synced_at").values_list("synced_at", flat=True).first(),
        "last_run": ein15_config.runs.first() if ein15_config else None,
        "is_file": True,
    })
    return TemplateResponse(
        request,
        "services/rcc_imports.html",
        {
            "rows": rows,
            "total_imported": sum(row["imported_count"] for row in rows),
            "enabled_count": sum(row["enabled"] for row in rows),
        },
    )


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_arc2_imports_view(request):
    return _importer_view(request, "arc2")


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_cpc_imports_view(request):
    return _importer_view(request, "cpc-unified")


def _importer_view(request, product):
    importer = dict(IMPORTERS[product])
    if product == "arc2":
        # Resolve module functions at request time so existing integrations can patch them.
        importer.update(
            discover_countries=discover_countries,
            discover_stations=discover_stations,
            validate=validate_catalogue_root,
            sync_schedule=sync_schedule,
        )
    route = importer["route"]
    config, _ = importer["model"].objects.get_or_create(
        singleton_key=product, defaults={"catalogue_url": importer["catalogue_url"]}
    )
    requested_country = request.POST.get("country") or request.GET.get("country")
    countries = config.discovered_countries
    if request.POST.get("country") and requested_country not in countries:
        messages.error(request, "Choose a discovered country first.")
        return _redirect(route=route)
    default_country = "Niger" if "Niger" in countries else (countries[0] if countries else None)
    country = requested_country if requested_country in countries else default_country
    settings_form = ImportSettingsForm(
        config=config, validate=importer["validate"],
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
                discovered = importer["discover_countries"](config.catalogue_url)
            except Exception as exc:
                config.discovery_error = str(exc)[:500]
                config.save(update_fields=["discovery_error"])
                messages.error(request, "Country discovery failed. Existing selections were kept.")
            else:
                config.discovered_countries = discovered
                config.discovered_at = timezone.now()
                config.discovery_error = ""
                config.save(update_fields=["discovered_countries", "discovered_at", "discovery_error"])
                messages.success(request, f"Discovered {len(discovered)} {importer['label']} countries.")
            return _redirect(country, route)
        if action == "discover_stations":
            if not country:
                messages.error(request, "Refresh countries first.")
            else:
                try:
                    stations = importer["discover_stations"](country, config.catalogue_url)
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
                    importer["sync_schedule"](config)
                    messages.success(request, f"Discovered {len(stations)} {country} stations.")
            return _redirect(country, route)
        if action == "save_settings":
            settings_form = ImportSettingsForm(request.POST, config=config, validate=importer["validate"])
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
                importer["sync_schedule"](config)
                messages.success(
                    request,
                    "Source URL saved. Refresh countries before importing."
                    if url_changed else f"{importer['label']} importer settings saved.",
                )
                return _redirect(route=route)
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
                    importer["sync_schedule"](config)
                    messages.success(request, f"{country} station selection saved.")
                    return _redirect(country, route)
        if action == "run":
            run = importer["create_run"](config.pk, "manual", request.user)
            if not run:
                messages.error(request, "Enable all stations or select stations, and wait for any active run to finish.")
            else:
                try:
                    importer["execute"].delay(run.pk)
                except Exception as exc:
                    run.status = "failed"
                    run.results = [{"status": "failed", "error": f"Could not queue import: {exc}"[:500]}]
                    run.finished_at = timezone.now()
                    run.save(update_fields=["status", "results", "finished_at"])
                    messages.error(request, "The import could not be queued.")
                else:
                    messages.success(request, f"{importer['label']} import queued.")
            return _redirect(route=route)
    run_rows = []
    for run in config.runs.select_related("requested_by")[:20]:
        failed = [item for item in run.results if item.get("status") == "failed"]
        run_rows.append({"run": run, "completed": len(run.results), "failed": len(failed), "errors": failed[:10]})
    return TemplateResponse(
        request,
        "services/arc2_imports.html",
        {
            "config": config,
            "importer": importer,
            "product": product,
            "country": country,
            "settings_form": settings_form,
            "station_form": station_form,
            "country_station_count": sum(s.startswith(f"{country}/") for s in config.discovered_stations) if country else 0,
            "country_selected_count": sum(s.startswith(f"{country}/") for s in config.selected_stations) if country else 0,
            "run_rows": run_rows,
        },
    )
