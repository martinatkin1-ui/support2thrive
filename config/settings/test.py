from .base import *  # noqa: F401, F403

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

AXES_ENABLED = False

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Deterministic test key — never use in production
FIELD_ENCRYPTION_KEY = "Tt2OJknU0sLIWRXPEYFke1Fu4n-4z4KJs-5HZf4NGvE="

# Skip LightRAG/pgvector calls in tests — mock at task/view level instead
SKIP_RAG_TESTS = True
LIGHTRAG_WORKING_DIR = "/tmp/rag_storage_test"
