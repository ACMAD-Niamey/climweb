from django.core.management.base import BaseCommand

from climweb.pages.services.long_range_forums import CONSENSUS_FORUMS
from climweb.pages.services.models import (
    RCCConsensusForumPage,
    RCCLongRangeForecastingPage,
)


DEFAULT_CONSENSUS_METHOD = (
    "<p>Experts assess global and regional ensemble forecasts, statistical "
    "guidance, recent climate conditions, analogue years, trends and available "
    "verification. The evidence is discussed jointly, uncertainties are "
    "documented, and a consensus outlook is prepared for communication and "
    "national downscaling.</p>"
)


def paragraph(value):
    return f"<p>{value}</p>" if value else ""


class Command(BaseCommand):
    help = "Create the editable RCC Regional Climate Outlook Forum pages."

    def handle(self, *args, **options):
        parent = RCCLongRangeForecastingPage.objects.live().first()
        if not parent:
            self.stderr.write(
                "The RCC Long-range Forecasting page was not found; forum page "
                "creation was deferred."
            )
            return

        created = 0
        preserved = 0
        for definition in CONSENSUS_FORUMS:
            page = RCCConsensusForumPage.objects.child_of(parent).filter(
                slug=definition["slug"]
            ).first()
            if page:
                preserved += 1
                continue

            page = RCCConsensusForumPage(
                title=str(definition["name"]),
                slug=definition["slug"],
                banner_title=str(definition["name"]),
                banner_subtitle=str(definition["summary"]),
                banner_image=parent.banner_image,
                forum_code=definition["code"],
                region=str(definition["region"]),
                target_season=str(definition["season"]),
                summary=str(definition["summary"]),
                overview=paragraph(definition["overview"]),
                geographic_coverage=paragraph(definition["coverage"]),
                climate_drivers=paragraph(definition["drivers"]),
                climate_hazards=paragraph(definition["hazards"]),
                consensus_method=DEFAULT_CONSENSUS_METHOD,
                user_involvement=paragraph(definition["users"]),
                development_priorities=paragraph(definition["priorities"]),
                archive_codes=",".join(definition["document_codes"]),
            )
            parent.add_child(instance=page)
            page.save_revision().publish()
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"RCC consensus forum pages: created={created}, "
                f"preserved={preserved}."
            )
        )
