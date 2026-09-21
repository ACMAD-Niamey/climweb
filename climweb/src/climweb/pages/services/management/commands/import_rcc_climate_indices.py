from django.core.management.base import BaseCommand, CommandError

from climweb.pages.services.climate_index_importer import INDEX_TITLES, sync_chart


class Command(BaseCommand):
    help = "Preserve the legacy RCC climate-index charts in local RCC storage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--index",
            action="append",
            type=int,
            dest="indices",
            help="Import one chart number; repeat to import several. Defaults to all charts.",
        )

    def handle(self, *args, **options):
        indices = options["indices"] or range(1, len(INDEX_TITLES) + 1)
        failures = []
        for index in indices:
            try:
                asset = sync_chart(index)
                self.stdout.write(self.style.SUCCESS(f"Imported {asset.legacy_index}: {asset.title}"))
            except Exception as exc:
                failures.append((index, str(exc)))
                self.stderr.write(self.style.ERROR(f"Failed {index}: {exc}"))
        if failures:
            raise CommandError(f"{len(failures)} climate-index chart(s) failed to import.")
