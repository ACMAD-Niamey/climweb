from celery import shared_task
from celery_singleton import Singleton
from django.core.management import call_command


@shared_task(base=Singleton, unique_on=[], lock_expiry=60 * 60)
def sync_rcc_arc2_niamey():
    """Refresh the locally hosted Niamey ARC2 dataset."""
    call_command("sync_rcc_arc2_niamey")


@shared_task(base=Singleton, unique_on=["station"], lock_expiry=60 * 60)
def sync_rcc_arc2_station(station):
    """Refresh one locally hosted Niger ARC2 station dataset."""
    call_command("sync_rcc_arc2_station", station)
