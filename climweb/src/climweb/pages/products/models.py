import uuid

from adminboundarymanager.models import AdminBoundarySettings
from django import forms
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils import timezone
from django.utils.dates import MONTHS
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from geomanager.models import RasterFileLayer
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import TaggedItemBase
from wagtail import blocks
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.admin.panels import (FieldPanel, MultiFieldPanel)
from wagtail.api.v2.utils import get_full_url
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.rich_text import RichText
from wagtail.snippets.models import register_snippet
from climweb.base.choosers import register_searchable_chooser

from climweb.base.blocks import UUIDModelChooserBlock
from climweb.base.mixins import MetadataPageMixin
from climweb.base.models import Product, ProductItemType
from climweb.base.models import ServiceCategory, AbstractIntroPage
from climweb.base.utils import paginate, query_param_to_list, get_first_non_empty_p_string
from climweb.pages.publications.models import PageView
from .blocks import (
    ProductItemImageContentBlock,
    ProductItemDocumentContentBlock,
    ProductItemGifContentBlock,
    ProductItemStreamContentBlock
)

from climweb.base.models.abstracts import AbstractBannerPage

class ProductIndexPage(AbstractBannerPage):
    parent_page_types = ['home.HomePage']
    subpage_types = [
        'products.ProductPage',
        'products.SubNationalProductsLandingPage'
    ]
    template = "subpages_listing.html"
    
    max_count = 1
    is_products_index = True
    
    listing_heading = models.CharField(max_length=255, default="Explore our Products",
                                       verbose_name=_("Products listing Heading"))
    group_menu_items_by_service = models.BooleanField(default=True, verbose_name=_("Group menu items by service"))
    
    content_panels = AbstractBannerPage.content_panels + [
        FieldPanel("listing_heading"),
        FieldPanel("group_menu_items_by_service")
    ]
    
    class Meta:
        verbose_name = _('Product Index Page')
        verbose_name_plural = _('Product Index Pages')
    
    @cached_property
    def service_categories(self):
        product_service = set(ProductPage.objects.all().live().values_list('service', flat=True))
        
        unique_services = ServiceCategory.objects.filter(id__in=list(product_service))
        
        return unique_services
    
    @cached_property
    def products_by_service(self):
        services = self.service_categories
        
        products_by_service = {}
        for service in services:
            products_by_service[service] = ProductPage.objects.filter(service=service).live()
        
        return products_by_service
    
    def get_menu_product_pages(self):
        products = ProductPage.objects.live().descendant_of(self).order_by('menu_order')
        subnational_products = SubNationalProductPage.objects.live().descendant_of(self).order_by('menu_order')
        
        return list(products) + list(subnational_products)
    

    
    def get_meta_description(self):
        meta_description = super().get_meta_description()
        
        if not meta_description:
            parent = self.get_parent()
            # get from homepage
            if hasattr(parent, 'get_meta_description'):
                meta_description = parent.get_meta_description()
        
        return meta_description


class LayerBlock(blocks.StructBlock):
    geomanager_layer = UUIDModelChooserBlock(RasterFileLayer)
    product_type = blocks.ChoiceBlock(required=False, choices=[])


class ProductPageForm(WagtailAdminPageForm):
    class Media:
        js = ("products/js/product_page_conditional.js",)


