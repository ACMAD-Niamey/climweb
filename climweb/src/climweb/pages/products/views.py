from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .forms import (
    ProductImportRunForm,
    ProductImportScheduleForm,
    ProductImportSourceConfigForm,
    ProductLayerForm,
)
from .import_monitoring import (
    build_import_monitor_rows,
    build_import_monitor_summary,
)
from .import_registry import PRODUCT_IMPORTS_BY_KEY
from .models import (
    ProductImportRun,
    ProductImportSchedule,
    ProductImportSourceConfig,
    ProductPage,
)


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_import_status_view(request, family_key=None):
    runs = ProductImportRun.objects.all()
    if family_key:
        if family_key not in PRODUCT_IMPORTS_BY_KEY:
            raise Http404("Unknown product importer")
        runs = runs.filter(product_family=family_key)
    runs = runs[:20]
    return JsonResponse(
        {
            "runs": [
                {
                    "id": run.pk,
                    "status": run.status,
                    "status_label": run.get_status_display(),
                    "progress_percent": run.progress_percent,
                    "total_items": run.total_items,
                    "processed_items": run.processed_items,
                    "imported_items": run.imported_items,
                    "failed_items": run.failed_items,
                    "skipped_items": run.skipped_items,
                    "current_phase": run.current_phase,
                    "error_message": run.error_message,
                }
                for run in runs
            ]
        }
    )


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_import_monitor_view(request):
    rows = build_import_monitor_rows()
    return TemplateResponse(
        request,
        "products/import_monitor.html",
        {
            "rows": rows,
            "summary": build_import_monitor_summary(rows),
        },
    )


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_import_family_view(request, family_key):
    definition = PRODUCT_IMPORTS_BY_KEY.get(family_key)
    if definition is None:
        raise Http404("Unknown product importer")

    action = request.POST.get("action", "manual_import")
    source_config = None
    source_form = None
    source_preview = None
    if definition.get("configurable_source"):
        source_config = ProductImportSourceConfig.objects.filter(
            product_family=family_key
        ).select_related("updated_by").first()
        source_form = ProductImportSourceConfigForm(
            (
                request.POST
                if request.method == "POST"
                and action in {"save_source", "test_source", "preview_source"}
                else None
            ),
            instance=source_config,
            initial=(
                definition.get("source_defaults", {})
                if source_config is None
                else {}
            ),
        )

    source_actions = {"save_source", "test_source", "preview_source"}
    if request.method == "POST" and action == "restore_source_defaults":
        if source_form is None:
            raise Http404("Source configuration is not available for this importer")
        ProductImportSourceConfig.objects.filter(product_family=family_key).delete()
        messages.success(
            request,
            f"{definition['label']} source configuration was restored to defaults.",
        )
        return redirect("product_import_family", family_key=family_key)
    elif request.method == "POST" and action in {
        "enable_importer",
        "disable_importer",
    }:
        enabled = action == "enable_importer"
        default_interval = getattr(
            settings, definition["interval_setting"], 24
        )
        schedule, _ = ProductImportSchedule.objects.get_or_create(
            product_family=family_key,
            defaults={"interval_hours": default_interval},
        )
        schedule.enabled_override = enabled
        schedule.updated_by = request.user
        schedule.save(
            update_fields=["enabled_override", "updated_by", "updated_at"]
        )
        from .import_scheduling import sync_product_import_schedule

        try:
            sync_product_import_schedule(
                family_key,
                schedule.interval_hours,
                enabled=enabled,
            )
        except Exception as exc:
            messages.warning(
                request,
                "The importer status was saved, but the live scheduler could "
                f"not be updated: {exc}",
            )
        else:
            status_label = "enabled" if enabled else "disabled"
            messages.success(
                request,
                f"{definition['label']} automatic importer was {status_label}.",
            )
        return redirect("product_import_family", family_key=family_key)
    elif request.method == "POST" and action == "cancel_import":
        with transaction.atomic():
            run = get_object_or_404(
                ProductImportRun.objects.select_for_update(),
                pk=request.POST.get("run_id"),
                product_family=family_key,
            )
            if run.status not in {
                ProductImportRun.STATUS_QUEUED,
                ProductImportRun.STATUS_RUNNING,
                ProductImportRun.STATUS_CANCELLING,
            }:
                messages.info(request, "This manual import has already finished.")
                return redirect("product_import_family", family_key=family_key)

            was_queued = run.status == ProductImportRun.STATUS_QUEUED
            run.cancel_requested = True
            run.status = (
                ProductImportRun.STATUS_CANCELLED
                if was_queued
                else ProductImportRun.STATUS_CANCELLING
            )
            run.current_phase = (
                "Stopped before starting" if was_queued else "Stop requested"
            )
            if was_queued:
                run.finished_at = timezone.now()
            run.save(
                update_fields=[
                    "cancel_requested",
                    "status",
                    "current_phase",
                    "finished_at",
                ]
            )
        if run.task_id:
            from climweb.config.celery import app

            try:
                app.control.revoke(run.task_id, terminate=False)
            except Exception as exc:
                messages.warning(
                    request,
                    "The stop request was saved, but the Celery revoke signal "
                    f"could not be sent: {exc}",
                )
            else:
                messages.success(request, "The manual import is being stopped.")
        else:
            messages.success(request, "The manual import is being stopped.")
        return redirect("product_import_family", family_key=family_key)
    elif request.method == "POST" and action in source_actions:
        if source_form is None:
            raise Http404("Source configuration is not available for this importer")
        if source_form.is_valid():
            if action == "save_source":
                source_config = source_form.save(commit=False)
                source_config.product_family = family_key
                source_config.updated_by = request.user
                source_config.save()
                messages.success(
                    request,
                    f"{definition['label']} source configuration was saved.",
                )
                return redirect("product_import_family", family_key=family_key)

            from .import_sources import inspect_product_import_source

            try:
                source_preview = inspect_product_import_source(
                    family_key,
                    source_form.cleaned_data,
                    include_history=False,
                )
            except Exception as exc:
                messages.error(request, f"Source check failed: {exc}")
            else:
                if action == "test_source":
                    messages.success(
                        request,
                        "Connection successful. "
                        f"Discovered {source_preview['discovered_count']} "
                        "matching file(s) on the current archive page.",
                    )
                    source_preview = None
                else:
                    messages.success(
                        request,
                        f"Preview found {source_preview['discovered_count']} "
                        "matching file(s).",
                    )
        today = timezone.localdate()
        form = ProductImportRunForm(
            initial={
                "mode": ProductImportRun.MODE_PREVIEW,
                "from_date": today - timedelta(days=30),
                "to_date": today,
                "limit": 100,
            }
        )
        schedule_form = None
    elif request.method == "POST" and action == "update_schedule":
        schedule_form = ProductImportScheduleForm(request.POST)
        if schedule_form.is_valid():
            interval_hours = schedule_form.cleaned_data["interval_hours"]
            ProductImportSchedule.objects.update_or_create(
                product_family=family_key,
                defaults={
                    "interval_hours": interval_hours,
                    "updated_by": request.user,
                },
            )
            from .import_scheduling import sync_product_import_schedule

            try:
                sync_product_import_schedule(family_key, interval_hours)
            except Exception as exc:
                messages.warning(
                    request,
                    "The interval was saved, but the live scheduler could not "
                    f"be updated: {exc}",
                )
            else:
                messages.success(
                    request,
                    f"{definition['label']} will now be checked every "
                    f"{interval_hours} hour(s).",
                )
            return redirect("product_import_family", family_key=family_key)
        today = timezone.localdate()
        form = ProductImportRunForm(
            initial={
                "mode": ProductImportRun.MODE_PREVIEW,
                "from_date": today - timedelta(days=30),
                "to_date": today,
                "limit": 100,
            }
        )
    elif request.method == "POST":
        form = ProductImportRunForm(request.POST)
        if form.is_valid():
            run = ProductImportRun.objects.create(
                product_family=family_key,
                mode=form.cleaned_data["mode"],
                from_date=form.cleaned_data["from_date"],
                to_date=form.cleaned_data["to_date"],
                limit=form.cleaned_data["limit"],
                refresh_existing=form.cleaned_data["refresh_existing"],
                retry_failures=form.cleaned_data["retry_failures"],
                requested_by=request.user,
            )
            from .tasks import run_manual_product_import

            try:
                task = run_manual_product_import.delay(run.pk)
            except Exception as exc:
                run.status = ProductImportRun.STATUS_FAILED
                run.error_message = f"Could not queue import: {exc}"
                run.finished_at = timezone.now()
                run.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "finished_at",
                    ]
                )
                messages.error(request, run.error_message)
            else:
                run.task_id = task.id
                run.save(update_fields=["task_id"])
                messages.success(
                    request,
                    f"{definition['label']} import was queued.",
                )
            return redirect("product_import_family", family_key=family_key)
        schedule_form = None
    else:
        today = timezone.localdate()
        form = ProductImportRunForm(
            initial={
                "mode": ProductImportRun.MODE_PREVIEW,
                "from_date": today - timedelta(days=30),
                "to_date": today,
                "limit": 100,
            }
        )
        schedule_form = None

    monitor_row = next(
        row for row in build_import_monitor_rows() if row["key"] == family_key
    )
    if schedule_form is None:
        schedule_form = ProductImportScheduleForm(
            initial={"interval_hours": monitor_row["interval_hours"]}
        )
    schedule = ProductImportSchedule.objects.filter(
        product_family=family_key
    ).select_related("updated_by").first()
    recent_runs = ProductImportRun.objects.filter(
        product_family=family_key
    ).select_related("requested_by")[:20]
    return TemplateResponse(
        request,
        "products/import_family.html",
        {
            "definition": definition,
            "monitor_row": monitor_row,
            "form": form,
            "schedule_form": schedule_form,
            "schedule": schedule,
            "source_config": source_config,
            "source_form": source_form,
            "source_preview": source_preview,
            "recent_runs": recent_runs,
        },
    )


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def trigger_product_ingestion_view(request, product_page_id):
    product_page = get_object_or_404(ProductPage, pk=product_page_id)
    product = product_page.product

    if not product.ingestion_enabled:
        messages.warning(request, f"Auto-ingestion is not enabled for {product.name}.")
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    try:
        from climweb.pages.products.tasks import _ingest_product
        _ingest_product(product)
        messages.success(request, f"Ingestion completed for {product.name}.")
    except Exception as exc:
        messages.error(request, f"Ingestion failed for {product.name}: {exc}")

    return redirect(request.META.get('HTTP_REFERER', '/admin/'))


def product_layers_integration_view(request, product_page_id):
    template_name = "products/product_layer_integration.html"
    product_page = ProductPage.objects.get(pk=product_page_id)

    form = ProductLayerForm(instance=product_page)

    context = {
        "form_media": form.media,
        "product_page_url": product_page.url
    }

    if request.POST:
        form = ProductLayerForm(request.POST, instance=product_page)

        # save data
        if form.is_valid():
            form.save()

    context.update({
        "form": form,
    })

    return render(request, template_name, context=context)
