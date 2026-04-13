import environ
from pathlib import Path

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "django_htmx",
    "axes",
    "anymail",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.organizations",
    "apps.events",
    "apps.referrals",
    "apps.services",
    "apps.pathways",
    "apps.assistant",
    "apps.newsfeed",
    "apps.audit",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.organizations.middleware.OnboardingRedirectMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
}

# Auth
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("pa", "ਪੰਜਾਬੀ"),       # Punjabi
    ("pl", "Polski"),          # Polish
    ("ur", "اردو"),            # Urdu (RTL)
    ("ro", "Română"),          # Romanian
    ("bn", "বাংলা"),           # Bengali
    ("gu", "ગુજરાતી"),        # Gujarati
    ("ar", "العربية"),         # Arabic (RTL)
    ("zh-hans", "简体中文"),    # Chinese Simplified
    ("so", "Soomaali"),        # Somali
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# Languages that require RTL
RTL_LANGUAGES = ["ur", "ar"]

# Static files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# JWT
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    # Extend occurrence window weekly
    "generate-event-occurrences-weekly": {
        "task": "apps.events.tasks.generate_event_occurrences",
        "schedule": 604800,  # every 7 days
    },
    # Scrape org event/news pages weekly
    "scrape-all-org-events-weekly": {
        "task": "apps.events.tasks.scrape_all_org_events",
        "schedule": 604800,
    },
    # Check unacknowledged referrals every hour
    "escalate-unacknowledged-referrals-hourly": {
        "task": "apps.referrals.tasks.escalate_unacknowledged_referrals",
        "schedule": 3600,
    },
}

SITE_URL = env("SITE_URL", default="http://localhost:8000")

# Regional hero imagery (Flickr public feed — no API key; see Real Python Picha).
# Comma-separated list: each segment is its own feed query (results merged).
# (A single Flickr request ANDs comma-separated tags, so one long list returns almost nothing.)
COMMUNITY_PHOTO_FLICKR_TAGS = env(
    "COMMUNITY_PHOTO_FLICKR_TAGS",
    default=(
        "wolverhampton,westmidlands,blackcountry,staffordshire,"
        "worcestershire,shropshire,birmingham,community"
    ),
)
COMMUNITY_PHOTO_SYNC_LIMIT = env.int("COMMUNITY_PHOTO_SYNC_LIMIT", default=24)
COMMUNITY_PHOTO_HERO_DISPLAY = env.int("COMMUNITY_PHOTO_HERO_DISPLAY", default=6)

# Curated hero imagery (preferred over Flickr for public home)
SITE_IMAGE_HERO_MAX = env.int("SITE_IMAGE_HERO_MAX", default=3)
HERO_USE_FLICKR_COMMUNITY_PHOTOS = env.bool("HERO_USE_FLICKR_COMMUNITY_PHOTOS", default=False)

# Email — SendGrid via django-anymail
# Set EMAIL_BACKEND in .env:
#   console: django.core.mail.backends.console.EmailBackend  (dev default)
#   live:    anymail.backends.sendgrid.EmailBackend
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

ANYMAIL = {
    "SENDGRID_API_KEY": env("SENDGRID_API_KEY", default=""),
}

# Axes (brute force protection)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_PARAMETERS = ["username"]

# CORS
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Obsidian vault path
OBSIDIAN_VAULT_PATH = env("OBSIDIAN_VAULT_PATH", default="")

# Encryption key for PII fields
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# Gemini API
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
