from django.conf import settings
from django.contrib import messages
from django.core.mail import mail_admins
from django.db import models
from django.template.defaultfilters import truncatechars
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from loguru import logger
from modelcluster.fields import ParentalKey
from wagtail import blocks
from wagtail.admin.panels import (FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel, TabbedInterface,
                                  ObjectList)
from wagtail.contrib.forms.models import AbstractEmailForm, AbstractFormField, FORM_FIELD_CHOICES
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtailcaptcha.forms import remove_captcha_field
from wagtailcaptcha.models import WagtailCaptchaEmailForm
from wagtailiconchooser.widgets import IconChooserWidget

from climweb.base import blocks as base_blocks
from climweb.base.forms import (FormImageField, FormDocumentField, CustomSubmissionsListView,
                                CustomWagtailCaptchaFormBuilder)
from climweb.base.mixins import MetadataPageMixin
from climweb.base.models import FormFileSubmission
from climweb.base.seo_utils import get_homepage_meta_image, get_homepage_meta_description
from climweb.base.utils import get_duplicates, generate_title_from_filename
from .blocks import CohortBlock, ScheduleSessionBlock, SummerSchoolPartnerBlock, TrainerBlock

SUMMARY_RICHTEXT_FEATURES = getattr(settings, "SUMMARY_RICHTEXT_FEATURES")


class SummerSchoolIndexPage(MetadataPageMixin, Page):
    template = 'summer_school_index_page.html'
    parent_page_types = ['home.HomePage']
    subpage_types = ['summer_school.SummerSchoolPage']
    max_count = 1
    show_in_menus = True

    # --- Hero ---
    hero_heading = models.CharField(max_length=255, blank=True, verbose_name=_("Hero Heading"))
    hero_subtitle = models.CharField(max_length=255, blank=True, verbose_name=_("Hero Subtitle"))
    hero_description = RichTextField(blank=True, features=SUMMARY_RICHTEXT_FEATURES,
                                     verbose_name=_("Hero Description"))
    hero_badges = StreamField([
        ('badge', blocks.CharBlock(max_length=60)),
    ], blank=True, use_json_field=True, verbose_name=_("Hero Badges"))
    hero_background_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Hero Background Image"),
    )

    # --- Bottom banner ---
    banner_heading = models.CharField(max_length=255, blank=True, verbose_name=_("Banner Heading"))
    banner_description = RichTextField(blank=True, features=SUMMARY_RICHTEXT_FEATURES,
                                       verbose_name=_("Banner Description"))

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('hero_heading'),
            FieldPanel('hero_subtitle'),
            FieldPanel('hero_description'),
            FieldPanel('hero_badges'),
            FieldPanel('hero_background_image'),
        ], heading=_("Hero")),
        MultiFieldPanel([
            FieldPanel('banner_heading'),
            FieldPanel('banner_description'),
        ], heading=_("Bottom Banner")),
    ]

    class Meta:
        verbose_name = _("Summer School Index Page")

    def get_meta_image(self):
        meta_image = super().get_meta_image()

        if not meta_image:
            meta_image = self.hero_background_image

        if not meta_image:
            meta_image = get_homepage_meta_image(self.get_site())

        return meta_image

    def get_meta_description(self):
        meta_description = super().get_meta_description()

        if not meta_description:
            meta_description = get_homepage_meta_description(self.get_site())

        return meta_description

    @cached_property
    def editions(self):
        return SummerSchoolPage.objects.live().child_of(self).order_by('-featured', '-edition_start_date')

    @cached_property
    def programmes_count(self):
        return self.editions.count()

    @cached_property
    def unique_badge_tags(self):
        tags = []
        for edition in self.editions:
            for badge in edition.hero_badges:
                if badge.value not in tags:
                    tags.append(badge.value)
        return tags

    @cached_property
    def upcoming_count(self):
        today = timezone.now().date()
        return self.editions.filter(edition_start_date__gte=today).count()

    @cached_property
    def past_cohorts_count(self):
        return sum(len(edition.cohorts) for edition in self.editions)


