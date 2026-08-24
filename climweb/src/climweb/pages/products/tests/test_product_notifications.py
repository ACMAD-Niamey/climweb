from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from climweb.base.models import Product
from climweb.pages.products.models import (
    ProductNotificationDelivery,
    ProductNotificationEvent,
    ProductSourceImport,
    ProductSubscriber,
    ProductSubscriptionPreference,
)
from climweb.pages.products.product_notifications import (
    deliver_product_notification,
    queue_automatic_product_notifications,
)


class TestProductSubscriptions(TestCase):
    def test_subscription_page_uses_product_alert_layout(self):
        response = self.client.get(reverse("product_subscription"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse("product_subscription"), "/subscribe/")
        self.assertContains(response, "Get Product Updates")
        self.assertContains(response, "Our Products")
        self.assertContains(response, "Sector")
        self.assertContains(response, "Type of Organisation")
        self.assertContains(response, "Agriculture")
        self.assertContains(response, "Public Sector")
        self.assertContains(response, "Select all")
        self.assertContains(response, "products/css/subscription.css")

    def test_previous_product_subscription_url_redirects_to_main_page(self):
        response = self.client.get(reverse("product_subscription_legacy"))

        self.assertRedirects(response, reverse("product_subscription"))

    @patch(
        "climweb.pages.products.tasks.send_product_subscription_confirmation.delay"
    )
    def test_subscription_is_stored_locally_active(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("product_subscription"),
                {
                    "name": "Forecast User",
                    "email": "USER@example.com",
                    "sector": ProductSubscriber.Sector.RESEARCH,
                    "organization_name": "Test Org",
                    "organization_type": (
                        ProductSubscriber.OrganizationType.ACADEMIC_RESEARCH
                    ),
                    "product_families": ["rainfall", "heat-stress"],
                    "consent": "on",
                },
            )

        self.assertEqual(response.status_code, 200)
        subscriber = ProductSubscriber.objects.get(email="user@example.com")
        self.assertEqual(subscriber.status, ProductSubscriber.STATUS_ACTIVE)
        self.assertEqual(subscriber.sector, ProductSubscriber.Sector.RESEARCH)
        self.assertEqual(subscriber.organization_name, "Test Org")
        self.assertEqual(
            subscriber.organization_type,
            ProductSubscriber.OrganizationType.ACADEMIC_RESEARCH,
        )
        self.assertEqual(
            set(subscriber.preferences.values_list("product_family", flat=True)),
            {"rainfall", "heat-stress"},
        )
        delay.assert_called_once_with(subscriber.pk)

    def test_confirmation_and_unsubscribe_change_local_status(self):
        subscriber = ProductSubscriber.objects.create(email="alerts@example.com")
        ProductSubscriptionPreference.objects.create(
            subscriber=subscriber, product_family="rainfall"
        )

        response = self.client.get(
            reverse(
                "product_subscription_confirm",
                kwargs={"token": subscriber.confirmation_token},
            )
        )
        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertEqual(subscriber.status, ProductSubscriber.STATUS_ACTIVE)

        response = self.client.post(
            reverse(
                "product_subscription_unsubscribe",
                kwargs={"token": subscriber.unsubscribe_token},
            )
        )
        self.assertEqual(response.status_code, 200)
        subscriber.refresh_from_db()
        self.assertEqual(
            subscriber.status, ProductSubscriber.STATUS_UNSUBSCRIBED
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestProductNotifications(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Daily Rainfall Monitoring",
            variable_name="notification-rainfall",
            temporal_resolution="daily",
        )
        cls.source_import = ProductSourceImport.objects.create(
            product=cls.product,
            source_url="https://example.com/rainfall-20260817.jpg",
            source_system="Test source",
            source_published_date=date(2026, 8, 17),
            checksum_sha256="a" * 64,
            status=ProductSourceImport.STATUS_IMPORTED,
        )

    @patch("climweb.pages.products.tasks.send_product_notification.delay")
    def test_automatic_import_queues_new_successful_source_once(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            event_ids = queue_automatic_product_notifications(
                "rainfall", timezone.now() - timedelta(minutes=1)
            )
        self.assertEqual(len(event_ids), 1)
        event = ProductNotificationEvent.objects.get()
        self.assertEqual(
            event.trigger, ProductNotificationEvent.TRIGGER_AUTOMATIC
        )
        delay.assert_called_once_with(event.pk)

        with self.captureOnCommitCallbacks(execute=True):
            duplicate_ids = queue_automatic_product_notifications(
                "rainfall", timezone.now() - timedelta(minutes=1)
            )
        self.assertEqual(duplicate_ids, [])
        self.assertEqual(ProductNotificationEvent.objects.count(), 1)

    @patch("climweb.pages.products.tasks.send_product_notification.delay")
    def test_automatic_import_queues_only_latest_touched_source(self, delay):
        started_at = timezone.now()
        historical = ProductSourceImport.objects.create(
            product=self.product,
            source_url="https://example.com/rainfall-20210104.jpg",
            source_system="Test source",
            source_published_date=date(2021, 1, 4),
            checksum_sha256="b" * 64,
            status=ProductSourceImport.STATUS_IMPORTED,
        )
        latest = ProductSourceImport.objects.create(
            product=self.product,
            source_url="https://example.com/rainfall-20260818.jpg",
            source_system="Test source",
            source_published_date=date(2026, 8, 18),
            checksum_sha256="c" * 64,
            status=ProductSourceImport.STATUS_IMPORTED,
        )

        with self.captureOnCommitCallbacks(execute=True):
            event_ids = queue_automatic_product_notifications(
                "rainfall", started_at
            )

        event = ProductNotificationEvent.objects.get(pk=event_ids[0])
        self.assertEqual(event.source_import, latest)
        self.assertFalse(
            ProductNotificationEvent.objects.filter(source_import=historical).exists()
        )
        delay.assert_called_once_with(event.pk)

    @patch("climweb.pages.products.tasks.send_product_notification.delay")
    def test_automatic_import_ignores_historical_backfill(self, delay):
        started_at = timezone.now()
        ProductSourceImport.objects.create(
            product=self.product,
            source_url="https://example.com/rainfall-20240104.jpg",
            source_system="Test source",
            source_published_date=date(2024, 1, 4),
            checksum_sha256="d" * 64,
            status=ProductSourceImport.STATUS_IMPORTED,
        )

        with self.captureOnCommitCallbacks(execute=True):
            event_ids = queue_automatic_product_notifications(
                "rainfall", started_at
            )

        self.assertEqual(event_ids, [])
        self.assertFalse(ProductNotificationEvent.objects.exists())
        delay.assert_not_called()

    def test_delivery_only_targets_active_matching_subscribers(self):
        active = ProductSubscriber.objects.create(
            email="active@example.com", status=ProductSubscriber.STATUS_ACTIVE
        )
        ProductSubscriptionPreference.objects.create(
            subscriber=active, product_family="rainfall"
        )
        pending = ProductSubscriber.objects.create(email="pending@example.com")
        ProductSubscriptionPreference.objects.create(
            subscriber=pending, product_family="rainfall"
        )
        other = ProductSubscriber.objects.create(
            email="other@example.com", status=ProductSubscriber.STATUS_ACTIVE
        )
        ProductSubscriptionPreference.objects.create(
            subscriber=other, product_family="heat-stress"
        )
        event = ProductNotificationEvent.objects.create(
            product_family="rainfall",
            source_import=self.source_import,
            trigger=ProductNotificationEvent.TRIGGER_MANUAL,
        )

        deliver_product_notification(event.pk)

        event.refresh_from_db()
        self.assertEqual(event.status, ProductNotificationEvent.STATUS_SENT)
        self.assertEqual(event.recipient_count, 1)
        self.assertEqual(event.sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["active@example.com"])

    @patch("climweb.pages.products.tasks.send_product_notification.delay")
    def test_dashboard_can_queue_latest_product_notification(self, delay):
        user = get_user_model().objects.create_superuser(
            username="notification-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse(
                    "product_import_family", kwargs={"family_key": "rainfall"}
                ),
                {"action": "send_latest_notification"},
            )

        self.assertRedirects(
            response,
            reverse("product_import_family", kwargs={"family_key": "rainfall"}),
        )
        event = ProductNotificationEvent.objects.get()
        self.assertEqual(event.trigger, ProductNotificationEvent.TRIGGER_MANUAL)
        self.assertEqual(event.requested_by, user)
        delay.assert_called_once_with(event.pk)


class TestProductSubscriberDashboard(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active = ProductSubscriber.objects.create(
            name="Alice Forecast",
            email="alice@example.com",
            status=ProductSubscriber.STATUS_ACTIVE,
            confirmed_at=timezone.now(),
        )
        ProductSubscriptionPreference.objects.create(
            subscriber=cls.active,
            product_family="rainfall",
        )
        cls.pending = ProductSubscriber.objects.create(
            name="Bob Climate",
            email="bob@example.com",
            status=ProductSubscriber.STATUS_PENDING,
        )
        ProductSubscriptionPreference.objects.create(
            subscriber=cls.pending,
            product_family="heat-stress",
        )

        product = Product.objects.create(
            name="Daily Rainfall Monitoring",
            variable_name="subscriber-dashboard-rainfall",
            temporal_resolution="daily",
        )
        source_import = ProductSourceImport.objects.create(
            product=product,
            source_url="https://example.com/rainfall-20260817.jpg",
            source_system="Test source",
            source_published_date=date(2026, 8, 17),
            checksum_sha256="b" * 64,
            status=ProductSourceImport.STATUS_IMPORTED,
        )
        event = ProductNotificationEvent.objects.create(
            product_family="rainfall",
            source_import=source_import,
            trigger=ProductNotificationEvent.TRIGGER_AUTOMATIC,
            status=ProductNotificationEvent.STATUS_SENT,
            recipient_count=1,
            sent_count=1,
            finished_at=timezone.now(),
        )
        ProductNotificationDelivery.objects.create(
            event=event,
            subscriber=cls.active,
            status=ProductNotificationDelivery.STATUS_SENT,
            sent_at=timezone.now(),
        )

    def test_dashboard_requires_admin_access(self):
        response = self.client.get(reverse("product_subscriber_dashboard"))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_tracks_subscribers_and_recent_notifications(self):
        user = get_user_model().objects.create_superuser(
            username="subscriber-admin",
            email="subscriber-admin@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("product_subscriber_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email Subscribers")
        self.assertContains(response, "alice@example.com")
        self.assertContains(response, "bob@example.com")
        self.assertContains(response, "Daily Rainfall Monitoring")
        self.assertContains(response, "Recent notification activity")
        self.assertEqual(response.context["total_subscribers"], 2)
        self.assertEqual(response.context["status_counts"]["active"], 1)
        active_row = next(
            subscriber
            for subscriber in response.context["subscriber_page"]
            if subscriber.pk == self.active.pk
        )
        self.assertEqual(active_row.sent_delivery_count, 1)

    def test_dashboard_filters_by_search_status_and_product(self):
        user = get_user_model().objects.create_superuser(
            username="subscriber-filter-admin",
            email="subscriber-filter-admin@example.com",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("product_subscriber_dashboard"),
            {
                "q": "alice",
                "status": ProductSubscriber.STATUS_ACTIVE,
                "product": "rainfall",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alice@example.com")
        self.assertNotContains(response, "bob@example.com")
        self.assertEqual(response.context["subscriber_page"].paginator.count, 1)
