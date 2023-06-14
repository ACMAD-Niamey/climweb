"""
Django settings for nmhs_cms project.

Generated by 'django-admin startproject' using Django 4.0.8.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

import environ

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
)

if os.path.exists(os.path.join(BASE_DIR, '.env')):
    # reading .env file
    environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/


# Application definition

INSTALLED_APPS = [

    # Common
    'core',

    "home",
    "search",
    "services",
    "products",
    "allauth",
    "allauth.account",
    # "product",

    # Organisation pages 
    "organisation_pages.about",
    "organisation_pages.contact",
    "organisation_pages.feedback",
    "organisation_pages.events",
    "organisation_pages.projects",
    "organisation_pages.vacancies",
    "organisation_pages.tenders",

    # Media Pages 
    "media_pages.videos",
    "media_pages.news",
    "media_pages.mediacenter",
    "media_pages.publications",

    "email_marketing",
    "geomanager",
    "surveys",
    # Utility apps & pages 
    'integrations.webicons',
    "wagtailmautic",
    "wagtailzoom",
    "wagtail_adminsortable",
    "wagtailiconchooser",
    "wagtailhumanitarianicons",
    "django_large_image",
    'django_json_widget',
    'django_nextjs',
    "django_filters",

    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    'wagtail.contrib.modeladmin',
    'wagtail.contrib.settings',
    "wagtail.contrib.routable_page",
    'wagtail.contrib.search_promotions',
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",

    "forecast_manager",
    # "layer_manager",
    "site_settings",

    "wagtailsurveyjs",
    "wagtailgeowidget",
    "wagtail_lazyimages",
    "wagtail_color_panel",
    "rest_framework",
    'rest_framework_xml',
    "capeditor",
    "widget_tweaks",
    "captcha",
    'wagtailcaptcha',
    "wagtailmenus",
    "modelcluster",
    "taggit",
    "django_jsonfield_backport",
    "bulma",
    "svg",
    "django_celery_results",
    "mailchimp3",
    "manifest_loader",
    "django_cron",
    "django_deep_translator",
    "wagtailmailchimp",
    "wagtailfontawesomesvg",
    "corsheaders",
    "wagtailmetadata",
]

PO_TRANSLATOR_SERVICE = 'django_deep_translator.services.GoogleTranslatorService'
DEEPL_TRANSLATE_KEY = "testkey"
DEEPL_FREE_API = True
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",

]

ROOT_URLCONF = "nmhs_cms.urls"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                'django.template.context_processors.media',
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "wagtailmenus.context_processors.wagtailmenus",
                'django.template.context_processors.i18n',
                'site_settings.context_processors.theme',
                "django.template.context_processors.debug",
            ],
        },
    },
]

WSGI_APPLICATION = "nmhs_cms.wsgi.application"
WAGTAILLOCALIZE_MACHINE_TRANSLATOR = {
    "CLASS": "wagtail_localize.machine_translators.dummy.DummyTranslator",
}

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    'default': env.db()
}

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework_xml.renderers.XMLRenderer',  # add XMLRenderer
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_xml.parsers.XMLParser',
        'rest_framework.parsers.JSONParser',
    ),
}

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/
LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'French'),
    ('ar', 'Arabic'),
    ('am', 'Amharic'),
    ('sw', 'Swahili'),
]

LANGUAGE_CODE = "en"

WAGTAIL_CONTENT_LANGUAGES = LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'French'),
    ('ar', 'Arabic'),
    ('am', 'Amharic'),
    ('sw', 'Swahili'),
]

WAGTAIL_LANGUAGES_FALLBACK = False
WAGTAILADMIN_PERMITTED_LANGUAGES = [
    ('en', 'English'),
    ('es', 'Español'),
    ('fr', 'French'),
    ('ar', 'Arabic'),
    ('sw', 'Swahili'),
    # ('am', 'Amharic'),

]

LOCALE_PATHS = (
    'home/locale',
    'products/locale',
    'services/locale',
    'organisation_pages/about/locale',
    'organisation_pages/contact/locale',
    'organisation_pages/events/locale',
    'organisation_pages/feedback/locale',
    'organisation_pages/projects/locale',
    'organisation_pages/tenders/locale',
    'organisation_pages/vacancies/locale',
    'media_pages/mediacenter/locale',
    'media_pages/videos/locale',
    'media_pages/publications/locale',
    'media_pages/news/locale',
    'core/locale',
    'forecast_manager/locale',
)

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_LANGUAGES = ('en', 'es')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]

SVG_DIRS = [
    os.path.join(BASE_DIR, 'media/svg'),
]

# ManifestStaticFilesStorage is recommended in production, to prevent outdated
# JavaScript / CSS assets being served from cache (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/4.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
# STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
BASE_PATH = os.getenv("BASE_PATH", '')
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = BASE_PATH + "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = BASE_PATH + "/media/"

# Wagtail settings
# SITE_NAME="nmhs_cms"
WAGTAIL_SITE_NAME = "NMHS Content Management System"

# Search
# https://docs.wagtail.org/en/stable/topics/search/backends.html
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
    }
}

# Base URL to use when referring to full URLs within the Wagtail admin backend -
# e.g. in notification emails. Don't include '/admin' or a trailing slash
WAGTAILADMIN_BASE_URL = "http://example.com"

GEO_WIDGET_DEFAULT_LOCATION = {
    'lng': 23.9479,
    'lat': 4.0310
}
GEO_WIDGET_EMPTY_LOCATION = False

GEO_WIDGET_ZOOM = 3

SUMMARY_RICHTEXT_FEATURES = ["bold", "ul", "ol", "link", "superscript", "subscript"]

# RECAPTCHA Settings
RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY', '')

RECAPTCHA_TESTING = True

ORDERING_FIELD = 'position'
WAGTAILDOCS_DOCUMENT_MODEL = 'core.CustomDocumentModel'

# AUTH STUFF
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_LOGOUT_REDIRECT_URL = '/login/'
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_USERNAME_BLACKLIST = ["admin", "god", "superadmin", "staff"]
ACCOUNT_USERNAME_MIN_LENGTH = 3

# CSRF_TRUSTED_ORIGINS = ['http://*.127.0.0.1', 'http://127.0.0.1','http://*.localhost', 'http://localhost','http://localhost:3031','http://example.com', 'http://localhost:*', 'http://127.0.0.1:3031']
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', cast=None)

SOCIAL_MEDIA_SHARE_CONFIG = {
    'facebook': {"base_url": "https://www.facebook.com/sharer/sharer.php", "link_param": "u"},
    'twitter': {"base_url": "http://twitter.com/share", "text_param": "text", "link_param": "url"}
}

CORS_ORIGIN_ALLOW_ALL = True

NEXTJS_SETTINGS = {
    "nextjs_server_url": os.getenv("NEXTJS_SERVER_URL", "http://localhost:3000"),
}
