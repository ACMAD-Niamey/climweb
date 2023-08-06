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
    EMAIL_USE_TLS=(bool, True),
)

if os.path.exists(os.path.join(BASE_DIR, '.env')):
    # reading .env file
    environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# Application definition
INSTALLED_APPS = [
    "base",
    "pages.home",
    "pages.services",
    "pages.products",
    "pages.mediacenter",
    "pages.news",
    "pages.videos",
    "pages.publications",
    "pages.contact",
    "pages.feedback",
    "pages.events",
    "pages.organisation_pages.organisation",
    "pages.organisation_pages.about",
    "pages.organisation_pages.partners",
    "pages.organisation_pages.projects",
    "pages.organisation_pages.tenders",
    "pages.organisation_pages.vacancies",
    "pages.email_subscription",
    "pages.surveys",
    "pages.search",
    "pages.data_request",
    "pages.flex_page",
    "pages.cap",
    "pages.stations",
    "pages.satellite_imagery",
    "pages.cityclimate",

    "adminboundarymanager",
    "geomanager",
    "capeditor",
    "forecastmanager",

    "wagtailmautic",
    "wagtailzoom",
    "wagtailsurveyjs",
    "wagtailmailchimp",
    "wagtailhumanitarianicons",
    "wagtailiconchooser",

    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    'wagtail.contrib.settings',
    "wagtail.contrib.routable_page",
    'wagtail.contrib.search_promotions',
    "wagtail.contrib.table_block",
    'wagtail.contrib.sitemaps',
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
    'django.contrib.sitemaps',

    "modelcluster",
    "rest_framework",
    'rest_framework_xml',
    "taggit",
    "corsheaders",
    "wagtailcache",
    "allauth",
    "allauth.account",
    "wagtail_adminsortable",
    "wagtailmetadata",
    "wagtailfontawesomesvg",
    "wagtailgeowidget",
    "wagtail_lazyimages",
    "wagtail_color_panel",
    "django_large_image",
    'django_json_widget',
    'django_nextjs',
    "django_filters",
    "django_deep_translator",
    "widget_tweaks",
    "captcha",
    'wagtailcaptcha',
    "bulma",
    "mailchimp3",
    "manifest_loader",
    "django_tables2",
    "django_tables2_bulma_template",
    "background_task",
    "django_cleanup",
    "django_countries",
    "wagtail_modeladmin"
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
                'django.template.context_processors.i18n',
                'base.context_processors.theme',
                "django.template.context_processors.debug",
            ],
        },
    },
]

WSGI_APPLICATION = "nmhs_cms.wsgi.application"

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
    # 'pages/home/locale',
    # 'pages/products/locale',
    # 'pages/services/locale',
    # 'pages/events/locale',
    # 'pages/feedback/locale',
    # 'pages/contact/locale',
    # 'pages/publications/locale',
    # 'pages/surveys/locale',
    # 'pages/videos/locale',
    # 'pages/cap/locale',
    # 'pages/data_request/locale',
    # 'pages/email_subscription/locale',
    # 'pages/flex_page/locale',
    # 'pages/mediacenter/locale',
    # 'pages/videos/locale',
    # 'pages/publications/locale',
    # 'pages/news/locale',
    # 'pages/organisation_pages/about/locale',
    # 'pages/organisation_pages/organisation/locale',
    # 'pages/organisation_pages/contact/locale',
    # 'pages/organisation_pages/projects/locale',
    # 'pages/organisation_pages/partners/locale',
    # 'pages/organisation_pages/tenders/locale',
    # 'pages/organisation_pages/vacancies/locale',
    # 'base/locale',
    'docs/locales',
)

TIME_ZONE = env.str("TIME_ZONE", "UTC")

USE_I18N = True
# WAGTAIL_I18N_ENABLED = True

USE_L10N = True

USE_TZ = True

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_LANGUAGES = ('en', 'es')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django.contrib.staticfiles.finders.FileSystemFinder",
]

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]

# ManifestStaticFilesStorage is recommended in production, to prevent outdated
# JavaScript / CSS assets being served from cache (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/4.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
# STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATIC_URL = env.str("FORCE_SCRIPT_NAME", "") + "/static/"

MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = env.str("FORCE_SCRIPT_NAME", "") + "/media/"

# Wagtail settings
# SITE_NAME="nmhs_cms"
WAGTAIL_SITE_NAME = env.str("WAGTAIL_SITE_NAME", "NMHSs CMS")

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
RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY', '')

RECAPTCHA_TESTING = True

ORDERING_FIELD = 'position'
WAGTAILDOCS_DOCUMENT_MODEL = 'base.CustomDocumentModel'

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

SOCIAL_MEDIA_SHARE_CONFIG = {
    'facebook': {"base_url": "https://www.facebook.com/sharer/sharer.php", "link_param": "u"},
    'twitter': {"base_url": "http://twitter.com/share", "text_param": "text", "link_param": "url"}
}

CORS_ALLOW_ALL_ORIGINS = True

NEXTJS_SETTINGS = {
    "nextjs_server_url": env.str("NEXTJS_SERVER_URL", default=""),
}

FORCE_SCRIPT_NAME = env.str("FORCE_SCRIPT_NAME", default="")

WAGTAILIMAGES_EXTENSIONS = ["gif", "jpg", "jpeg", "png", "webp", "svg"]

DJANGO_TABLES2_TEMPLATE = "django-tables2/bulma.html"
