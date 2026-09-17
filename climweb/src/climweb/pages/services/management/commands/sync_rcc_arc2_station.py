import csv
import hashlib
import os
import re
import tempfile
from datetime import date
from pathlib import Path

import requests
from django.core.files import File
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from climweb.pages.services.models import RCCDatasetAsset
from climweb.pages.services.arc2_importer import (
    COUNTRY_PATTERN,
    catalogue_url_for,
    station_source_url,
    validate_station_source_url,
)


EXPECTED_FIELDS = ["Station", "Country", "Lon", "Lat", "Date", "Precipitation"]
STATION_PATTERN = re.compile(r"^[A-Z0-9_-]+$")
DISPLAY_NAMES = {"NIAMEY-AERO": "Niamey-Aéro"}


class Command(BaseCommand):
    help = "Synchronize one ARC2 daily station rainfall CSV into RCC storage."
    default_station = None
    dataset_key = "arc2"
    dataset_label = "ARC2"
    directory = "Synoptic_Daily_ARC2_Data"
    root_catalogue_url = None

    def prepare_source(self, path):
        """Return the file to validate/store, a warning, and any extra temporary path."""
        return path, "", None

    def summary_text(self, display_name, country, quality_note=""):
        kind = "ARC2 satellite" if self.dataset_key == "arc2" else self.dataset_label
        summary = f"Daily {kind} rainfall estimates for the {display_name} synoptic station in {country}."
        return f"{summary} {quality_note}" if quality_note else summary

    def add_arguments(self, parser):
        parser.add_argument("station", nargs="?", default=self.default_station)
        parser.add_argument("--country", default="Niger", help="Dataset country directory.")
        parser.add_argument("--source-url", help="Validated THREDDS fileServer URL for this station.")
        parser.add_argument("--source-file", help="Import a local CSV instead of downloading it.")

    def _station_details(self, station, country, source_url=None):
        station = (station or "").strip().upper()
        if not STATION_PATTERN.fullmatch(station):
            raise CommandError("Supply a valid station filename without .csv.")
        if not COUNTRY_PATTERN.fullmatch(country):
            raise CommandError("Supply a valid country directory.")
        display_name = DISPLAY_NAMES.get(station, station.replace("_", "-").title())
        station_slug = slugify(station)
        if source_url is None:
            root_url = self.root_catalogue_url
            country_url = (
                catalogue_url_for(country, root_url, self.directory)
                if root_url else catalogue_url_for(country)
            )
            source_url = station_source_url(country_url, country, station, self.directory)
        validate_station_source_url(source_url, country, station, self.directory)
        return station, display_name, station_slug, source_url

    def _download(self, source_url, target, country, station):
        validate_station_source_url(source_url, country, station, self.directory)
        with requests.get(source_url, stream=True, timeout=(15, 300)) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if chunk:
                    target.write(chunk)

    def _validate(self, path, station, country):
        digest = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)

        count = 0
        start = end = longitude = latitude = None
        with open(path, encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != EXPECTED_FIELDS:
                raise CommandError("The downloaded CSV has an unexpected header.")
            for row in reader:
                if row["Station"] != station or row["Country"] != country:
                    raise CommandError("The CSV contains data for an unexpected station.")
                try:
                    observed_on = date.fromisoformat(row["Date"])
                    row_longitude = float(row["Lon"])
                    row_latitude = float(row["Lat"])
                    if row["Precipitation"]:
                        float(row["Precipitation"])
                except (TypeError, ValueError) as exc:
                    raise CommandError("The CSV contains an invalid observation.") from exc
                if longitude is None:
                    longitude, latitude = row_longitude, row_latitude
                elif (longitude, latitude) != (row_longitude, row_latitude):
                    raise CommandError("The CSV contains inconsistent station coordinates.")
                start = observed_on if start is None else min(start, observed_on)
                end = observed_on if end is None else max(end, observed_on)
                count += 1
        if not count:
            raise CommandError("The downloaded CSV contains no observations.")
        return digest.hexdigest(), count, start, end, longitude, latitude

    def handle(self, *args, **options):
        country = options.get("country") or "Niger"
        station, display_name, station_slug, source_url = self._station_details(
            options.get("station"), country, options.get("source_url")
        )
        country_slug = slugify(country)
        asset_key = (
            f"arc2-{station_slug}" if country == "Niger" else f"arc2-{country_slug}-{station_slug}"
        ) if self.dataset_key == "arc2" else f"{self.dataset_key}-{country_slug}-{station_slug}"
        asset, _ = RCCDatasetAsset.objects.get_or_create(
            key=asset_key,
            defaults={
                "title": f"{self.dataset_label} daily rainfall — {display_name}",
                "summary": self.summary_text(display_name, country),
                "station": station,
                "country": country,
                "source_url": source_url,
            },
        )
        temporary_path = None
        prepared_path = None
        try:
            source_file = options.get("source_file")
            if source_file:
                temporary_path = str(Path(source_file).expanduser().resolve())
                if not Path(temporary_path).is_file():
                    raise CommandError("The supplied source file does not exist.")
            else:
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as target:
                    temporary_path = target.name
                    self.stdout.write(f"Downloading the {display_name} {self.dataset_label} source file...")
                    self._download(source_url, target, country, station)

            data_path, quality_note, prepared_path = self.prepare_source(temporary_path)
            checksum, count, start, end, longitude, latitude = self._validate(data_path, station, country)
            object_name = f"{self.dataset_key}/{country_slug}/{station_slug}/{checksum[:16]}/{station}.csv"
            storage = storages["rcc_data"]
            if not storage.exists(object_name):
                with open(data_path, "rb") as source:
                    storage.save(object_name, File(source))

            with transaction.atomic():
                asset.title = f"{self.dataset_label} daily rainfall — {display_name}"
                asset.summary = self.summary_text(display_name, country, quality_note)
                asset.station = station
                asset.country = country
                asset.longitude = str(longitude)
                asset.latitude = str(latitude)
                asset.source_url = source_url
                asset.object_name = object_name
                asset.original_filename = f"{station}.csv"
                asset.checksum_sha256 = checksum
                asset.size_bytes = os.path.getsize(data_path)
                asset.record_count = count
                asset.coverage_start = start
                asset.coverage_end = end
                asset.synced_at = timezone.now()
                asset.last_error = ""
                asset.save()
            self.stdout.write(self.style.SUCCESS(f"Synchronized {count:,} {display_name} observations."))
        except Exception as exc:
            asset.last_error = str(exc)
            asset.save(update_fields=["last_error"])
            raise
        finally:
            if prepared_path and os.path.exists(prepared_path):
                os.unlink(prepared_path)
            if temporary_path and not options.get("source_file") and os.path.exists(temporary_path):
                os.unlink(temporary_path)
