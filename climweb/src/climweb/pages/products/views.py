import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.utils import timezone
from wagtail.admin.auth import user_passes_test

from .forms import (
    ConfiguredProductImporterForm,
    ProductImportRunForm,
    ProductImportScheduleForm,
    ProductImportSourceConfigForm,
    ProductLayerForm,
    ProductSubscriptionForm,
    ProductSubscriptionPreferencesForm,
)
from .import_monitoring import (
    build_import_monitor_rows,
    build_import_monitor_summary,
)
from .import_registry import get_product_import_definition
from .models import (
    ConfiguredProductImporter,
    ConfiguredProductImporterAuditEvent,
    ProductImportRun,
    ProductImportSchedule,
    ProductImportSourceConfig,
    ProductNotificationDelivery,
    ProductNotificationEvent,
    ProductPage,
    ProductSubscriptionPreference,
    ProductSubscriber,
)


def product_subscription_view(request):
    form = ProductSubscriptionForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        subscriber, _ = ProductSubscriber.objects.update_or_create(
            email=email,
            defaults={
                "name": form.cleaned_data["name"].strip(),
                "sector": form.cleaned_data["sector"],
                "organization_type": form.cleaned_data["organization_type"],
                "status": ProductSubscriber.STATUS_PENDING,
                "confirmation_token": uuid.uuid4(),
                "consented_at": timezone.now(),
                "confirmed_at": None,
                "unsubscribed_at": None,
                "consent_ip": request.META.get("REMOTE_ADDR") or None,
                "consent_user_agent": request.META.get(
                    "HTTP_USER_AGENT", ""
                )[:500],
            },
        )
        subscriber.preferences.all().delete()
        ProductSubscriptionPreference.objects.bulk_create(
            [
                ProductSubscriptionPreference(
                    subscriber=subscriber, product_family=family
                )
                for family in form.cleaned_data["product_families"]
            ]
        )
        from .tasks import send_product_subscription_confirmation

        send_product_subscription_confirmation.delay(subscriber.pk)
        return render(
            request,
            "products/subscription_status.html",
            {
                "status_title": "Check your email",
                "status_message": (
                    "We sent you a confirmation link. Your subscription will "
                    "remain inactive until you confirm it."
                ),
            },
        )
    return render(request, "products/subscription_form.html", {"form": form})


def product_subscription_confirm_view(request, token):
    subscriber = get_object_or_404(ProductSubscriber, confirmation_token=token)
    subscriber.status = ProductSubscriber.STATUS_ACTIVE
    subscriber.confirmed_at = timezone.now()
    subscriber.unsubscribed_at = None
    subscriber.save(
        update_fields=[
            "status",
            "confirmed_at",
            "unsubscribed_at",
            "updated_at",
        ]
    )
    return render(
        request,
        "products/subscription_status.html",
        {
            "status_title": "Subscription confirmed",
            "status_message": (
                "You will now receive notifications for your selected ACMAD "
                "products."
            ),
        },
    )


def product_subscription_preferences_view(request, token):
    subscriber = get_object_or_404(ProductSubscriber, unsubscribe_token=token)
    initial = {
        "name": subscriber.name,
        "email": subscriber.email,
        "sector": subscriber.sector,
        "organization_type": subscriber.organization_type,
        "product_families": list(
            subscriber.preferences.values_list("product_family", flat=True)
        ),
    }
    form = ProductSubscriptionPreferencesForm(
        request.POST if request.method == "POST" else None,
        initial=initial,
    )
    form.fields["email"].disabled = True
    if request.method == "POST" and form.is_valid():
        subscriber.name = form.cleaned_data["name"].strip()
        subscriber.sector = form.cleaned_data["sector"]
        subscriber.organization_type = form.cleaned_data["organization_type"]
        subscriber.status = ProductSubscriber.STATUS_ACTIVE
        subscriber.unsubscribed_at = None
        subscriber.save(
            update_fields=[
                "name",
                "sector",
                "organization_type",
                "status",
                "unsubscribed_at",
                "updated_at",
            ]
        )
        subscriber.preferences.all().delete()
        ProductSubscriptionPreference.objects.bulk_create(
            [
                ProductSubscriptionPreference(
                    subscriber=subscriber, product_family=family
                )
                for family in form.cleaned_data["product_families"]
            ]
        )
        return render(
            request,
            "products/subscription_status.html",
            {
                "status_title": "Preferences updated",
                "status_message": (
                    "Your ACMAD product notification preferences have been saved."
                ),
            },
        )
    return render(
        request,
        "products/subscription_form.html",
        {"form": form, "managing_preferences": True, "subscriber": subscriber},
    )