class BaseProductPage(AbstractIntroPage):
    base_form_class = ProductPageForm
    
    template = 'products/product_index.html'
    ajax_template = 'product_list_include.html'
    parent_page_types = ['products.ProductIndexPage']
    subpage_types = ['products.ProductItemPage']
    show_in_menus_default = True
    
    service = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, verbose_name=_("Primary Service"))
    
    products_per_page = models.PositiveIntegerField(default=6, validators=[
        MinValueValidator(6),
        MaxValueValidator(20),
    ], help_text=_("How many of this products should be visible on the landing page filter section ?"),
                                                    verbose_name=_("Products per page"))
    
    default_listing_thumbnail = models.ForeignKey(
        'wagtailimages.Image',
        verbose_name=_("Default Listing Thumbnail"),
        help_text=_("An image that will be used as a thumbnail for in the products listing, "
                    "if no image can be extracted from product items"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    menu_order = models.PositiveIntegerField(default=0, verbose_name=_("Menu Order"))
    
    class Meta:
        abstract = True
    
    @cached_property
    def listing_image(self):
        if self.introduction_image:
            return self.introduction_image

        for product_item in self.all_products:
            listing_image = product_item.products_listing_image
            if listing_image:
                return listing_image

        if self.default_listing_thumbnail:
            return self.default_listing_thumbnail
        return None
    
    @cached_property
    def filters(self):
        years = self.all_products.dates("productitempage__date", "year")
        return {'year': years, 'month': MONTHS}
    
    @cached_property
    def all_products(self):
        product_items = self.get_children().specific().live().order_by('-productitempage__date')
        # Return the related items
        return product_items
    
    def filter_products(self, request):
        products = self.all_products
        
        years = query_param_to_list(request.GET.get("year"), as_int=True)
        months = query_param_to_list(request.GET.get("month"), as_int=True)
        
        filters = models.Q()
        
        if years:
            filters &= models.Q(productitempage__date__year__in=years)
        if months:
            filters &= models.Q(productitempage__date__month__in=months)
        
        return products.filter(filters)
    
    def filter_and_paginate_products(self, request):
        page = request.GET.get('page')
        
        filtered_products = self.filter_products(request)
        
        paginated_products = paginate(filtered_products, page, self.products_per_page)
        
        return paginated_products
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        context['products'] = self.filter_and_paginate_products(request)
        
        return context


class ProductPage(BaseProductPage):
    template = 'products/product_index.html'
    parent_page_types = ['products.ProductIndexPage']
    subpage_types = ['products.ProductItemPage']
    show_in_menus_default = True
    
    product = models.OneToOneField(Product, on_delete=models.PROTECT, verbose_name=_("Product"))
    other_services = ParentalManyToManyField(ServiceCategory, blank=True, verbose_name=_("Other relevant Services"),
                                             related_name="other_services")
    is_featured_on_homepage = models.BooleanField(
        default=False,
        verbose_name=_("Feature on homepage"),
        help_text=_("Show this product in the homepage Featured Products card"),
    )
    homepage_feature_order = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Homepage feature order"),
        help_text=_(
            "Controls the order of products selected for the homepage. "
            "Lower numbers appear first."
        ),
    )
    map_layers = StreamField([
        ('layers', LayerBlock(label="Layer"))
    ], blank=True, null=True, use_json_field=True, verbose_name=_("Map Layers"))
    
    content_panels = Page.content_panels + [
        FieldPanel('service'),
        FieldPanel('other_services', widget=forms.CheckboxSelectMultiple),
        FieldPanel('product'),
        *AbstractIntroPage.content_panels,
        MultiFieldPanel(
            [
                FieldPanel('products_per_page'),
                FieldPanel('default_listing_thumbnail'),
                FieldPanel('menu_order'),
                FieldPanel('is_featured_on_homepage'),
                FieldPanel('homepage_feature_order'),
            ],
            heading=_("Other settings"),
        ),
    ]

    class Meta:
        verbose_name = _('National Product Page')
        verbose_name_plural = _('National Product Pages')
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        abm_settings = AdminBoundarySettings.for_request(request)
        abm_extents = abm_settings.combined_countries_bounds
        boundary_tiles_url = get_full_url(request, abm_settings.boundary_tiles_url)
        
        context.update({
            "bounds": abm_extents,
            "boundary_tiles_url": boundary_tiles_url
        })
        
        if self.map_layers:
            try:
                context["datasetsurl"] = get_full_url(request, (reverse("datasets-list")))
                context["layertimestampsurl"] = get_full_url(request, reverse("layerrasterfile-list"))
            except Exception:
                pass
        
        return context
    
    @cached_property
    def map_layers_list(self):
        layers = []
        for map_layer in self.map_layers:
            layer = map_layer.value.get("geomanager_layer")
            product_type = map_layer.value.get("product_type")
            
            if product_type:
                product_type = ProductItemType.objects.filter(pk=product_type).first()
            layers.append({
                "layer": layer,
                "product_type": product_type
            })
        return layers
    
    @property
    def view_count(self):
        """Get the total number of views for this product page"""
        try:
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(self)
            return PageView.objects.filter(content_type=content_type, object_id=self.pk).count()
        except Exception:
            return 0
    
    def record_view(self, request=None, **kwargs):
        """Record a view of this product page"""
        try:
            view_record = PageView.record_view(self, request=request, **kwargs)
            return view_record
        except Exception as e:
            print(f"Error in record_view for ProductPage: {e}")
            return None

    def serve(self, request, *args, **kwargs):
        """Override serve to record page views when the product page is accessed"""
        try:
            # Only record views for GET requests from non-authenticated users and not in preview mode
            if (request.method == 'GET' and 
                not request.user.is_authenticated and 
                not getattr(request, 'is_preview', False)):
                
                # Check if internal tracking is enabled in settings
                from climweb.base.models import IntegrationSettings
                try:
                    integration_settings = IntegrationSettings.for_request(request)
                    if integration_settings and integration_settings.track_internally:
                        self.record_view(request)
                except Exception:
                    # If settings are not available, don't track views
                    pass
        except Exception as e:
            # Log the error for debugging but continue serving the page
            print(f"Error recording page view: {e}")
        
        return super().serve(request, *args, **kwargs)


register_searchable_chooser(RasterFileLayer)


class ProductPageTag(TaggedItemBase):
    content_object = ParentalKey('products.ProductItemPage', on_delete=models.CASCADE, related_name='product_tags',
                                 verbose_name=_("Product Tag"))


class ProductItemPageForm(WagtailAdminPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        parent_page = kwargs.get("parent_page")
        products_item_types = parent_page.specific.product.product_item_types
        
        products_field = self.fields.get("products")
        
        for product_content_type, block in products_field.block.child_blocks.items():
            for key, val in block.child_blocks.items():
                if key == "product_type":
                    label = val.label or key
                    products_field.block.child_blocks[product_content_type].child_blocks[key] = blocks.ChoiceBlock(
                        choices=products_item_types)
                    products_field.block.child_blocks[product_content_type].child_blocks[key].name = "product_type"
                    products_field.block.child_blocks[product_content_type].child_blocks[key].label = label
        
        self.fields["products"] = products_field


class ProductItemPage(MetadataPageMixin, Page):
    template = 'products/product_detail.html'
    parent_page_types = ['products.ProductPage', 'products.SubNationalProductPage']
    subpage_types = []
    base_form_class = ProductItemPageForm
    
    date = models.DateField(default=timezone.now, verbose_name=_("Effective from"),
                            help_text=_("The first day when products added below become effective"))
    valid_until = models.DateField(blank=True, null=True, verbose_name=_("Effective until"),
                                   help_text=_("The last day when products added below remain effective. "
                                               "Leave blank if not applicable"))
    products = StreamField([
        ("image_product", ProductItemImageContentBlock(label="Map/Image Product")),
        ("gif_product", ProductItemGifContentBlock(label="GIF Product")),
        ("document_product", ProductItemDocumentContentBlock(label="Document/Bulletin Product")),
        ("content_block", ProductItemStreamContentBlock(label="Text/Tabular Product"))
    ], use_json_field=True)
    
    content_panels = Page.content_panels + [
        FieldPanel("date"),
        FieldPanel("valid_until"),
        FieldPanel("products")
    ]
    
    class Meta:
        verbose_name = _("Product Item")
    
    def __str__(self):
        parent_page = self.get_parent().specific
        return f"{parent_page.title} - {self.title}"
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)

        parent_page = self.get_parent().specific
        categories = list(parent_page.product.categories.all())

        # build a complete map: item_type_id → list of category ids
        # (one item type can belong to multiple categories)
        item_type_to_categories = {}
        for category in categories:
            for item_type in category.product_item_types.all():
                if item_type.pk not in item_type_to_categories:
                    item_type_to_categories[item_type.pk] = []
                item_type_to_categories[item_type.pk].append(category.id)

        product_categories = {}
        products_dict = {}

        for product in self.products:
            item_type = product.value.product_item_type()

            # find which category this item type belongs to
            category_ids = item_type_to_categories.get(item_type.pk, [])
            # use the first matching category — or None
            category_id = category_ids[0] if category_ids else None

            # composite key guarantees uniqueness across categories
            composite_key = f"{category_id}-{item_type.pk}" if category_id else str(item_type.pk)

            if composite_key not in products_dict:
                products_dict[composite_key] = {
                    "item_type": item_type,
                    "category_id": category_id,
                    "products": [],
                }
            products_dict[composite_key]["products"].append(product)

            # collect categories that have products
            if category_id and category_id not in product_categories:
                for cat in categories:
                    if cat.id == category_id:
                        product_categories[cat.id] = cat
                        break

        # sort each group by date
        for key in products_dict:
            products_dict[key]["products"].sort(key=lambda r: r.value.get("date"))

        context.update({
            "products": products_dict,
            "categories": product_categories,
        })

        return context
    
    @cached_property
    def product_category(self):
        parent = self.get_parent().specific
        return parent.product.name
    
    @property
    def products_listing_image(self):
        products = self.products
        for product in products:
            if product.value.p_image:
                return product.value.p_image
        
        return None
    
    @property
    def product_listing_description(self):
        products = self.products
        for product in products:
            if product.value.description:
                return product.value.description
        
        return None
    
    def get_meta_image(self):
        meta_image = super().get_meta_image()
        
        if not meta_image:
            meta_image = self.products_listing_image
        
        if not meta_image:
            parent = self.get_parent()
            if hasattr(parent, 'get_meta_image'):
                meta_image = parent.get_meta_image()
        
        return meta_image
    
    @property
    def listing_summary(self):
        html_description = self.product_listing_description
        if html_description:
            if isinstance(html_description, RichText):
                html = html_description.source
                p = get_first_non_empty_p_string(html)
                if p:
                    # Limit the search meta desc to google's 160 recommended chars
                    return truncatechars(p, 160)
        return None
    
    def get_meta_description(self):
        meta_description = super().get_meta_description()
        
        if not meta_description:
            # try getting from the description of the first product item
            if self.listing_summary:
                meta_description = self.listing_summary
        
        if not meta_description:
            parent = self.get_parent()
            if hasattr(parent, 'get_meta_description'):
                meta_description = parent.get_meta_description()
        
        return meta_description
    
    @property
    def view_count(self):
        """Get the total number of views for this product item page"""
        try:
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(self)
            return PageView.objects.filter(content_type=content_type, object_id=self.pk).count()
        except Exception:
            return 0
    
    def record_view(self, request=None, **kwargs):
        """Record a view of this product item page"""
        try:
            view_record = PageView.record_view(self, request=request, **kwargs)
            return view_record
        except Exception as e:
            print(f"Error in record_view for ProductItemPage: {e}")
            return None

    def serve(self, request, *args, **kwargs):
        """Override serve to record page views when the product item page is accessed"""
        try:
            # Only record views for GET requests from non-authenticated users and not in preview mode
            if (request.method == 'GET' and 
                not request.user.is_authenticated and 
                not getattr(request, 'is_preview', False)):
                
                # Check if internal tracking is enabled in settings
                from climweb.base.models import IntegrationSettings
                try:
                    integration_settings = IntegrationSettings.for_request(request)
                    if integration_settings and integration_settings.track_internally:
                        self.record_view(request)
                except Exception:
                    # If settings are not available, don't track views
                    pass
        except Exception as e:
            # Log the error for debugging but continue serving the page
            print(f"Error recording page view: {e}")
        
        return super().serve(request, *args, **kwargs)


class ProductIngestedFile(models.Model):
    """Tracks files that have already been auto-ingested to prevent duplicates."""
    product = models.ForeignKey(
        'base.Product',
        on_delete=models.CASCADE,
        related_name='ingested_files',
        verbose_name=_("Product"),
    )
    file_path = models.CharField(max_length=1000, verbose_name=_("File Path"))
    file_mtime = models.FloatField(verbose_name=_("File Modification Time"))
    product_item_page = models.ForeignKey(
        ProductItemPage,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ingested_files',
        verbose_name=_("Product Item Page"),
    )
    ingested_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ingested At"))

    class Meta:
        unique_together = [('product', 'file_path')]
        verbose_name = _("Product Ingested File")
        verbose_name_plural = _("Product Ingested Files")

    def __str__(self):
        return self.file_path


class ProductSourceImport(models.Model):
    """Provenance for a product item imported from an external catalogue."""

    STATUS_IMPORTED = 'imported'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_IMPORTED, _("Imported")),
        (STATUS_FAILED, _("Failed")),
    ]

    product = models.ForeignKey(
        'base.Product',
        on_delete=models.CASCADE,
        related_name='source_imports',
        verbose_name=_("Product"),
    )
    source_url = models.URLField(max_length=1000, unique=True, verbose_name=_("Source URL"))
    source_system = models.CharField(max_length=255, verbose_name=_("Source System"))
    source_published_date = models.DateField(verbose_name=_("Source Published Date"))
    checksum_sha256 = models.CharField(max_length=64, verbose_name=_("SHA-256 Checksum"))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IMPORTED,
        verbose_name=_("Status"),
    )
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    attempt_count = models.PositiveIntegerField(default=1, verbose_name=_("Attempt Count"))
    document = models.ForeignKey(
        'base.CustomDocumentModel',
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_source_imports',
        verbose_name=_("Document"),
    )
    image = models.ForeignKey(
        'wagtailimages.Image',
        on_delete=models.SET_NULL,
        null=True,
        related_name='product_source_imports',
        verbose_name=_("Image"),
    )
    product_item_page = models.ForeignKey(
        ProductItemPage,
        on_delete=models.SET_NULL,
        null=True,
        related_name='source_imports',
        verbose_name=_("Product Item Page"),
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-source_published_date', '-imported_at']
        verbose_name = _("Product Source Import")
        verbose_name_plural = _("Product Source Imports")

    def __str__(self):
        return f"{self.product} — {self.source_published_date}"


class ProductImportRun(models.Model):
    """A dashboard-requested historical product import or preview."""

    MODE_PREVIEW = 'preview'
    MODE_IMPORT = 'import'
    MODE_CHOICES = [
        (MODE_PREVIEW, _("Preview")),
        (MODE_IMPORT, _("Import")),
    ]

    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_CANCELLING = 'cancelling'
    STATUS_CANCELLED = 'cancelled'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_QUEUED, _("Queued")),
        (STATUS_RUNNING, _("Running")),
        (STATUS_CANCELLING, _("Stopping")),
        (STATUS_CANCELLED, _("Stopped")),
        (STATUS_SUCCEEDED, _("Succeeded")),
        (STATUS_FAILED, _("Failed")),
    ]

    product_family = models.CharField(max_length=80, verbose_name=_("Product Family"))
    mode = models.CharField(max_length=20, choices=MODE_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
    )
    from_date = models.DateField(verbose_name=_("From Date"))
    to_date = models.DateField(verbose_name=_("To Date"))
    limit = models.PositiveIntegerField(default=100)
    refresh_existing = models.BooleanField(default=False)
    retry_failures = models.BooleanField(default=False)
    cancel_requested = models.BooleanField(default=False)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_import_runs',
    )
    task_id = models.CharField(max_length=255, blank=True)
    output = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    progress_percent = models.PositiveSmallIntegerField(default=0)
    total_items = models.PositiveIntegerField(default=0)
    processed_items = models.PositiveIntegerField(default=0)
    imported_items = models.PositiveIntegerField(default=0)
    failed_items = models.PositiveIntegerField(default=0)
    skipped_items = models.PositiveIntegerField(default=0)
    current_phase = models.CharField(max_length=255, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = _("Product Import Run")
        verbose_name_plural = _("Product Import Runs")

    def __str__(self):
        return (
            f"{self.product_family}: {self.from_date}–{self.to_date} "
            f"({self.status})"
        )

    @property
    def product_family_label(self):
        from climweb.pages.products.import_registry import get_product_import_definition

        definition = get_product_import_definition(self.product_family)
        return definition["label"] if definition else self.product_family


class ProductImportSchedule(models.Model):
    """Dashboard-managed automatic import interval for a product family."""

    product_family = models.CharField(
        max_length=80,
        unique=True,
        verbose_name=_("Product Family"),
    )
    interval_hours = models.PositiveIntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(720)],
        verbose_name=_("Interval Hours"),
    )
    enabled_override = models.BooleanField(
        null=True,
        blank=True,
        verbose_name=_("Enabled Override"),
        help_text=_("Leave empty to use the deployment configuration."),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_import_schedules',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_family']
        verbose_name = _("Product Import Schedule")
        verbose_name_plural = _("Product Import Schedules")

    def __str__(self):
        return f"{self.product_family}: every {self.interval_hours} hour(s)"


