import csv
import os
import tempfile

from climweb.pages.services.management.commands.sync_rcc_arc2_station import Command as StationCommand


class Command(StationCommand):
    help = "Synchronize one CPC-Unified daily station rainfall CSV into RCC storage."
    dataset_key = "cpc-unified"
    dataset_label = "CPC-Unified"
    directory = "Synoptic_Daily_CPC_Unified_Data"
    root_catalogue_url = (
        "http://sgbd.acmad.org:8080/thredds/catalog/ACMAD/CDD/"
        "climatedataservice/Synoptic_Daily_CPC_Unified_Data/catalog.xml"
    )

    def prepare_source(self, path):
        """Keep valid dates while marking non-numeric source rainfall as missing."""
        invalid_count = 0
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", suffix=".csv", delete=False) as target:
            prepared_path = target.name
            try:
                with open(path, encoding="utf-8-sig", newline="") as source:
                    reader = csv.DictReader(source)
                    writer = csv.DictWriter(target, fieldnames=reader.fieldnames or [])
                    writer.writeheader()
                    for row in reader:
                        value = row.get("Precipitation")
                        if value:
                            try:
                                float(value)
                            except ValueError:
                                row["Precipitation"] = ""
                                invalid_count += 1
                        writer.writerow(row)
            except Exception:
                os.unlink(prepared_path)
                raise
        warning = (
            f"{invalid_count} non-numeric source precipitation values are blank in this hosted copy."
            if invalid_count else ""
        )
        return prepared_path, warning, prepared_path
