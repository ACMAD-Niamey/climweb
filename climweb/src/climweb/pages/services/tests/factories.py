import factory
import wagtail_factories
from faker import Faker
from wagtail.rich_text import RichText

from climweb.base.models import ServiceCategory
from ..models import (
    RCCClimateMonitoringPage,
    RCCClimateProductsPage,
    RCCDataServicesPage,
    ServiceIndexPage,
    ServicePage,
)

fake = Faker()


class ServiceCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceCategory
    
    name = factory.Sequence(lambda n: f"Service {n}")
    icon = factory.Faker("random_element", elements=["desktop", "comment", "date"])


class ServiceIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ServiceIndexPage
    
    title = "Services"


class ServicePageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = ServicePage
    
    title = factory.sequence(lambda n: f"Service {n}")
    banner_image = factory.SubFactory(wagtail_factories.ImageFactory)
    banner_title = factory.Faker("sentence")
    
    introduction_title = factory.Faker("sentence")
    introduction_image = factory.SubFactory(wagtail_factories.ImageFactory)
    service = factory.SubFactory(ServiceCategoryFactory)
    
    @factory.lazy_attribute
    def introduction_text(self):
        p = fake.paragraph()
        return RichText(f"<p>{p}</p>")


class RCCDataServicesPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCDataServicesPage

    title = "Data Services"
    banner_title = "Climate data for Africa"
    banner_subtitle = "Observations, gridded datasets and model archives."
    introduction_title = "One catalogue for regional climate data"
    introduction_text = RichText("<p>Find climate datasets and understand their access conditions.</p>")
    catalogue_notice = RichText("<p>Access and freshness vary by source.</p>")
    data_groups = [
        (
            "group",
            {
                "anchor": "observations",
                "title": "Observations and station data",
                "summary": "Station observations for climate monitoring.",
                "icon": "database",
                "datasets": [
                    {
                        "title": "ARC2 estimated rainfall",
                        "description": "Daily station rainfall estimates.",
                        "coverage": "Africa",
                        "formats": "THREDDS catalogue",
                        "access_type": "open",
                        "access_url": "https://example.com/arc2/",
                        "source": "ACMAD SGBD",
                        "last_verified": "2026-09-08",
                    }
                ],
            },
        )
    ]


class RCCClimateProductsPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCClimateProductsPage

    title = "Climate Products"
    banner_title = "Climate products for Africa"
    banner_subtitle = "Operational monitoring and forecast products from ACMAD."
    introduction_title = "Regional climate intelligence"
    introduction_text = RichText("<p>Browse RCC climate products for Africa.</p>")


class RCCClimateMonitoringPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCClimateMonitoringPage

    title = "Climate Monitoring"
    banner_title = "Climate monitoring for Africa"
    banner_subtitle = "Tracking present climate conditions, anomalies and extremes."
    introduction_title = "Monitoring Africa's climate system"
    introduction_text = RichText(
        "<p>ACMAD monitors the ocean-land-atmosphere system using observations, analyses and reanalyses.</p>"
    )