def product_subscription_unsubscribe_view(request, token):
    subscriber = get_object_or_404(ProductSubscriber, unsubscribe_token=token)
    if request.method == "POST":
        subscriber.status = ProductSubscriber.STATUS_UNSUBSCRIBED
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save(update_fields=["status", "unsubscribed_at", "updated_at"])
        return render(
            request,
            "products/subscription_status.html",
            {
                "status_title": "Unsubscribed",
                "status_message": (
                    "You will no longer receive ACMAD product notifications."
                ),
            },
        )
    return render(
        request,
        "products/subscription_unsubscribe.html",
        {"subscriber": subscriber},
    )


def _record_importer_audit(importer, action, actor, changes=None):
    return ConfiguredProductImporterAuditEvent.objects.create(
        importer=importer,
        action=action,
        actor=actor,
        changes=changes or {},
    )


def _queue_product_import(request, run, label, *, retry=False):
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
        return False

    run.task_id = task.id
    run.save(update_fields=["task_id"])
    action_label = "retry" if retry else "import"
    messages.success(request, f"{label} {action_label} was queued.")
    return True


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_import_status_view(request, family_key=None):
    runs = ProductImportRun.objects.all()
    if family_key:
        if get_product_import_definition(family_key) is None:
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
def product_subscriber_dashboard_view(request):
    """Track locally stored product subscribers and notification activity."""
    from .import_registry import get_product_import_definitions

    definitions = [
        definition
        for definition in get_product_import_definitions()
        if not definition.get("is_archived")
    ]
    product_choices = [
        (definition["key"], definition["label"])
        for definition in definitions
    ]
    product_labels = dict(product_choices)
    valid_statuses = dict(ProductSubscriber.STATUS_CHOICES)

    search = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    product_filter = request.GET.get("product", "").strip()
    if status_filter not in valid_statuses:
        status_filter = ""
    if product_filter not in product_labels:
        product_filter = ""

    subscribers = ProductSubscriber.objects.prefetch_related("preferences")
    if search:
        subscribers = subscribers.filter(
            Q(email__icontains=search) | Q(name__icontains=search)
        )
    if status_filter:
        subscribers = subscribers.filter(status=status_filter)
    if product_filter:
        subscribers = subscribers.filter(
            preferences__product_family=product_filter
        )

    subscribers = subscribers.annotate(
        sent_delivery_count=Count(
            "deliveries",
            filter=Q(
                deliveries__status=ProductNotificationDelivery.STATUS_SENT
            ),
            distinct=True,
        ),
        last_notified_at=Max("deliveries__sent_at"),
    ).order_by("-created_at", "email")

    page = Paginator(subscribers, 50).get_page(request.GET.get("page"))
    for subscriber in page.object_list:
        subscriber.selected_product_labels = [
            product_labels.get(
                preference.product_family, preference.product_family
            )
            for preference in subscriber.preferences.all()
        ]

    status_counts = {
        row["status"]: row["count"]
        for row in ProductSubscriber.objects.values("status").annotate(
            count=Count("pk")
        )
    }
    recent_events = list(
        ProductNotificationEvent.objects.select_related("source_import")[:10]
    )
    for event in recent_events:
        event.product_label = product_labels.get(
            event.product_family, event.product_family
        )

    return TemplateResponse(
        request,
        "products/subscriber_dashboard.html",
        {
            "subscriber_page": page,
            "total_subscribers": ProductSubscriber.objects.count(),
            "status_counts": status_counts,
            "status_choices": ProductSubscriber.STATUS_CHOICES,
            "product_choices": product_choices,
            "search": search,
            "status_filter": status_filter,
            "product_filter": product_filter,
            "recent_events": recent_events,
        },
    )


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def configured_product_importer_create_view(request):
    action = request.POST.get("action", "")
    form = ConfiguredProductImporterForm(
        request.POST if request.method == "POST" else None
    )
    source_preview = None
    if request.method == "POST" and form.is_valid():
        from .import_sources import inspect_product_import_source

        try:
            source_preview = inspect_product_import_source(
                form.cleaned_data["key"],
                form.source_values,
                include_history=False,
            )
        except Exception as exc:
            messages.error(request, f"Source check failed: {exc}")
        else:
            if action == "test_source":
                messages.success(
                    request,
                    "Connection successful. "
                    f"Discovered {source_preview['discovered_count']} matching file(s).",
                )
                source_preview = None
            elif action == "preview_source":
                messages.success(
                    request,
                    f"Preview found {source_preview['discovered_count']} matching file(s).",
                )
            elif action == "create_importer":
                if source_preview["discovered_count"] == 0:
                    form.add_error(
                        "filename_pattern",
                        "No matching dated files were found. Preview the source and adjust the schema.",
                    )
                else:
                    with transaction.atomic():
                        importer = form.save(commit=False)
                        importer.default_source_config = form.source_values
                        importer.created_by = request.user
                        importer.save()
                        _record_importer_audit(
                            importer,
                            ConfiguredProductImporterAuditEvent.ACTION_CREATED,
                            request.user,
                            {
                                "status": importer.status,
                                "destination_product_page": importer.product_page.title,
                                "destination_product_type": str(
                                    importer.product_item_type
                                ),
                                "source_url": form.source_values["source_url"],
                            },
                        )
                        ProductImportSourceConfig.objects.create(
                            product_family=importer.key,
                            updated_by=request.user,
                            **form.source_values,
                        )
                        ProductImportSchedule.objects.create(
                            product_family=importer.key,
                            interval_hours=importer.default_interval_hours,
                            enabled_override=(
                                importer.status
                                == ConfiguredProductImporter.STATUS_ACTIVE
                            ),
                            updated_by=request.user,
                        )
                    if importer.status == ConfiguredProductImporter.STATUS_ACTIVE:
                        from .import_scheduling import sync_product_import_schedule

                        try:
                            sync_product_import_schedule(
                                importer.key,
                                importer.default_interval_hours,
                                enabled=True,
                            )
                        except Exception as exc:
                            messages.warning(
                                request,
                                "The importer was created, but the live scheduler "
                                f"could not be updated: {exc}",
                            )
                    messages.success(
                        request,
                        f"{importer.label} importer was created.",
                    )
                    return redirect(
                        "product_import_family", family_key=importer.key
                    )
    return TemplateResponse(
        request,
        "products/importer_create.html",
        {"form": form, "source_preview": source_preview},
    )


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def configured_product_importer_edit_view(request, family_key):
    importer = get_object_or_404(
        ConfiguredProductImporter.objects.select_related(
            "product_page__product", "product_item_type__category"
        ),
        key=family_key,
    )
    if importer.status == ConfiguredProductImporter.STATUS_ARCHIVED:
        messages.warning(request, "Restore this importer before editing it.")
        return redirect("product_import_family", family_key=family_key)

    source_config = ProductImportSourceConfig.objects.filter(
        product_family=family_key
    ).first()
    source_values = (
        {
            field: getattr(source_config, field)
            for field in (
                "source_type",
                "source_url",
                "source_system",
                "allowed_extensions",
                "filename_pattern",
                "date_format",
                "history_url_pattern",
                "request_headers",
            )
        }
        if source_config
        else importer.default_source_config
    )
    action = request.POST.get("action", "")
    form = ConfiguredProductImporterForm(
        request.POST if request.method == "POST" else None,
        instance=importer,
        source_config=source_values,
    )
    source_preview = None
    if request.method == "POST" and form.is_valid():
        from .import_sources import inspect_product_import_source

        try:
            source_preview = inspect_product_import_source(
                importer.key,
                form.source_values,
                include_history=False,
            )
        except Exception as exc:
            messages.error(request, f"Source check failed: {exc}")
        else:
            if action == "test_source":
                messages.success(
                    request,
                    "Connection successful. "
                    f"Discovered {source_preview['discovered_count']} matching file(s).",
                )
                source_preview = None
            elif action == "preview_source":
                messages.success(
                    request,
                    f"Preview found {source_preview['discovered_count']} matching file(s).",
                )
            elif action == "save_importer":
                if source_preview["discovered_count"] == 0:
                    form.add_error(
                        "filename_pattern",
                        "No matching dated files were found. Adjust the source schema before saving.",
                    )
                else:
                    original = ConfiguredProductImporter.objects.get(pk=importer.pk)
                    old_values = {
                        "label": original.label,
                        "product_page": original.product_page_id,
                        "product_item_type": original.product_item_type_id,
                        "status": original.status,
                        "default_interval_hours": original.default_interval_hours,
                        "source": source_values,
                    }
                    with transaction.atomic():
                        importer = form.save(commit=False)
                        importer.default_source_config = form.source_values
                        importer.save()
                        ProductImportSourceConfig.objects.update_or_create(
                            product_family=importer.key,
                            defaults={
                                **form.source_values,
                                "updated_by": request.user,
                            },
                        )
                        schedule, _ = ProductImportSchedule.objects.update_or_create(
                            product_family=importer.key,
                            defaults={
                                "interval_hours": importer.default_interval_hours,
                                "enabled_override": (
                                    importer.status
                                    == ConfiguredProductImporter.STATUS_ACTIVE
                                ),
                                "updated_by": request.user,
                            },
                        )
                        new_values = {
                            "label": importer.label,
                            "product_page": importer.product_page_id,
                            "product_item_type": importer.product_item_type_id,
                            "status": importer.status,
                            "default_interval_hours": importer.default_interval_hours,
                            "source": form.source_values,
                        }
                        changes = {
                            key: {"from": old_values[key], "to": value}
                            for key, value in new_values.items()
                            if old_values[key] != value
                        }
                        _record_importer_audit(
                            importer,
                            ConfiguredProductImporterAuditEvent.ACTION_UPDATED,
                            request.user,
                            changes,
                        )
                    from .import_scheduling import sync_product_import_schedule

                    try:
                        sync_product_import_schedule(
                            importer.key,
                            schedule.interval_hours,
                            enabled=(
                                importer.status
                                == ConfiguredProductImporter.STATUS_ACTIVE
                            ),
                        )
                    except Exception as exc:
                        messages.warning(
                            request,
                            "Changes were saved, but the live scheduler could not "
                            f"be updated: {exc}",
                        )
                    messages.success(request, f"{importer.label} was updated.")
                    return redirect(
                        "product_import_family", family_key=importer.key
                    )

    return TemplateResponse(
        request,
        "products/importer_create.html",
        {
            "form": form,
            "importer": importer,
            "source_preview": source_preview,
        },
    )


