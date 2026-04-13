from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

DEBUG = False

# Reject deployments that forgot to set a real SECRET_KEY
if SECRET_KEY.startswith("django-insecure-"):
    raise ImproperlyConfigured(
        "SECRET_KEY uses the development placeholder. "
        "Generate a real key and set it via the SECRET_KEY environment variable."
    )

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = "DENY"

# Email — SendGrid via anymail (set EMAIL_BACKEND + SENDGRID_API_KEY in env)
# base.py reads both from .env — no override needed here
