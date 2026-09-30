from django.core.management.base import BaseCommand, CommandError

from climweb.base.models import Product, ProductCategory, ProductItemType, ServiceCategory
from climweb.pages.products.models import ElNinoPage, ProductIndexPage


class Command(BaseCommand):
    help = "Create the editable Africa-focused El Niño page and its monthly bulletin product structure."

    def handle(self, *args, **options):
        index = ProductIndexPage.objects.live().first()
        if not index:
            raise CommandError("A live ProductIndexPage was not found")

        existing = ElNinoPage.objects.filter(slug="el-nino-africa").first()
        if existing:
            self.stdout.write(self.style.SUCCESS(f"El Niño page ready: {existing.url}"))
            return

        service = ServiceCategory.objects.filter(name="Seasonal and Long-Range Forecasts").first()
        if not service:
            service = ServiceCategory.objects.filter(name="Regional Climate Center").first()
        if not service:
            raise CommandError("A seasonal forecasting or RCC service category was not found")

        product, _ = Product.objects.get_or_create(
            name="El Niño Bulletin",
            defaults={
                "variable_name": "el-nino-bulletin",
                "temporal_resolution": "monthly",
            },
        )
        category, _ = ProductCategory.objects.get_or_create(
            product=product,
            name="Monthly Bulletin",
            defaults={"icon": "file-pdf", "category_format": "pdf"},
        )
        ProductItemType.objects.get_or_create(
            category=category,
            name="El Niño Bulletin",
            defaults={
                "file_name_convention": "el_nino_bulletin_{yyyy}_{mm}",
                "valid_for_days": 31,
            },
        )

        page = ElNinoPage(
            title="El Niño in Africa",
            slug="el-nino-africa",
            service=service,
            product=product,
            introduction_title="Understanding El Niño and its implications for Africa",
            introduction_text=(
                "<p>El Niño is a warming of the central and eastern tropical Pacific Ocean that can influence "
                "weather patterns around the world. Across Africa, its effects are not uniform: the timing, "
                "strength and location of rainfall and temperature changes differ between regions and seasons.</p>"
                "<p>ACMAD provides a continental view that complements national and regional information, helping "
                "decision-makers understand where conditions may create heightened risks or opportunities.</p>"
            ),
            products_per_page=12,
            search_description=(
                "ACMAD El Niño monitoring, outlooks, impacts and monthly bulletins for Africa."
            ),
        )
        index.add_child(instance=page)
        page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS(f"Created El Niño page: {page.url}"))
