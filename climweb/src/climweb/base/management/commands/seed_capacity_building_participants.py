"""Load demo Capacity Building Participant records.

This is an OPT-IN convenience for demos and manual testing - it is deliberately
*not* a data migration, because participant records are real people's data that
the programme office maintains by hand. The demo rows use placeholder names
("<Country> participant 1") and mirror the per-country totals on ACMAD's public
"Capacity Building over Africa" reference map so the choropleth renders something
recognisable straight away. Editors then delete these and enter the real people.

    python manage.py seed_capacity_building_participants          # add demo rows
    python manage.py seed_capacity_building_participants --wipe   # re-seed from scratch

``--wipe`` only deletes rows that exactly match the bundled demo data (by name +
country), so hand-entered records are never affected.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Q

from climweb.base.models import CapacityBuildingParticipant

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "capacity_building_participants_demo.json"


class Command(BaseCommand):
    help = "Create demo Capacity Building Participant records for the participant map."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete the exact bundled demo rows before seeding.",
        )

    def handle(self, *args, **options):
        rows = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        if options["wipe"]:
            # Only ever remove the exact rows this command seeds - matched by the
            # (full_name, country) pair from the bundled JSON - so a real record
            # is never touched.
            match = Q()
            for row in rows:
                match |= Q(full_name=row["full_name"], country=row["country"])
            deleted, _ = CapacityBuildingParticipant.objects.filter(match).delete()
            self.stdout.write(self.style.WARNING(f"Removed {deleted} demo record(s)."))

        created = 0
        for row in rows:
            _, was_created = CapacityBuildingParticipant.objects.get_or_create(
                full_name=row["full_name"],
                country=row["country"],
                defaults={
                    "institution": row.get("institution", ""),
                    "gender": row["gender"],
                    "category": row["category"],
                    "start_date": row["start_date"],
                    "end_date": row.get("end_date"),
                    "is_active": row.get("is_active", True),
                },
            )
            created += int(was_created)

        self.stdout.write(self.style.SUCCESS(
            f"Demo participants ready: {created} created, "
            f"{CapacityBuildingParticipant.objects.count()} total."
        ))
