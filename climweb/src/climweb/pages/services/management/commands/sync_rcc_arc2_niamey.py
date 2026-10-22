from .sync_rcc_arc2_station import Command as StationCommand


class Command(StationCommand):
    """Backward-compatible shortcut for the original Niamey pilot."""

    help = "Synchronize the Niamey-Aero ARC2 daily rainfall CSV into RCC storage."
    default_station = "NIAMEY-AERO"
