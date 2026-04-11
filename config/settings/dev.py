from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Use SQLite for dev if no DATABASE_URL set
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# CORS - allow all in dev
CORS_ALLOW_ALL_ORIGINS = True

# Email - console backend for dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Disable axes in dev for convenience
AXES_ENABLED = False
