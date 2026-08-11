import re
from contextlib import contextmanager
from contextvars import ContextVar
from io import StringIO

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from climweb.pages.products.models import ProductImportRun, ProductSourceImport


_active_run_id = ContextVar("active_product_import_run_id", default=None)
_ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
_selected_count = re.compile(r"\bSelected\s+(\d+)\b", re.IGNORECASE)
_preview_action = re.compile(r"^(CREATE|REFRESH|SKIP)\s+", re.IGNORECASE)


class ImportCancelled(Exception):
    """Raised at a safe progress checkpoint after a user requests a stop."""


def raise_if_cancelled(run_id):
    if ProductImportRun.objects.filter(
        pk=run_id,
        cancel_requested=True,
    ).exists():
        raise ImportCancelled("Manual import stopped by user")


@contextmanager
def activate_import_run(run_id):
    token = _active_run_id.set(run_id)
    try:
        yield
    finally:
        _active_run_id.reset(token)


def update_run_total(run_id, total):
    ProductImportRun.objects.filter(
        pk=run_id,
        status=ProductImportRun.STATUS_RUNNING,
    ).update(
        total_items=total,
        progress_percent=10,
        current_phase=f"Processing {total} selected item(s)",
    )


def record_run_item(run_id, outcome):
    with transaction.atomic():
        run = (
            ProductImportRun.objects.select_for_update()
            .filter(pk=run_id, status=ProductImportRun.STATUS_RUNNING)
            .first()
        )
        if run is None:
            return

        run.processed_items += 1
        if outcome == "imported":
            run.imported_items += 1
        elif outcome == "failed":
            run.failed_items += 1
        elif outcome == "skipped":
            run.skipped_items += 1

        if run.total_items:
            ratio = min(run.processed_items / run.total_items, 1)
            run.progress_percent = min(95, 10 + round(ratio * 85))
            run.current_phase = (
                f"Processed {run.processed_items} of {run.total_items} item(s)"
            )
        else:
            run.progress_percent = min(95, 10 + run.processed_items)
            run.current_phase = f"Processed {run.processed_items} item(s)"
        run.save(
            update_fields=[
                "processed_items",
                "imported_items",
                "failed_items",
                "skipped_items",
                "progress_percent",
                "current_phase",
            ]
        )


class ImportProgressOutput(StringIO):
    """Capture command output while deriving preview and selection progress."""

    def __init__(self, run_id, preview=False):
        super().__init__()
        self.run_id = run_id
        self.preview = preview

    def write(self, value):
        raise_if_cancelled(self.run_id)
        written = super().write(value)
        for raw_line in value.splitlines():
            line = _ansi_escape.sub("", raw_line).strip()
            selected = _selected_count.search(line)
            if selected:
                update_run_total(self.run_id, int(selected.group(1)))
            if self.preview and _preview_action.match(line):
                action = line.split(maxsplit=1)[0].upper()
                outcome = "skipped" if action == "SKIP" else "imported"
                record_run_item(self.run_id, outcome)
            elif not self.preview and line.upper().startswith("SKIP "):
                record_run_item(self.run_id, "skipped")
        return written


@receiver(
    post_save,
    sender=ProductSourceImport,
    dispatch_uid="track_manual_product_import_progress",
)
def track_manual_product_import_progress(sender, instance, **kwargs):
    run_id = _active_run_id.get()
    if run_id is None:
        return
    outcome = (
        "failed"
        if instance.status == ProductSourceImport.STATUS_FAILED
        or instance.error_message
        else "imported"
    )
    record_run_item(run_id, outcome)
