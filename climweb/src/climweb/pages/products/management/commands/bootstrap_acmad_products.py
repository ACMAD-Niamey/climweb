from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from climweb.pages.products.import_registry import PRODUCT_IMPORTS



class Command(BaseCommand):
    help = "Seed enabled ACMAD product families using their idempotent importers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Run even when ACMAD_INITIAL_IMPORT_ON_STARTUP or an individual "
                "product's automatic-import setting is disabled."
            ),
        )
        parser.add_argument(
            "--product",
            action="append",
            choices=[definition["key"] for definition in PRODUCT_IMPORTS],
            help="Seed only this product key. This option may be repeated.",
        )

    def handle(self, *args, **options):
        if not settings.ACMAD_INITIAL_IMPORT_ON_STARTUP and not options["force"]:
            self.stdout.write(
                "ACMAD initial product import is disabled; set "
                "ACMAD_INITIAL_IMPORT_ON_STARTUP=True to enable it."
            )
            return

        selected_keys = set(options["product"] or [])
        attempted = 0
        skipped = 0
        failures = []
        for definition in PRODUCT_IMPORTS:
            if selected_keys and definition["key"] not in selected_keys:
                continue
            enabled = getattr(settings, definition["enabled_setting"])
            if not enabled and not options["force"]:
                skipped += 1
                self.stdout.write(
                    f"SKIP {definition['label']}: "
                    f"{definition['enabled_setting']} is disabled"
                )
                continue

            command_options = {"continue_on_error": True}
            limit_setting = definition.get("limit_setting")
            if limit_setting:
                command_options["limit"] = getattr(settings, limit_setting)
            attempted += 1
            self.stdout.write(self.style.MIGRATE_HEADING(definition["label"]))
            try:
                call_command(definition["command"], **command_options)
            except CommandError as exc:
                failures.append((definition["label"], str(exc)))
                self.stderr.write(
                    self.style.ERROR(f"FAILED {definition['label']}: {exc}")
                )

        summary = (
            f"ACMAD initial import complete: attempted={attempted}, "
            f"skipped={skipped}, failed={len(failures)}"
        )
        if failures:
            self.stderr.write(self.style.ERROR(summary))
            raise CommandError(
                "Initial import failed for: "
                + ", ".join(label for label, _ in failures)
            )
        self.stdout.write(self.style.SUCCESS(summary))