class ProductImportSourceConfig(models.Model):
    """Dashboard-managed source and discovery schema for a product importer."""

    TYPE_HTML_ARCHIVE = 'html_archive'
    TYPE_THREDDS_CATALOG = 'thredds_catalog'
    TYPE_WORDPRESS_API = 'wordpress_api'
    SOURCE_TYPE_CHOICES = [
        (TYPE_HTML_ARCHIVE, _("HTML archive or directory listing")),
        (TYPE_THREDDS_CATALOG, _("THREDDS XML catalogue")),
        (TYPE_WORDPRESS_API, _("WordPress media API")),
    ]

    product_family = models.CharField(
        max_length=80,
        unique=True,
        verbose_name=_("Product Family"),
    )
    source_type = models.CharField(
        max_length=40,
        choices=SOURCE_TYPE_CHOICES,
        default=TYPE_HTML_ARCHIVE,
        verbose_name=_("Source Type"),
    )
    source_url = models.URLField(max_length=1000, verbose_name=_("Source URL"))
    source_system = models.CharField(
        max_length=255,
        verbose_name=_("Source Name"),
    )
    allowed_extensions = models.JSONField(default=list)
    filename_pattern = models.TextField(verbose_name=_("Filename Pattern"))
    date_format = models.CharField(
        max_length=80,
        default='%Y%m%d',
        verbose_name=_("Date Format"),
    )
    history_url_pattern = models.TextField(
        blank=True,
        verbose_name=_("Historical Archive Pattern"),
    )
    request_headers = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_import_source_configs',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product_family']
        verbose_name = _("Product Import Source Configuration")
        verbose_name_plural = _("Product Import Source Configurations")

    def __str__(self):
        return f"{self.product_family}: {self.source_url}"


