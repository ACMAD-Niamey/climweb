from django.core.management.base import BaseCommand, CommandError

from climweb.pages.services.climate_index_importer import INDEX_TITLES, legacy_asset, sync_asset, sync_chart
from climweb.pages.services.models import RCCClimateIndexAsset


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
        indices = options["indices"]
        if indices:
            assets = []
        else:
            if not RCCClimateIndexAsset.objects.exists():
                for index in range(1, len(INDEX_TITLES) + 1):
                    legacy_asset(index)
            assets = RCCClimateIndexAsset.objects.filter(active=True).order_by("legacy_index")
        failures = []
        for item in indices or assets:
            try:
                asset = sync_chart(item) if indices else sync_asset(item)
                self.stdout.write(self.style.SUCCESS(f"Imported {asset.legacy_index}: {asset.title}"))
            except Exception as exc:
                label = item if indices else item.legacy_index
                failures.append((label, str(exc)))
                self.stderr.write(self.style.ERROR(f"Failed {label}: {exc}"))
        if failures:
            raise CommandError(f"{len(failures)} climate-index chart(s) failed to import.")
