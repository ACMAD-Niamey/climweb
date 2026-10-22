from django import forms
from django.contrib import messages
from django.core.files.storage import storages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .ein15_importer import CATALOGUE_URL, discover_files, sync_schedule, validate_catalogue_url
from .models import RCCEIN15Asset, RCCEIN15ImportConfig
from .tasks import create_rcc_ein15_run, execute_rcc_ein15_import


class EIN15SettingsForm(forms.Form):
    catalogue_url = forms.URLField(max_length=700)
    interval_hours = forms.IntegerField(min_value=1, max_value=8760)
    enabled = forms.BooleanField(required=False)

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config

    def clean_catalogue_url(self):
        value = self.cleaned_data["catalogue_url"].strip()
        validate_catalogue_url(value)
        return value

    def clean(self):
        data = super().clean()
        if data.get("enabled") and data.get("catalogue_url") != self.config.catalogue_url:
            self.add_error("enabled", "Disable automatic imports before changing the source URL.")
        if data.get("enabled") and not self.config.selected_files:
            self.add_error("enabled", "Select files before enabling automatic imports.")
        return data


class EIN15SelectionForm(forms.Form):
    files = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, config, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["files"].choices = [
            (item["filename"], item["filename"])
            for item in config.discovered_files
        ]


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_ein15_imports_view(request):
    config, _ = RCCEIN15ImportConfig.objects.get_or_create(
        singleton_key="ein15", defaults={"catalogue_url": CATALOGUE_URL}
    )
    settings_form = EIN15SettingsForm(config=config, initial={
        "catalogue_url": config.catalogue_url,
        "interval_hours": config.interval_hours,
        "enabled": config.enabled,
    })
    selection_form = EIN15SelectionForm(config=config, initial={"files": config.selected_files})
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "discover":
            try:
                discovered = discover_files(config.catalogue_url)
            except Exception as exc:
                config.discovery_error = str(exc)[:500]
                config.save(update_fields=["discovery_error"])
                messages.error(request, "EIN15 discovery failed. Existing selections were kept.")
            else:
                config.discovered_files = discovered
                names = {item["filename"] for item in discovered}
                config.selected_files = sorted(set(config.selected_files) & names)
                config.discovered_at = timezone.now()
                config.discovery_error = ""
                if config.enabled and not config.selected_files:
                    config.enabled = False
                config.save()
                sync_schedule(config)
                messages.success(request, f"Discovered {len(discovered)} EIN15 NetCDF files.")
            return redirect("rcc_ein15_imports")
        if action == "save_settings":
            settings_form = EIN15SettingsForm(request.POST, config=config)
            if settings_form.is_valid():
                url = settings_form.cleaned_data["catalogue_url"]
                changed = url != config.catalogue_url
                config.catalogue_url = url
                config.interval_hours = settings_form.cleaned_data["interval_hours"]
                if changed:
                    config.enabled = False
                    config.discovered_files = []
                    config.selected_files = []
                    config.discovered_at = None
                    config.discovery_error = ""
                else:
                    config.enabled = settings_form.cleaned_data["enabled"]
                config.save()
                sync_schedule(config)
                messages.success(request, "Refresh the catalogue before selecting files." if changed else "EIN15 settings saved.")
                return redirect("rcc_ein15_imports")
        if action == "save_files":
            selection_form = EIN15SelectionForm(request.POST, config=config)
            if selection_form.is_valid():
                selected = selection_form.cleaned_data["files"]
                if config.enabled and not selected:
                    selection_form.add_error("files", "Disable automatic imports before clearing the selection.")
                else:
                    config.selected_files = selected
                    config.save(update_fields=["selected_files"])
                    sync_schedule(config)
                    messages.success(request, "EIN15 file selection saved.")
                    return redirect("rcc_ein15_imports")
        if action == "run":
            run = create_rcc_ein15_run(config.pk, "manual", request.user)
            if not run:
                messages.error(request, "Select discovered files and wait for any active run to finish.")
            else:
                try:
                    execute_rcc_ein15_import.delay(run.pk)
                except Exception as exc:
                    run.status = "failed"
                    run.results = [{"file": "Queue", "status": "failed", "error": str(exc)[:500]}]
                    run.finished_at = timezone.now()
                    run.save(update_fields=["status", "results", "finished_at"])
                    messages.error(request, "The EIN15 import could not be queued.")
                else:
                    messages.success(request, "EIN15 import queued.")
            return redirect("rcc_ein15_imports")
    run_rows = []
    for run in config.runs.select_related("requested_by")[:20]:
        failed = [item for item in run.results if item.get("status") == "failed"]
        run_rows.append({"run": run, "completed": len(run.results), "failed": failed[:10], "failed_count": len(failed)})
    return TemplateResponse(request, "services/ein15_imports.html", {
        "config": config, "settings_form": settings_form,
        "selection_form": selection_form, "assets": RCCEIN15Asset.objects.all(),
        "run_rows": run_rows,
    })


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_ein15_download(request, asset_id):
    asset = get_object_or_404(RCCEIN15Asset, pk=asset_id)
    storage = storages["rcc_data"]
    if not storage.exists(asset.object_name):
        raise Http404("EIN15 file is not available.")
    response = FileResponse(
        storage.open(asset.object_name, "rb"), as_attachment=True,
        filename=asset.filename, content_type="application/x-netcdf",
    )
    response["Content-Length"] = asset.size_bytes
    response["X-Content-Type-Options"] = "nosniff"
    return response