class ConfiguredProductImporter(models.Model):
    """A safe, dashboard-created importer for a file-based product."""

    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_ACTIVE, _("Active")),
        (STATUS_ARCHIVED, _("Archived")),
    ]

    key = models.SlugField(
        max_length=80,
        unique=True,
        verbose_name=_("Importer Key"),
        help_text=_("Stable identifier used by import runs and schedules."),
    )
    label = models.CharField(max_length=255, verbose_name=_("Importer Name"))
    product_page = models.ForeignKey(
        'products.ProductPage',
        on_delete=models.PROTECT,
        related_name='configured_importers',
        verbose_name=_("Destination Product Page"),
    )
    product_item_type = models.ForeignKey(
        'base.ProductItemType',
        on_delete=models.PROTECT,
        related_name='configured_importers',
        verbose_name=_("Destination Product Type"),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    default_interval_hours = models.PositiveIntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(720)],
        verbose_name=_("Default Interval Hours"),
    )
    default_source_config = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configured_product_importers',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['label']
        verbose_name = _("Configured Product Importer")
        verbose_name_plural = _("Configured Product Importers")

    def __str__(self):
        return self.label


class ConfiguredProductImporterAuditEvent(models.Model):
    """Immutable lifecycle history for a dashboard-created importer."""

    ACTION_CREATED = 'created'
    ACTION_UPDATED = 'updated'
    ACTION_ARCHIVED = 'archived'
    ACTION_RESTORED = 'restored'
    ACTION_ENABLED = 'enabled'
    ACTION_DISABLED = 'disabled'
    ACTION_SOURCE_UPDATED = 'source_updated'
    ACTION_SCHEDULE_UPDATED = 'schedule_updated'
    ACTION_CHOICES = [
        (ACTION_CREATED, _("Created")),
        (ACTION_UPDATED, _("Updated")),
        (ACTION_ARCHIVED, _("Archived")),
        (ACTION_RESTORED, _("Restored")),
        (ACTION_ENABLED, _("Enabled")),
        (ACTION_DISABLED, _("Disabled")),
        (ACTION_SOURCE_UPDATED, _("Source updated")),
        (ACTION_SCHEDULE_UPDATED, _("Schedule updated")),
    ]

    importer = models.ForeignKey(
        ConfiguredProductImporter,
        on_delete=models.CASCADE,
        related_name='audit_events',
    )
    action = models.CharField(max_length=40, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configured_importer_audit_events',
    )
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = _("Configured Product Importer Audit Event")
        verbose_name_plural = _("Configured Product Importer Audit Events")

    def __str__(self):
        return f"{self.importer}: {self.get_action_display()}"