class SummerSchoolPage(MetadataPageMixin, Page):
    template = 'summer_school_page.html'
    parent_page_types = ['summer_school.SummerSchoolIndexPage']
    subpage_types = ['summer_school.SummerSchoolApplicationPage']

    # --- Hero ---
    program_tagline = models.CharField(max_length=255, blank=True, verbose_name=_("Program Tagline"))
    hero_heading = models.CharField(max_length=255, verbose_name=_("Hero Heading"))
    hero_description = RichTextField(features=SUMMARY_RICHTEXT_FEATURES, verbose_name=_("Hero Description"))
    hero_badges = StreamField([
        ('badge', blocks.CharBlock(max_length=60)),
    ], blank=True, use_json_field=True, verbose_name=_("Hero Badges"))
    hero_background_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Hero Background Image"),
    )
    decorative_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Decorative Image"),
    )
    cta_primary_text = models.CharField(max_length=60, blank=True, verbose_name=_("Primary CTA Text"))
    cta_primary_page = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Primary CTA - Internal Page"),
    )
    cta_primary_external_url = models.URLField(blank=True, verbose_name=_("Primary CTA - External URL"),
                                               help_text=_("If provided, the internal page link is ignored"))
    cta_secondary_text = models.CharField(max_length=60, blank=True, verbose_name=_("Secondary CTA Text"))
    cta_secondary_page = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Secondary CTA - Internal Page"),
    )
    cta_secondary_external_url = models.URLField(blank=True, verbose_name=_("Secondary CTA - External URL"),
                                                 help_text=_("If provided, the internal page link is ignored"))

    # --- Key Info ---
    key_info_dates = models.CharField(max_length=255, blank=True, verbose_name=_("Dates"))
    edition_start_date = models.DateField(null=True, blank=True, verbose_name=_("Edition Start Date"),
                                          help_text=_("Used to order editions on the index page"))
    key_info_location = models.CharField(max_length=255, blank=True, verbose_name=_("Location"))
    key_info_format = models.CharField(max_length=255, blank=True, verbose_name=_("Format"))
    key_info_language = models.CharField(max_length=255, blank=True, verbose_name=_("Language"))
    key_info_certificate = models.CharField(max_length=255, blank=True, verbose_name=_("Certificate"))
    key_info_contact = models.CharField(max_length=255, blank=True, verbose_name=_("Contact"))
    apply_button_text = models.CharField(max_length=60, default="Apply", verbose_name=_("Apply Button Text"))

    # --- Index card display ---
    card_icon = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Card Icon"),
                                 help_text=_("Small icon shown on this edition's card on the index page"))
    status_badge_text = models.CharField(max_length=60, blank=True, verbose_name=_("Status Badge Text"),
                                         help_text=_("e.g. 'Applications opening soon', 'Applications open'. "
                                                     "Leave blank to hide the badge."))

    # --- Background ---
    background_intro = RichTextField(blank=True, features=SUMMARY_RICHTEXT_FEATURES,
                                     verbose_name=_("Background Introduction"))
    background_items = StreamField([
        ('card', base_blocks.WhatWeDoBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("Background Items"))

    # --- Eligibility ---
    eligibility_intro = RichTextField(blank=True, features=SUMMARY_RICHTEXT_FEATURES,
                                      verbose_name=_("Eligibility Introduction"))
    eligibility_criteria = StreamField([
        ('item', blocks.CharBlock(max_length=200)),
    ], blank=True, use_json_field=True, verbose_name=_("Eligibility Criteria"))
    prerequisite_courses_text = models.CharField(max_length=150, blank=True,
                                                 default="View pre-requisite courses",
                                                 verbose_name=_("Pre-requisite Courses - Link Text"))
    prerequisite_courses_url = models.URLField(blank=True, verbose_name=_("Pre-requisite Courses - External URL"),
                                               help_text=_("Link to an external course a candidate should complete "
                                                           "before applying"))

    # --- Structure ---
    structure_items = StreamField([
        ('card', base_blocks.WhatWeDoBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("Structure Items"))

    # --- Trainers ---
    trainers = StreamField([
        ('trainer', TrainerBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("Trainers"))

    # --- Schedule ---
    schedule_sessions = StreamField([
        ('session', ScheduleSessionBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("Schedule Sessions"))

    # --- Cohorts ---
    cohorts = StreamField([
        ('cohort', CohortBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("Cohorts"))

    # --- Concept Note ---
    concept_note_title = models.CharField(max_length=255, default="Concept Note",
                                          verbose_name=_("Concept Note Title"))
    concept_note_thumbnail = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Concept Note Thumbnail"),
    )
    concept_note_description = RichTextField(blank=True, verbose_name=_("Concept Note Description"))
    concept_note_checklist = StreamField([
        ('item', blocks.CharBlock(max_length=100)),
    ], blank=True, use_json_field=True, verbose_name=_("Concept Note Checklist"))
    concept_note_document = models.ForeignKey(
        'base.CustomDocumentModel',
        verbose_name=_("Concept Note Document"),
        help_text=_("Downloadable concept note document, preferably in PDF format"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    # --- Sponsors, Organizers & Partners ---
    partners = StreamField([
        ('partner', SummerSchoolPartnerBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("Sponsors, Organizers & Partners"))

    # --- FAQ ---
    faq = StreamField([
        ('faq', base_blocks.AccordionBlock()),
    ], blank=True, use_json_field=True, verbose_name=_("FAQ"))
    faq_view_all_text = models.CharField(max_length=60, blank=True, verbose_name=_("FAQ - View All Text"))
    faq_view_all_page = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("FAQ - View All Page"),
    )

    # --- Flags ---
    featured = models.BooleanField(default=False, verbose_name=_("Featured"),
                                   help_text=_("Show this edition as featured ?"))
    is_hidden = models.BooleanField(default=False, verbose_name=_("Is hidden"),
                                    help_text=_("Make this edition hidden in listings or elsewhere"))
    is_visible_on_homepage = models.BooleanField(default=False, verbose_name=_("Is visible on homepage"),
                                                 help_text=_("Show this edition on the homepage ?"))
    application_open = models.BooleanField(default=True, verbose_name=_("Application open"))

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('program_tagline'),
            FieldPanel('hero_heading'),
            FieldPanel('hero_description'),
            FieldPanel('hero_badges'),
            FieldPanel('hero_background_image'),
            FieldPanel('decorative_image'),
            FieldPanel('cta_primary_text'),
            FieldPanel('cta_primary_page'),
            FieldPanel('cta_primary_external_url'),
            FieldPanel('cta_secondary_text'),
            FieldPanel('cta_secondary_page'),
            FieldPanel('cta_secondary_external_url'),
        ], heading=_("Hero")),
        MultiFieldPanel([
            FieldPanel('key_info_dates'),
            FieldPanel('edition_start_date'),
            FieldPanel('key_info_location'),
            FieldPanel('key_info_format'),
            FieldPanel('key_info_language'),
            FieldPanel('key_info_certificate'),
            FieldPanel('key_info_contact'),
            FieldPanel('apply_button_text'),
        ], heading=_("Key Info")),
        MultiFieldPanel([
            FieldPanel('card_icon', widget=IconChooserWidget),
            FieldPanel('status_badge_text'),
        ], heading=_("Index Card Display")),
        MultiFieldPanel([
            FieldPanel('background_intro'),
            FieldPanel('background_items'),
        ], heading=_("Background")),
        MultiFieldPanel([
            FieldPanel('eligibility_intro'),
            FieldPanel('eligibility_criteria'),
            FieldPanel('prerequisite_courses_text'),
            FieldPanel('prerequisite_courses_url'),
        ], heading=_("Eligibility")),
        MultiFieldPanel([
            FieldPanel('structure_items'),
        ], heading=_("Structure")),
        MultiFieldPanel([
            FieldPanel('trainers'),
        ], heading=_("Trainers")),
        MultiFieldPanel([
            FieldPanel('schedule_sessions'),
        ], heading=_("Schedule")),
        MultiFieldPanel([
            FieldPanel('cohorts'),
        ], heading=_("Cohorts")),
        MultiFieldPanel([
            FieldPanel('concept_note_title'),
            FieldPanel('concept_note_thumbnail'),
            FieldPanel('concept_note_description'),
            FieldPanel('concept_note_checklist'),
            FieldPanel('concept_note_document'),
        ], heading=_("Concept Note")),
        MultiFieldPanel([
            FieldPanel('partners'),
        ], heading=_("Sponsors, Organizers & Partners")),
        MultiFieldPanel([
            FieldPanel('faq'),
            FieldPanel('faq_view_all_text'),
            FieldPanel('faq_view_all_page'),
        ], heading=_("FAQ")),
        FieldPanel('featured'),
        FieldPanel('is_hidden'),
        FieldPanel('is_visible_on_homepage'),
    ]

    settings_panels = [
        FieldPanel('application_open'),
    ]

    # This is where all the tabs are created
    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading=_('Content')),
            ObjectList(Page.promote_panels, heading=_('SEO'), classname="seo"),
            ObjectList(settings_panels, heading=_('Settings'), classname="settings"),
        ]
    )

    class Meta:
        ordering = ['-edition_start_date']
        verbose_name = _("Summer School Page")

    def get_meta_image(self):
        meta_image = super().get_meta_image()

        # try getting the hero background image
        if not meta_image:
            meta_image = self.hero_background_image

        # try getting the parent (index page) image
        if not meta_image:
            meta_image = self.get_parent().specific.get_meta_image()

        return meta_image

    def get_meta_description(self):
        meta_description = super().get_meta_description()

        # try getting the parent (index page) description
        if not meta_description:
            meta_description = self.get_parent().specific.get_meta_description()

        return meta_description

    @cached_property
    def application_page(self):
        return self.get_first_child()

    @cached_property
    def card_props(self):
        # same contract NewsPage/EventPage use, so this edition can slot into
        # the homepage's generic "Latest Updates" card loop unchanged
        return {
            "card_image": self.hero_background_image,
            "card_title": self.hero_heading,
            "card_text": self.hero_description,
            "card_meta": self.key_info_dates,
            "card_more_link": self.url,
            "card_tag": _("Summer School"),
            "card_tags": "",
        }

    @cached_property
    def has_eligibility_content(self):
        return bool(self.eligibility_intro or self.eligibility_criteria or self.prerequisite_courses_url)

    @cached_property
    def is_upcoming(self):
        if not self.edition_start_date:
            return False
        return self.edition_start_date >= timezone.now().date()

    @cached_property
    def schedule_data(self):
        sessions_list = list(self.schedule_sessions)
        sessions_list.sort(key=lambda s: s.value.get("start_time"))

        sessions_by_date = {}

        for session in sessions_list:
            start_time = session.value.get("start_time")
            st = start_time.strftime('%I:%M %p')
            ct = f"{st}"
            session_date = start_time.date()

            if sessions_by_date.get(session_date) is None:
                sessions_by_date[session_date] = {}
                sessions_by_date[session_date][ct] = [session]
            else:
                if sessions_by_date[session_date].get(ct) is None:
                    sessions_by_date[session_date][ct] = [session]
                else:
                    sessions_by_date[session_date][ct].append(session)

        return sessions_by_date

    @cached_property
    def partners_by_role(self):
        grouped = {'sponsor': [], 'organizer': [], 'partner': []}

        for item in self.partners:
            role = item.value.get('role') or 'partner'
            grouped.setdefault(role, []).append(item.value)

        return grouped


class SummerSchoolApplicationPage(MetadataPageMixin, WagtailCaptchaEmailForm):
    required_css_class = 'required'
    form_builder = CustomWagtailCaptchaFormBuilder
    submissions_list_view_class = CustomSubmissionsListView

    template = 'summer_school_application_page.html'
    landing_page_template = 'form_thank_you_landing.html'
    parent_page_types = ['summer_school.SummerSchoolPage']
    subpage_types = []
    max_count_per_parent = 1

    # don't cache this page because it has a form
    cache_control = 'no-cache'

    introduction_title = models.CharField(max_length=255, verbose_name=_("Introduction Title"))
    introduction_subtitle = models.TextField(blank=True, null=True, verbose_name=_("Introduction Subtitle"))
    illustration = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        verbose_name=_("Illustration")
    )
    thank_you_text = models.TextField(blank=True, null=True, verbose_name=_("Thank you text"))
    application_deadline = models.DateField(null=True, blank=True, verbose_name=_("Application Deadline"))
    journey_stages = StreamField([
        ('stage', blocks.CharBlock(max_length=60)),
    ], blank=True, use_json_field=True, verbose_name=_("Application Journey Stages"))
    journey_note = models.CharField(max_length=255, blank=True, verbose_name=_("Application Journey Note"),
                                    help_text=_("Optional caption shown under the journey steps"))
    validation_field = models.CharField(max_length=100, blank=True, default="email_address",
                                        verbose_name=_("Validation Field"),
                                        help_text=_("A field on the form to check if is already submitted so as to "
                                                    "prevent multiple submissions by one person. This is usually the "
                                                    "email address field in snake casing format"))

    content_panels = AbstractEmailForm.content_panels + [
        FieldPanel('introduction_title'),
        FieldPanel('introduction_subtitle'),
        FieldPanel('illustration'),
        FieldPanel('application_deadline'),
        MultiFieldPanel([
            FieldPanel('journey_stages'),
            FieldPanel('journey_note'),
        ], heading=_("Application Journey")),
        InlinePanel('application_form_fields', label="Form fields"),
        FieldPanel('validation_field'),
        FieldPanel('thank_you_text'),
        MultiFieldPanel([
            FieldRowPanel([
                FieldPanel('from_address', classname="col6"),
                FieldPanel('to_address', classname="col6"),
            ]),
            FieldPanel('subject'),
        ], "Email"),
    ]

    class Meta:
        verbose_name = _("Summer School Application Page")

    def get_meta_image(self):
        meta_image = super().get_meta_image()

        if not meta_image and self.illustration:
            meta_image = self.illustration

        # try getting the parent (summer school page) image
        if not meta_image:
            meta_image = self.get_parent().specific.get_meta_image()

        return meta_image

    def get_meta_description(self):
        meta_description = super().get_meta_description()

        if not meta_description and self.introduction_subtitle:
            meta_description = truncatechars(self.introduction_subtitle, 160)

        # try getting the parent (summer school page) description
        if not meta_description:
            meta_description = self.get_parent().specific.get_meta_description()

        return meta_description

    def get_form_fields(self):
        return self.application_form_fields.all()

    def get_form_class(self):
        form_class = super(SummerSchoolApplicationPage, self).get_form_class()
        form_class.required_css_class = 'required'
        return form_class

    def save(self, *args, **kwargs):
        if not self.search_description and self.introduction_subtitle:
            # Limit the search meta desc to google's 160 recommended chars
            self.search_description = truncatechars(self.introduction_subtitle, 160)
        return super().save(*args, **kwargs)

    def should_process_form(self, request, form_data):
        """
        Duplicate-submission check keyed on a single, specific field (self.validation_field).

        Adapted from EventRegistrationPage.should_process_form - unlike the generic
        "any two answers repeat" spam heuristic used by FeedbackPage, this checks whether
        a previous submission already used the same value for the configured field
        (usually an email address), to stop the same applicant applying twice.
        """
        should_process = True

        validation_field = self.validation_field.replace('-', '_')
        submission_class = self.get_submission_class()
        form_validation_value = form_data.get(validation_field)

        # try getting email using email or email_address
        if not form_validation_value:
            form_validation_value = form_data.get("email") or form_data.get("email_address")

        if form_validation_value:
            queryset = submission_class.objects.filter(form_data__icontains=form_validation_value, page=self)
            if queryset.exists():
                message = "An application with {} - {} had already been submitted. " \
                          "This means you have already applied. " \
                          "Contact us if you think this is a mistake.".format(
                    validation_field.replace('_', ' '),
                    form_validation_value)
                messages.add_message(request, messages.ERROR, message)

                # We have a duplicate. Do not continue to process form
                should_process = False
        else:
            try:
                # send admins an email so that they check that a correct field is set
                mail_admins(subject="Incorrect form validation field found !",
                            message="Incorrect validation field  - {} - set for the form page {}. Please "
                                    "make sure the correct field is set to avoid duplicate submissions and "
                                    "stop these messages from being sent".format(self.validation_field, self.title),
                            fail_silently=True)
            except Exception as e:
                logger.error("[SUMMER_SCHOOL_APPLICATION_PAGE] Incorrect form validation field."
                             " Error sending email to admins: {}".format(e))

            # meanwhile, mark the form for saving
            should_process = True

        return should_process

    def serve(self, request, *args, **kwargs):
        if request.method == 'POST':
            form = self.get_form(request.POST, request.FILES, page=self, user=request.user)

            if form.is_valid():
                form_submission = None

                if self.validation_field:
                    # check for a duplicate submission keyed on the specific validation field
                    if self.should_process_form(request, form_data=form.data):
                        form_submission = self.process_form_submission(form)
                else:
                    try:
                        # see if we have any duplicated field values. Notorious with spammers !
                        duplicate_fields = get_duplicates(form.cleaned_data)
                    except Exception as e:
                        logger.error(f"[SUMMER_SCHOOL_APPLICATION_PAGE] Error checking for duplicate fields: {e}")
                        duplicate_fields = []

                    if not duplicate_fields:
                        form_submission = self.process_form_submission(form)
                    else:
                        self.process_suspicious_form(form)

                return self.render_landing_page(request, form_submission, *args, **kwargs)
        else:
            form = self.get_form(page=self, user=request.user)

        context = self.get_context(request)
        context['form'] = form
        return TemplateResponse(
            request,
            self.get_template(request),
            context
        )

    def process_suspicious_form(self, form):
        remove_captcha_field(form)
        try:
            logger.warning(f"[SUMMER_SCHOOL_APPLICATION_PAGE] Possible spam detected: {form.cleaned_data}")
            self.send_suspicious_form_to_admin(form)
        except Exception as e:
            logger.error(f"[SUMMER_SCHOOL_APPLICATION_PAGE] Error sending suspicious form to admin: {e}")

    def send_suspicious_form_to_admin(self, form):
        content = []
        for field in form:
            value = field.value()
            if isinstance(value, list):
                value = ', '.join(value)
            content.append('{}: {}'.format(field.label, value))
        content = '\n'.join(content)

        mail_admins("POSSIBLE SPAM (SUMMER SCHOOL APPLICATION PAGE) - {}".format(self.subject), content,
                   fail_silently=True)

    def process_form_submission(self, form):
        cleaned_data = form.cleaned_data

        for name, field in form.fields.items():
            file_type = None
            if isinstance(field, FormImageField):
                file_type = 'image'
            elif isinstance(field, FormDocumentField):
                file_type = 'document'

            if file_type:
                file = cleaned_data.get(name)
                if file:
                    file.title = generate_title_from_filename(file.name)

                    file_submission = FormFileSubmission.objects.create(
                        file=file,
                        file_type=file_type,
                    )

                    cleaned_data[name] = file_submission.pk
                else:
                    del cleaned_data[name]

        return super(SummerSchoolApplicationPage, self).process_form_submission(form)


class SummerSchoolApplicationFormField(AbstractFormField):
    FILE_SUBMISSION_FIELD_CHOICES = (
        ("image", _("Upload Image")),
        ("document", _("Upload PDF Document")),
    )

    field_type = models.CharField(
        verbose_name=_("field type"), max_length=16, choices=FORM_FIELD_CHOICES + FILE_SUBMISSION_FIELD_CHOICES
    )

    page = ParentalKey(SummerSchoolApplicationPage,
                       on_delete=models.CASCADE,
                       related_name="application_form_fields")
