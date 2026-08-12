"""Shared helpers for products owned by the ACMAD Regional Climate Center."""

from climweb.base.models import ServiceCategory


RCC_SERVICE_NAME = "Regional Climate Center"


def get_rcc_service_category():
    """Resolve the editor-created RCC service, creating it when absent."""
    service, _ = ServiceCategory.objects.get_or_create(
        name=RCC_SERVICE_NAME,
        defaults={"icon": "cloud-sun-rain"},
    )
    return service