@register_snippet
class ProductSubscriber(models.Model):
    """A locally owned subscriber with explicit product preferences."""

    class Sector(models.TextChoices):
        AGRICULTURE = "Agriculture", _("Agriculture")
        AVIATION = "Aviation", _("Aviation")
        MARINE = "Marine", _("Marine")
        MEDIA = "Media", _("Media")
        ENVIRONMENT = "Environment", _("Environment")
        TOURISM = "Tourism", _("Tourism")
        SECURITY = "Security", _("Security")
        CIVIL_PROTECTION = "Civil Protection", _("Civil Protection")
        TELECOMMUNICATION = "Telecommunication", _("Telecommunication")
        HEALTH = "Health", _("Health")
        BANKING_FINANCE = "Banking and Finance", _("Banking and Finance")
        RESEARCH = "Research", _("Research")
        WATER_SANITATION = "Water and Sanitation", _("Water and Sanitation")
        OTHERS = "Others", _("Others")

    class OrganizationType(models.TextChoices):
        PUBLIC_SECTOR = "Public Sector", _("Public Sector")
        INTERGOVERNMENTAL = (
            "Intergovernmental Organisation",
            _("Intergovernmental Organisation"),
        )
        PRIVATE_SECTOR = "Private Sector", _("Private Sector")
        ACADEMIC_RESEARCH = "Academic/Research", _("Academic/Research")
        MEDIA = "Media", _("Media")
        YOUTH = "Youth", _("Youth")
        DONOR_FINANCE = (
            "Donor/Finance institutions",
            _("Donor/Finance institutions"),
        )
        NGO = (
            "Non Governmental Organisation (NGO)",
            _("Non Governmental Organisation (NGO)"),
        )
        OTHERS = "Others", _("Others")

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_UNSUBSCRIBED = "unsubscribed"
    STATUS_BOUNCED = "bounced"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_ACTIVE, _("Active")),
        (STATUS_UNSUBSCRIBED, _("Unsubscribed")),
        (STATUS_BOUNCED, _("Bounced")),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    sector = models.CharField(
        max_length=80,
        choices=Sector.choices,
        blank=True,
    )
    organization_type = models.CharField(
        max_length=100,
        choices=OrganizationType.choices,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True)
    consented_at = models.DateTimeField(default=timezone.now)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    consent_ip = models.GenericIPAddressField(null=True, blank=True)
    consent_user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    panels = [
        FieldPanel("email"),
        FieldPanel("name"),
        FieldPanel("sector"),
        FieldPanel("organization_type"),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["email"]
        verbose_name = _("Product subscriber")
        verbose_name_plural = _("Product subscribers")

    def __str__(self):
        return self.email


class ProductSubscriptionPreference(models.Model):
    subscriber = models.ForeignKey(
        ProductSubscriber,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    product_family = models.SlugField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["product_family"]
        constraints = [
            models.UniqueConstraint(
                fields=["subscriber", "product_family"],
                name="unique_product_subscription_preference",
            )
        ]

    def __str__(self):
        return f"{self.subscriber.email}: {self.product_family}"


@register_snippet
class ProductNotificationEvent(models.Model):
    TRIGGER_AUTOMATIC = "automatic"
    TRIGGER_MANUAL = "manual"
    TRIGGER_CHOICES = [
        (TRIGGER_AUTOMATIC, _("Automatic import")),
        (TRIGGER_MANUAL, _("Dashboard action")),
    ]
    STATUS_QUEUED = "queued"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, _("Queued")),
        (STATUS_SENDING, _("Sending")),
        (STATUS_SENT, _("Sent")),
        (STATUS_FAILED, _("Failed")),
    ]

    product_family = models.SlugField(max_length=80)
    source_import = models.ForeignKey(
        ProductSourceImport,
        on_delete=models.CASCADE,
        related_name="notification_events",
    )
    trigger = models.CharField(max_length=20, choices=TRIGGER_CHOICES)
    automatic_key = models.CharField(
        max_length=120, unique=True, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED
    )
    recipient_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="product_notification_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    panels = [
        FieldPanel("product_family"),
        FieldPanel("source_import"),
        FieldPanel("trigger"),
        FieldPanel("status"),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Product notification event")
        verbose_name_plural = _("Product notification events")

    def __str__(self):
        return f"{self.product_family}: {self.source_import.source_published_date}"


