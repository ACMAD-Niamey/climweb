import hashlib
import re

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


_HTML_ENTITY_RE = re.compile(
    r"&(?:#\d+|#x[0-9a-f]+|[a-z][a-z0-9]+);", re.IGNORECASE
)
_MARKUP_RE = re.compile(r"[<>]|(?:https?://|www\.)", re.IGNORECASE)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_subscription_text(value):
    """Reject markup-like values while allowing normal names and punctuation."""
    if not value:
        return
    if (
        _HTML_ENTITY_RE.search(value)
        or _MARKUP_RE.search(value)
        or _CONTROL_RE.search(value)
    ):
        raise ValidationError(
            _("Enter plain text without HTML entities, markup, or web addresses.")
        )


def validate_honeypot(value):
    if value:
        raise ValidationError(_("Invalid submission."))


def get_client_ip(request):
    """Use django-ipware's configured proxy depth, with a conservative fallback."""
    try:
        from ipware import get_client_ip as ipware_get_client_ip

        client_ip, _ = ipware_get_client_ip(
            request,
            proxy_count=getattr(settings, "AXES_IPWARE_PROXY_COUNT", None),
        )
        if client_ip:
            return client_ip
    except (ImportError, TypeError, ValueError):
        pass
    return request.META.get("REMOTE_ADDR", "")


def subscription_rate_limited(request, email):
    """Bound subscription/email abuse without revealing which limit was reached."""
    window = getattr(settings, "PRODUCT_SUBSCRIPTION_RATE_LIMIT_WINDOW", 3600)
    limits = [
        (
            "email",
            email.lower(),
            getattr(settings, "PRODUCT_SUBSCRIPTION_RATE_LIMIT_EMAIL", 3),
        )
    ]
    client_ip = get_client_ip(request)
    if client_ip:
        limits.append(
            (
                "ip",
                client_ip,
                getattr(settings, "PRODUCT_SUBSCRIPTION_RATE_LIMIT_IP", 10),
            )
        )
    limited = False
    for kind, value, limit in limits:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        key = f"product-subscription:{kind}:{digest}"
        if cache.add(key, 1, timeout=window):
            count = 1
        else:
            try:
                count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=window)
                count = 1
        limited = limited or count > limit
    return limited
