import factory
import wagtail_factories

from .. import models


class SummerSchoolIndexPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.SummerSchoolIndexPage

    title = "Summer School"


class SummerSchoolPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.SummerSchoolPage

    title = factory.Sequence(lambda n: "Summer School Edition {}".format(n))
    hero_heading = factory.Sequence(lambda n: "Climate Summer School Edition {}".format(n))
    hero_description = factory.Sequence(lambda n: "Description for edition {}".format(n))


class SummerSchoolApplicationPageFactory(wagtail_factories.PageFactory):
    class Meta:
        model = models.SummerSchoolApplicationPage

    title = factory.Sequence(lambda n: "Apply {}".format(n))
    introduction_title = "Apply for the Summer School"
    introduction_subtitle = "Fill in the form below to apply."