class ProductNotificationDelivery(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, _("Queued")),
        (STATUS_SENT, _("Sent")),
        (STATUS_FAILED, _("Failed")),
    ]

    event = models.ForeignKey(
        ProductNotificationEvent,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    subscriber = models.ForeignKey(
        ProductSubscriber,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED
    )
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["subscriber__email"]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "subscriber"],
                name="unique_product_notification_delivery",
            )
        ]


class SubNationalProductsLandingPage(AbstractIntroPage, Page):
    parent_page_types = ['products.ProductIndexPage']
    subpage_types = ['products.SubNationalProductPage']
    template = "products/subnational/subnational_products_landing.html"
    
    max_count = 1
    
    content_panels = Page.content_panels + AbstractIntroPage.content_panels
    
    class Meta:
        verbose_name = _('Subnational Product Landing Page')
        verbose_name_plural = _('Subnational Product Landing Pages')
    
    @cached_property
    def all_items(self):
        product_pages = self.get_children().specific().live()
        return product_pages
    
    @cached_property
    def filters(self):
        regions = {p.region.id: p.region for p in self.all_items.all()}
        return {'regions': list(regions.values())}
    
    def filter_items(self, request):
        items = self.all_items
        
        regions = query_param_to_list(request.GET.get("region"), as_int=True)
        
        filters = models.Q()
        
        if regions:
            filters &= models.Q(subnationalproductpage__region__id__in=regions)
        
        return items.filter(filters)
    
    def filter_and_paginate_items(self, request):
        page = request.GET.get('page')
        
        filtered_products = self.filter_items(request)
        
        paginated_products = paginate(filtered_products, page, 10)
        
        return paginated_products
    
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        context['items'] = self.filter_and_paginate_items(request)
        
        return context


