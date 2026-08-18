from django.urls import path
from django.views.generic import RedirectView

from .views import (
    product_subscription_confirm_view,
    product_subscription_preferences_view,
    product_subscription_unsubscribe_view,
    product_subscription_view,
)


urlpatterns = [
    path(
        "subscribe/",
        product_subscription_view,
        name="product_subscription",
    ),
    path(
        "products/subscribe/",
        RedirectView.as_view(
            pattern_name="product_subscription",
            permanent=False,
        ),
        name="product_subscription_legacy",
    ),
    path(
        "products/subscribe/confirm/<uuid:token>/",
        product_subscription_confirm_view,
        name="product_subscription_confirm",
    ),
    path(
        "products/subscribe/preferences/<uuid:token>/",
        product_subscription_preferences_view,
        name="product_subscription_preferences",
    ),
    path(
        "products/subscribe/unsubscribe/<uuid:token>/",
        product_subscription_unsubscribe_view,
        name="product_subscription_unsubscribe",
    ),
]
