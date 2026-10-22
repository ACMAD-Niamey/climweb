import factory
import wagtail_factories

from .. import models


class AboutPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.AboutPage
    
    title = "About Us"
    banner_title = "About ACMAD"
    introduction_title = "Who we are"
    introduction_text = factory.Faker('paragraph')
