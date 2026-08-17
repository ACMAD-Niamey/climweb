from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-5=&i=f&w$_2=ktbhw43anl(uxgue*-i23r!1uibrh9l7-$q-1#"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

try:
    from .local import *
except ImportError:
    pass

# Disable caching in dev
WAGTAIL_CACHE = env.bool('WAGTAIL_CACHE', default=False)

# reCAPTCHA needs real, domain-registered keys to work at all, so any Wagtail
# form page with a captcha is unsubmittable on a fresh dev checkout whose
# .env leaves RECAPTCHA_PUBLIC_KEY/RECAPTCHA_PRIVATE_KEY blank (the widget
# fails with "Missing required parameters: sitekey" and can never be
# completed). Fall back to Google's own published "always-pass" test keys
# so the widget renders and validates locally - only when the operator
# hasn't set real ones. production.py imports from base.py directly, never
# from this file, so prod always requires real keys with no fallback.
if not RECAPTCHA_PUBLIC_KEY:
    RECAPTCHA_PUBLIC_KEY = "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
if not RECAPTCHA_PRIVATE_KEY:
    RECAPTCHA_PRIVATE_KEY = "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"

# django-recaptcha's own startup check hard-fails (SystemCheckError, not just
# a warning) when it detects these test keys, specifically to stop them ever
# reaching prod by accident - silencing it here is safe precisely because
# this whole fallback is unreachable outside dev.py in the first place.
SILENCED_SYSTEM_CHECKS = list(globals().get('SILENCED_SYSTEM_CHECKS', [])) + [
    'django_recaptcha.recaptcha_test_key_error',
]

INSTALLED_APPS = ["daphne"] + INSTALLED_APPS + ["wagtail.contrib.styleguide"]

SHOW_TOOLBAR_CALLBACK = False
SHOW_COLLAPSED = False

# used in dev with Mac OS
GDAL_LIBRARY_PATH = env.str('GDAL_LIBRARY_PATH', None)
GEOS_LIBRARY_PATH = env.str('GEOS_LIBRARY_PATH', None)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        # Send logs with at least INFO level to the console.
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s][%(process)d][%(levelname)s][%(name)s] %(message)s"
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
