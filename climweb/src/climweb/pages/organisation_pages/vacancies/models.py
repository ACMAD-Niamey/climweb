from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import BooleanField
from wagtail import blocks as wagtail_blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from climweb.base.mixins import MetadataPageMixin
from climweb.base.models import AbstractBannerWithOptionalIntroPage
from climweb.base.utils import paginate, get_first_non_empty_p_string
from climweb.config.settings.base import SUMMARY_RICHTEXT_FEATURES


class VacanciesPage(AbstractBannerWithOptionalIntroPage):
    template = 'vacancies_index_page.html'
    parent_page_types = ['organisation.OrganisationIndexPage']
    subpage_types = ['vacancies.VacancyDetailPage']
    max_count = 1
    show_in_menus = True
    show_in_menus_default = True
    
    banner_image = models.ForeignKey(
        'wagtailimages.Image',
        verbose_name=_("Banner Image"),
        help_text=_("A high quality image related to Vacancies"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    
    items_per_page = models.PositiveIntegerField(default=6, validators=[
        MinValueValidator(6),
        MaxValueValidator(20),
    ], help_text=_("How many items should be visible on the landing page filter section ?"),
                                                 verbose_name=_("Items per page"))
    
    no_vacancies_header_text = models.TextField(blank=True, null=True,
                                                help_text=_("Text to appear when there are no vacancies"),
                                                verbose_name=_("No vacancies header text"))
    
    no_vacancies_description_text = models.TextField(blank=True, null=True,
                                                     help_text=_(
                                                         "Additional text to appear when there are no vacancies,"
                                                         "below the no vacancies header text"),
                                                     verbose_name=_("No vacancies description text"))
    
    content_panels = Page.content_panels + [
        *AbstractBannerWithOptionalIntroPage.content_panels,
        MultiFieldPanel(
            [
                FieldPanel('no_vacancies_header_text'),
                FieldPanel('no_vacancies_description_text'),
                FieldPanel('items_per_page'),
            ],
            heading=_("Other Settings"),
        ),
    ]
    
    def get_meta_image(self):
        meta_image = super().get_meta_image()
        
        if not meta_image:
            meta_image = self.get_parent().specific.get_meta_image()
        
        return meta_image
    
    @cached_property
    def listing_image(self):
        if self.banner_image:
            return self.banner_image
        if self.introduction_image:
            return self.introduction_image
        return None
    
    def filter_vacancies(self, request):
        vacancies = self.all_vacancies
        
        is_open = request.GET.get("open")
        
        filters = models.Q()
        
        if is_open and is_open.lower() == "true":
            filters &= models.Q(deadline__gt=timezone.now())
        elif is_open and is_open.lower() == "false":
            filters &= models.Q(deadline__lt=timezone.now())
        
        return vacancies.filter(filters)
    
    def filter_and_paginate_vacancies(self, request):
        page = request.GET.get('page')
        
        filtered_vacancies = self.filter_vacancies(request)
        
        paginated_projects = paginate(filtered_vacancies, page, self.items_per_page)
        
        return paginated_projects
    
    @cached_property
    def all_vacancies(self):
        return VacancyDetailPage.objects.live().order_by('-posting_date')
    
    def get_context(self, request, *args, **kwargs):
        context = super(VacanciesPage, self).get_context(
            request, *args, **kwargs)
        
        context['vacancies'] = self.filter_and_paginate_vacancies(request)
        
        return context
    
    class Meta:
        verbose_name = _("Vacancy Page")


class VacancyDocumentBlock(wagtail_blocks.StructBlock):
    title = wagtail_blocks.CharBlock(max_length=255, label=_("Document title"))
    document = DocumentChooserBlock(label=_("Document"))

    class Meta:
        icon = "doc-full"
        label = _("Job description document")


class VacancyDetailPage(MetadataPageMixin, Page):
    template = 'vacancy_detail_page.html'
    parent_page_types = ['vacancies.VacanciesPage']
    subpage_types = []
    
    posting_date = models.DateTimeField(default=timezone.now, verbose_name=_("Date of Posting"))
    duty_station = models.CharField(max_length=100, verbose_name=_("Duty Station"))
    deadline = models.DateTimeField(_("Application Deadline"))
    description = RichTextField(_("Job Description"), blank=True, null=True,
                                features=SUMMARY_RICHTEXT_FEATURES)
    duration = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Duration"))
    document = models.ForeignKey(
        'base.CustomDocumentModel',
        verbose_name=_("Downloadable Job Description Document"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
        help_text=_("Optional downloadable job description document")
    )
    additional_documents = StreamField(
        [("document", VacancyDocumentBlock())],
        blank=True,
        use_json_field=True,
        verbose_name=_("Additional job description documents"),
    )
    
    content_panels = Page.content_panels + [
        FieldPanel('posting_date'),
        FieldPanel('duty_station'),
        FieldPanel('duration'),
        FieldPanel('description'),
        FieldPanel('deadline'),
        FieldPanel('document'),
        FieldPanel('additional_documents'),
    ]
    
    api_fields = [
        APIField('posting_date'),
        APIField('duty_station'),
        APIField('duration'),
        APIField('deadline'),
        APIField('document'),
        APIField('additional_documents'),
        APIField('closed', serializer=BooleanField(source='is_closed')),
    ]
    
    class Meta:
        verbose_name = _("Vacancy Detail Page")
    
    @property
    def item_type(self):
        return "Vacancy"
    
    @cached_property
    def position_title(self):
        return self.title
    
    @cached_property
    def is_new(self):
        difference = (timezone.now() - self.posting_date).days
        if difference < 10:
            return True
        return False
    
    @cached_property
    def days_to_deadline(self):
        today = timezone.now()
        time_delta = (self.deadline - today).days
        
        return time_delta
    
    @property
    def is_closed(self):
        return timezone.now() >= self.deadline
    
    @property
    def listing_summary(self):
        p = get_first_non_empty_p_string(self.description)
        if p:
            # Limit the search meta desc to google's 160 recommended chars
            return truncatechars(p, 160)
        
        return None
    
    def get_meta_image(self):
        meta_image = super().get_meta_image()
        
        if not meta_image:
            meta_image = self.get_parent().specific.get_meta_image()
        
        return meta_image
    
    def get_meta_description(self):
        meta_description = super().get_meta_description()
        
        if not meta_description:
            meta_description = self.listing_summary
        
        return meta_description