@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_import_family_view(request, family_key):
    definition = get_product_import_definition(family_key)
    if definition is None:
        raise Http404("Unknown product importer")

    action = request.POST.get("action", "manual_import")
    configured_importer = (
        ConfiguredProductImporter.objects.filter(key=family_key).first()
        if definition.get("is_configured")
        else None
    )
    if (
        request.method == "POST"
        and configured_importer
        and configured_importer.status
        == ConfiguredProductImporter.STATUS_ARCHIVED
        and action != "restore_importer"
    ):
        messages.warning(request, "Restore this importer before making changes.")
        return redirect("product_import_family", family_key=family_key)
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
    if request.method == "POST" and action == "archive_importer":
        if configured_importer is None:
            raise Http404("Only dashboard-created importers can be archived")
        active_runs = ProductImportRun.objects.filter(
            product_family=family_key,
            status__in={
                ProductImportRun.STATUS_QUEUED,
                ProductImportRun.STATUS_RUNNING,
                ProductImportRun.STATUS_CANCELLING,
            },
        )
        if active_runs.exists():
            messages.error(
                request,
                "Stop or wait for active manual imports before archiving this importer.",
            )
            return redirect("product_import_family", family_key=family_key)
        configured_importer.status = ConfiguredProductImporter.STATUS_ARCHIVED
        configured_importer.save(update_fields=["status", "updated_at"])
        schedule, _ = ProductImportSchedule.objects.get_or_create(
            product_family=family_key,
            defaults={
                "interval_hours": configured_importer.default_interval_hours,
            },
        )
        schedule.enabled_override = False
        schedule.updated_by = request.user
        schedule.save(
            update_fields=["enabled_override", "updated_by", "updated_at"]
        )
        from .import_scheduling import sync_product_import_schedule

        try:
            sync_product_import_schedule(
                family_key, schedule.interval_hours, enabled=False
            )
        except Exception as exc:
            messages.warning(
                request,
                "The importer was archived, but the live scheduler could not "
                f"be disabled: {exc}",
            )
        _record_importer_audit(
            configured_importer,
            ConfiguredProductImporterAuditEvent.ACTION_ARCHIVED,
            request.user,
            {"preserved_import_runs": ProductImportRun.objects.filter(
                product_family=family_key
            ).count()},
        )
        messages.success(
            request,
            f"{configured_importer.label} was archived. Its history was preserved.",
        )
        return redirect("product_import_family", family_key=family_key)
    elif request.method == "POST" and action == "restore_importer":
        if configured_importer is None:
            raise Http404("Only dashboard-created importers can be restored")
        configured_importer.status = ConfiguredProductImporter.STATUS_DRAFT
        configured_importer.save(update_fields=["status", "updated_at"])
        ProductImportSchedule.objects.update_or_create(
            product_family=family_key,
            defaults={
                "interval_hours": configured_importer.default_interval_hours,
                "enabled_override": False,
                "updated_by": request.user,
            },
        )
        _record_importer_audit(
            configured_importer,
            ConfiguredProductImporterAuditEvent.ACTION_RESTORED,
            request.user,
            {"status": ConfiguredProductImporter.STATUS_DRAFT},
        )
        messages.success(
            request,
            f"{configured_importer.label} was restored as a draft.",
        )
        return redirect("product_import_family", family_key=family_key)
    elif request.method == "POST" and action == "restore_source_defaults":
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
        default_interval = (
            definition.get("default_interval_hours", 24)
            if definition.get("is_configured")
            else getattr(settings, definition["interval_setting"], 24)
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
        if configured_importer:
            configured_importer.status = (
                ConfiguredProductImporter.STATUS_ACTIVE
                if enabled
                else ConfiguredProductImporter.STATUS_DRAFT
            )
            configured_importer.save(update_fields=["status", "updated_at"])
            _record_importer_audit(
                configured_importer,
                (
                    ConfiguredProductImporterAuditEvent.ACTION_ENABLED
                    if enabled
                    else ConfiguredProductImporterAuditEvent.ACTION_DISABLED
                ),
                request.user,
                {"enabled": enabled},
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
    elif request.method == "POST" and action == "retry_import":
        failed_run = get_object_or_404(
            ProductImportRun,
            pk=request.POST.get("run_id"),
            product_family=family_key,
        )
        if failed_run.status != ProductImportRun.STATUS_FAILED:
            messages.info(request, "Only failed imports can be retried.")
            return redirect("product_import_family", family_key=family_key)

        retry_run = ProductImportRun.objects.create(
            product_family=failed_run.product_family,
            mode=failed_run.mode,
            from_date=failed_run.from_date,
            to_date=failed_run.to_date,
            limit=failed_run.limit,
            refresh_existing=failed_run.refresh_existing,
            retry_failures=True,
            requested_by=request.user,
            current_phase=f"Retry of import #{failed_run.pk} waiting to start",
        )
        _queue_product_import(
            request,
            retry_run,
            definition["label"],
            retry=True,
        )
        return redirect("product_import_family", family_key=family_key)
    elif request.method == "POST" and action == "send_latest_notification":
        from .product_notifications import queue_latest_product_notification

        event = queue_latest_product_notification(family_key, request.user)
        if event is None:
            messages.warning(
                request,
                "There is no successfully imported file to notify subscribers about.",
            )
        else:
            messages.success(
                request,
                f"Notification for the latest {definition['label']} product was queued.",
            )
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
                if configured_importer:
                    _record_importer_audit(
                        configured_importer,
                        ConfiguredProductImporterAuditEvent.ACTION_SOURCE_UPDATED,
                        request.user,
                        {"source_url": source_config.source_url},
                    )
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
            if configured_importer:
                _record_importer_audit(
                    configured_importer,
                    ConfiguredProductImporterAuditEvent.ACTION_SCHEDULE_UPDATED,
                    request.user,
                    {"interval_hours": interval_hours},
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
            _queue_product_import(request, run, definition["label"])
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
    recent_notification_events = ProductNotificationEvent.objects.filter(
        product_family=family_key
    ).select_related("source_import", "requested_by")[:10]
    active_subscriber_count = ProductSubscriber.objects.filter(
        status=ProductSubscriber.STATUS_ACTIVE,
        preferences__product_family=family_key,
    ).distinct().count()
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
            "recent_notification_events": recent_notification_events,
            "active_subscriber_count": active_subscriber_count,
            "configured_importer": configured_importer,
            "audit_events": (
                configured_importer.audit_events.select_related("actor")[:20]
                if configured_importer
                else []
            ),
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
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from wagtail.admin.auth import user_passes_test
from .models import ProductSubscriber
from .product_notifications import send_confirmation_email

@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_subscriber_resend_verification_view(request, subscriber_id):
    subscriber = get_object_or_404(ProductSubscriber, pk=subscriber_id)
    if subscriber.status == ProductSubscriber.STATUS_PENDING:
        try:
            send_confirmation_email(subscriber)
            messages.success(request, f"Verification email sent to {subscriber.email}.")
        except Exception as e:
            messages.error(request, f"Failed to send email to {subscriber.email}: {e}")
    else:
        messages.warning(request, f"Subscriber {subscriber.email} is not pending verification.")
    
    return redirect("product_subscriber_dashboard")

@user_passes_test(lambda u: u.is_superuser or u.has_perm('wagtailadmin.access_admin'))
def product_subscriber_delete_view(request, subscriber_id):
    subscriber = get_object_or_404(ProductSubscriber, pk=subscriber_id)
    if request.method == "POST":
        email = subscriber.email
        subscriber.delete()
        messages.success(request, f"Subscriber {email} deleted successfully.")
    else:
        messages.error(request, "Invalid request method for deletion. Use POST.")
    return redirect("product_subscriber_dashboard")
