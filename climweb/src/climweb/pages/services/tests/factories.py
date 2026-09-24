import factory
import wagtail_factories
from faker import Faker
from wagtail.rich_text import RichText

from climweb.base.models import ServiceCategory
from ..models import (
    RCCClimateMonitoringPage,
    RCCConsensusForumPage,
    RCCClimateProductsPage,
    RCCDataServicesPage,
    RCCLongRangeForecastingPage,
    RCCRecommendedFunctionsPage,
    RCCTrainingPage,
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


class RCCLongRangeForecastingPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCLongRangeForecastingPage

    title = "Long-range Forecasting"
    banner_title = "Seasonal outlooks for Africa"
    banner_subtitle = "Regional climate guidance for the months and seasons ahead."
    introduction_title = "From global guidance to regional outlooks"
    introduction_text = RichText(
        "<p>ACMAD assesses global ensemble guidance and develops consolidated outlooks for Africa.</p>"
    )


class RCCTrainingPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCTrainingPage

    title = "Training"
    banner_title = "Strengthening climate-service capacity"
    banner_subtitle = "Methods, practical learning and regional knowledge exchange."
    introduction_title = "From climate data to usable regional services"
    introduction_text = RichText(
        "<p>ACMAD develops and shares practical climate-service skills.</p>"
    )
    focus_areas = [
        (
            "area",
            {
                "title": "Climate data services",
                "description": "Quality control, rescue and management.",
            },
        )
    ]
    programmes = [
        (
            "programme",
            {
                "title": "Workshops and seminars",
                "description": "Regional learning and knowledge exchange.",
                "icon": "group",
                "page": None,
                "external_url": "",
                "link_label": "",
            },
        )
    ]
    training_videos = [
        (
            "video",
            {
                "title": "Seasonal Forecasts Explained: Introduction",
                "description": "An introduction to seasonal forecasts.",
                "youtube_id": "CucEP23gWfU",
                "video_url": "https://www.youtube.com/watch?v=CucEP23gWfU",
            },
        )
    ]


class RCCRecommendedFunctionsPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCRecommendedFunctionsPage

    title = "Highly Recommended Functions"
    banner_title = "Climate-change analysis for African decision-making"
    banner_subtitle = "Model evaluation, scenarios, risk studies and indices."
    introduction_title = "Turning climate science into regional evidence"
    introduction_text = RichText(
        "<p>ACMAD assesses observed and projected climate change across Africa.</p>"
    )
    functions = [
        (
            "function",
            {
                "activity": "Detect and project changes in climate indices",
                "output_title": "Climate-change indices",
                "description": "Observed trends and projected indices for African stations.",
                "icon": "globe",
                "topics": ["Observed trends", "RCP scenarios"],
                "related_page": None,
                "external_url": "https://example.com/climate-indices/",
                "link_label": "Open indices application",
            },
        )
    ]
    evidence_heading = "Research reports and climate-change evidence"
    evidence_introduction = RichText("<p>Regional climate-change reports.</p>")


class RCCConsensusForumPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = RCCConsensusForumPage

    title = "Central Africa Climate Outlook Forum"
    banner_title = "Central Africa Climate Outlook Forum"
    forum_code = "PRESAC"
    region = "Central Africa"
    target_season = "October–November–December"
    summary = "Consensus seasonal guidance for Central Africa."
    overview = RichText("<p>Regional forum overview.</p>")
