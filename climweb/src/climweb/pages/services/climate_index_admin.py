from django import forms
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from wagtail.admin.auth import user_passes_test

from .climate_index_importer import sync_schedule, validate_source_url
from .models import RCCClimateIndexAsset, RCCClimateIndexImportConfig
from .tasks import create_rcc_climate_index_run, execute_rcc_climate_index_import


class ClimateIndexSettingsForm(forms.Form):
    interval_hours = forms.IntegerField(min_value=1, max_value=8760)
    enabled = forms.BooleanField(required=False)

    def clean_enabled(self):
        enabled = self.cleaned_data["enabled"]
        if enabled and not RCCClimateIndexAsset.objects.filter(active=True).exists():
            raise forms.ValidationError("Add or activate a graph before enabling automatic imports.")
        return enabled


class ClimateIndexAssetForm(forms.ModelForm):
    SCOPE_CHOICES = (
        ("central-africa", "Central Africa study"),
        ("africa", "Africa-wide analysis"),
        ("other", "Other"),
    )
    scope = forms.ChoiceField(choices=SCOPE_CHOICES)

    class Meta:
        model = RCCClimateIndexAsset
        fields = ("legacy_index", "title", "scope", "period", "description", "source_url", "active")
        labels = {"legacy_index": "Display order"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_source_url(self):
        value = self.cleaned_data["source_url"].strip()
        validate_source_url(value)
        return value


def _queue_run(request, config, asset_ids=None):
    run = create_rcc_climate_index_run(config.pk, "manual", request.user, asset_ids=asset_ids)
    if not run:
        messages.error(request, "Select an active graph and wait for any current climate-index import to finish.")
        return
    try:
        execute_rcc_climate_index_import.delay(run.pk)
    except Exception as exc:
        run.status = "failed"
        run.results = [{"title": "Queue", "status": "failed", "error": str(exc)[:500]}]
        from django.utils import timezone
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "results", "finished_at"])
        messages.error(request, "The climate-index import could not be queued.")
    else:
        messages.success(request, f"Climate-index import queued for {len(run.asset_ids)} graph(s).")


@user_passes_test(lambda user: user.is_superuser or user.has_perm("wagtailadmin.access_admin"))
def rcc_climate_index_imports_view(request):
    config, _ = RCCClimateIndexImportConfig.objects.get_or_create(singleton_key="climate-indices")
    edit_id = request.GET.get("edit")
    edited_asset = get_object_or_404(RCCClimateIndexAsset, pk=edit_id) if edit_id else None
    settings_form = ClimateIndexSettingsForm(initial={
        "interval_hours": config.interval_hours, "enabled": config.enabled,
    })
    next_order = (RCCClimateIndexAsset.objects.order_by("-legacy_index").values_list("legacy_index", flat=True).first() or 0) + 1
    asset_form = ClimateIndexAssetForm(
        instance=edited_asset,
        initial={} if edited_asset else {"legacy_index": next_order, "active": True},
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_settings":
            settings_form = ClimateIndexSettingsForm(request.POST)
            if settings_form.is_valid():
                config.interval_hours = settings_form.cleaned_data["interval_hours"]
                config.enabled = settings_form.cleaned_data["enabled"]
                config.save(update_fields=["interval_hours", "enabled"])
                sync_schedule(config)
                messages.success(request, "Climate-index schedule saved.")
                return redirect("rcc_climate_index_imports")
        elif action == "save_asset":
            posted_id = request.POST.get("asset_id")
            instance = get_object_or_404(RCCClimateIndexAsset, pk=posted_id) if posted_id else None
            asset_form = ClimateIndexAssetForm(request.POST, instance=instance)
            if asset_form.is_valid():
                asset = asset_form.save()
                if config.enabled and not RCCClimateIndexAsset.objects.filter(active=True).exists():
                    config.enabled = False
                    config.save(update_fields=["enabled"])
                sync_schedule(config)
                messages.success(request, f"Saved graph source: {asset.title}.")
                return redirect(f"{reverse('rcc_climate_index_imports')}?edit={asset.pk}")
        elif action == "run_all":
            _queue_run(request, config)
            return redirect("rcc_climate_index_imports")
        elif action == "run_asset":
            asset = get_object_or_404(RCCClimateIndexAsset, pk=request.POST.get("asset_id"))
            _queue_run(request, config, [asset.pk])
            return redirect("rcc_climate_index_imports")

    assets = RCCClimateIndexAsset.objects.prefetch_related("versions").all()
    run_rows = []
    for run in config.runs.select_related("requested_by")[:20]:
        failures = [item for item in run.results if item.get("status") == "failed"]
        run_rows.append({"run": run, "failed": failures[:10], "failed_count": len(failures)})
    return TemplateResponse(request, "services/climate_index_imports.html", {
        "config": config,
        "settings_form": settings_form,
        "asset_form": asset_form,
        "edited_asset": edited_asset,
        "assets": assets,
        "active_count": assets.filter(active=True).count(),
        "run_rows": run_rows,
    })
