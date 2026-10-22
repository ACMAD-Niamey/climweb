import factory
import wagtail_factories

from .. import models


class BoardPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.BoardPage

    title = "Board of Governors"
    banner_title = "Board of Governors"
    banner_image = factory.SubFactory(wagtail_factories.ImageFactory)


class BoardPresidentPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.BoardPresidentPage

    title = "President of the Board"
    banner_title = "President of the Board"
    name = "Dr. Board President"
    biography = "<p>A leader committed to climate resilience.</p>"
    vision = "<p>A safer, climate-resilient Africa.</p>"


class DirectorGeneralPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.DirectorGeneralPage

    title = "Director General"
    banner_title = "Director General"
    photo_caption = "Director General of ACMAD"
    inaugural_speech = "<p>Together, we will strengthen ACMAD.</p>"