@register_snippet
class SubNationalRegion(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _('Subnational Region')
        verbose_name_plural = _('Subnational Regions')


class SubNationalProductPage(BaseProductPage):
    template = 'products/subnational/subnational_product_index.html'
    parent_page_types = ['products.SubNationalProductsLandingPage']
    subpage_types = ['products.ProductItemPage']
    show_in_menus_default = False
    
    region = models.ForeignKey(SubNationalRegion, on_delete=models.PROTECT, verbose_name=_("Region"))
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_("Product"))
    
    content_panels = Page.content_panels + [
        FieldPanel('region'),
        FieldPanel('service'),
        FieldPanel('product'),
        *AbstractIntroPage.content_panels,
        MultiFieldPanel(
            [
                FieldPanel('products_per_page'),
                FieldPanel('default_listing_thumbnail'),
                FieldPanel('menu_order'),
            ],
            heading=_("Other settings"),
        ),
    ]
    
    class Meta:
        verbose_name = _('Subnational Product Page')
        verbose_name_plural = _('Subnational Product Pages')
    
    @cached_property
    def listing_summary(self):
        summary = self.get_meta_description()
        return summary
    
    @property
    def view_count(self):
        """Get the total number of views for this subnational product page"""
        try:
            from django.contrib.contenttypes.models import ContentType
            content_type = ContentType.objects.get_for_model(self)
            return PageView.objects.filter(content_type=content_type, object_id=self.pk).count()
        except Exception:
            return 0
    
    def record_view(self, request=None, **kwargs):
        """Record a view of this subnational product page"""
        try:
            view_record = PageView.record_view(self, request=request, **kwargs)
            return view_record
        except Exception as e:
            print(f"Error in record_view for SubNationalProductPage: {e}")
            return None

    def serve(self, request, *args, **kwargs):
        """Override serve to record page views when the subnational product page is accessed"""
        try:
            # Only record views for GET requests from non-authenticated users and not in preview mode
            if (request.method == 'GET' and 
                not request.user.is_authenticated and 
                not getattr(request, 'is_preview', False)):
                
                # Check if internal tracking is enabled in settings
                from climweb.base.models import IntegrationSettings
                try:
                    integration_settings = IntegrationSettings.for_request(request)
                    if integration_settings and integration_settings.track_internally:
                        self.record_view(request)
                except Exception:
                    # If settings are not available, don't track views
                    pass
        except Exception as e:
            # Log the error for debugging but continue serving the page
            print(f"Error recording page view: {e}")
        
        return super().serve(request, *args, **kwargs)
