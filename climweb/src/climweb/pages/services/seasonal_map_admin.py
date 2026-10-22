from django import forms
from django.contrib import messages
from django.core.files.storage import storages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .models import RCCSeasonalMapAsset, RCCSeasonalMapImportConfig
from .seasonal_map_importer import (
    CATALOGUE_URL, discover_maps, sync_schedule, validate_catalogue_url,
)
from .tasks import create_rcc_seasonal_map_run, execute_rcc_seasonal_map_import


class MapSettingsForm(forms.Form):
    catalogue_url = forms.URLField(max_length=700)
    interval_hours = forms.IntegerField(min_value=1, max_value=8760)
    enabled = forms.BooleanField(required=False)
    import_all_maps = forms.BooleanField(required=False)

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    def clean_catalogue_url(self):
        url = self.cleaned_data["catalogue_url"].strip()
        validate_catalogue_url(url)
        return url

    def clean(self):
        data = super().clean()
        if data.get("enabled") and data.get("catalogue_url") != self.config.catalogue_url:
            self.add_error("enabled", "Disable automatic imports before changing the source URL.")
        if data.get("enabled") and not (data.get("import_all_maps") or self.config.selected_maps):
            self.add_error("enabled", "Select maps or enable all-map imports first.")
        return data


class MapSelectionForm(forms.Form):
    maps = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["maps"].choices = [(name, name) for name in config.discovered_maps]


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_seasonal_map_imports_view(request):
    config, _ = RCCSeasonalMapImportConfig.objects.get_or_create(
        singleton_key="seasonal-maps", defaults={"catalogue_url": CATALOGUE_URL}
    )
    settings_form = MapSettingsForm(config=config, initial={
        "catalogue_url": config.catalogue_url,
        "interval_hours": config.interval_hours,
        "enabled": config.enabled,
        "import_all_maps": config.import_all_maps,
    })
    selection_form = MapSelectionForm(config=config, initial={"maps": config.selected_maps})
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "discover":
            try:
                discovered = discover_maps(config.catalogue_url)
            except Exception as exc:
                config.discovery_error = str(exc)[:500]
                config.save(update_fields=["discovery_error"])
                messages.error(request, "Map discovery failed. Existing selections were kept.")
            else:
                config.discovered_maps = discovered
                config.selected_maps = sorted(set(config.selected_maps) & set(discovered))
                config.discovered_at = timezone.now()
                config.discovery_error = ""
                if config.enabled and not (config.import_all_maps or config.selected_maps):
                    config.enabled = False
                config.save()
                sync_schedule(config)
                messages.success(request, f"Discovered {len(discovered)} seasonal maps.")
            return redirect("rcc_seasonal_map_imports")
        if action == "save_settings":
            settings_form = MapSettingsForm(request.POST, config=config)
            if settings_form.is_valid():
                new_url = settings_form.cleaned_data["catalogue_url"]
                url_changed = new_url != config.catalogue_url
                config.catalogue_url = new_url
                config.interval_hours = settings_form.cleaned_data["interval_hours"]
                if url_changed:
                    config.enabled = False
                    config.import_all_maps = False
                    config.discovered_maps = []
                    config.selected_maps = []
                    config.discovered_at = None
                    config.discovery_error = ""
                else:
                    config.enabled = settings_form.cleaned_data["enabled"]
                    config.import_all_maps = settings_form.cleaned_data["import_all_maps"]
                config.save()
                sync_schedule(config)
                messages.success(request, "Source saved. Refresh the catalogue before importing." if url_changed else "Map importer settings saved.")
                return redirect("rcc_seasonal_map_imports")
        if action == "save_maps":
            selection_form = MapSelectionForm(request.POST, config=config)
            if selection_form.is_valid():
                selected = selection_form.cleaned_data["maps"]
                if config.enabled and not config.import_all_maps and not selected:
                    selection_form.add_error("maps", "Disable automatic imports before clearing the final map.")
                else:
                    config.selected_maps = selected
                    config.save(update_fields=["selected_maps"])
                    sync_schedule(config)
                    messages.success(request, "Map selection saved.")
                    return redirect("rcc_seasonal_map_imports")
        if action == "run":
            run = create_rcc_seasonal_map_run(config.pk, "manual", request.user)
            if not run:
                messages.error(request, "Select maps or enable all maps, and wait for any active run to finish.")
            else:
                try:
                    execute_rcc_seasonal_map_import.delay(run.pk)
                except Exception as exc:
                    run.status = "failed"
                    run.results = [{"map": "Queue", "status": "failed", "error": str(exc)[:500]}]
                    run.finished_at = timezone.now()
                    run.save(update_fields=["status", "results", "finished_at"])
                    messages.error(request, "The import could not be queued.")
                else:
                    messages.success(request, "Seasonal map import queued.")
            return redirect("rcc_seasonal_map_imports")
    run_rows = []
    for run in config.runs.select_related("requested_by")[:20]:
        failed = [item for item in run.results if item.get("status") == "failed"]
        run_rows.append({"run": run, "completed": len(run.results), "failed": failed[:10], "failed_count": len(failed)})
    return TemplateResponse(request, "services/seasonal_map_imports.html", {
        "config": config, "settings_form": settings_form, "selection_form": selection_form,
        "assets": RCCSeasonalMapAsset.objects.all(), "run_rows": run_rows,
    })


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_seasonal_map_preview(request, asset_id):
    asset = get_object_or_404(RCCSeasonalMapAsset, pk=asset_id)
    storage = storages["rcc_data"]
    if not storage.exists(asset.object_name):
        raise Http404("Map image is not available.")
    response = FileResponse(storage.open(asset.object_name, "rb"), content_type="image/png")
    response["Content-Length"] = asset.size_bytes
    response["X-Content-Type-Options"] = "nosniff"
    return response
