from datetime import timedelta

from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .forms import ProductImportRunForm, ProductLayerForm
from .import_monitoring import (
    build_import_monitor_rows,
    build_import_monitor_summary,
)
from .import_registry import PRODUCT_IMPORTS_BY_KEY
from .models import ProductImportRun, ProductPage


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

    if request.method == "POST":
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

    monitor_row = next(
        row for row in build_import_monitor_rows() if row["key"] == family_key
    )
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
