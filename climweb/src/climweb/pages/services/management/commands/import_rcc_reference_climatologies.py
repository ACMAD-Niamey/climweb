from django.core.management.base import BaseCommand, CommandError

from climweb.pages.services.reference_climatology_importer import (
    PERIODS,
    ReferenceClimatologyClient,
    sync_climatology,
)


class Command(BaseCommand):
    help = "Import country and station reference climatologies from the legacy African RCC service."

    def add_arguments(self, parser):
        parser.add_argument("--country", action="append", dest="countries")
        parser.add_argument("--station", action="append", dest="stations")
        parser.add_argument("--period", action="append", choices=tuple(PERIODS))
        parser.add_argument("--limit-stations", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--continue-on-error", action="store_true")

    def handle(self, *args, **options):
        client = ReferenceClimatologyClient()
        countries = client.countries()
        requested_countries = {value.upper() for value in options["countries"] or []}
        if requested_countries:
            countries = [item for item in countries if item["code"].upper() in requested_countries]
            missing = requested_countries - {item["code"].upper() for item in countries}
            if missing:
                raise CommandError(f"Unknown country code(s): {', '.join(sorted(missing))}")

        requested_stations = {value.upper() for value in options["stations"] or []}
        periods = options["period"] or list(PERIODS)
        selected = []
        for country in countries:
            stations = client.stations(country["code"])
            if requested_stations:
                stations = [
                    item for item in stations
                    if item["code"].upper() in requested_stations
                    or item["name"].upper() in requested_stations
                ]
            for station in stations:
                selected.append((country, station))
                if options["limit_stations"] and len(selected) >= options["limit_stations"]:
                    break
            if options["limit_stations"] and len(selected) >= options["limit_stations"]:
                break

        if not selected:
            raise CommandError("No reference-climatology stations matched the selection.")
        self.stdout.write(
            f"Selected {len(selected)} station(s) and {len(periods)} reference period(s)."
        )
        if options["dry_run"]:
            for country, station in selected:
                self.stdout.write(f"{country['code']} {station['code']} {station['name']}")
            return

        counts = {"created": 0, "updated": 0, "failed": 0}
        for country, station in selected:
            for period in periods:
                try:
                    asset, created = sync_climatology(client, country, station, period)
                    outcome = "created" if created else "updated"
                    counts[outcome] += 1
                    self.stdout.write(
                        f"{outcome.upper()} {asset.country_code}/{asset.station_id} {asset.period_label}"
                    )
                except Exception as exc:
                    counts["failed"] += 1
                    self.stderr.write(
                        f"FAILED {country['code']}/{station['code']} {period}: {exc}"
                    )
                    if not options["continue_on_error"]:
                        raise CommandError(str(exc)) from exc
        self.stdout.write(
            "Reference climatology import complete: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
        )
        if counts["failed"]:
            raise CommandError(f"{counts['failed']} reference climatology import(s) failed")
