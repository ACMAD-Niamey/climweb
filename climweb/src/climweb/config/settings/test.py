from .dev import *

# Tests must not share the dev/prod Redis cache. base.py's CACHES points at
# the same Redis instance the running dev server uses, and Wagtail caches
# things like Site.get_site_root_paths() under fixed keys there - if tests
# write to it using the disposable test database's page tree, that (now
# wrong) data leaks into the live dev site's navigation for up to the cache's
# TIMEOUT, well after the test database is gone.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
