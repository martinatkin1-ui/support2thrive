"""
Fernet symmetric encryption for referral PII fields.

Fernet uses AES-128-CBC with HMAC-SHA256 for authenticated encryption.
The encryption key is read from settings.FIELD_ENCRYPTION_KEY (a URL-safe
base64-encoded 32-byte key).

In development/test (DEBUG=True), if no key is set, a deterministic key is
derived from settings.SECRET_KEY so tests run without extra config.
In production (DEBUG=False), FIELD_ENCRYPTION_KEY MUST be set — startup will
raise ImproperlyConfigured if it is missing.

Generate a production key once via:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

IMPORTANT: Losing the key means losing access to all PII. Store it in a secrets
manager (AWS Secrets Manager, HashiCorp Vault, etc.) and never commit it.
"""
import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        if not getattr(settings, "DEBUG", False):
            raise ImproperlyConfigured(
                "FIELD_ENCRYPTION_KEY must be set in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        # Derive a deterministic key from SECRET_KEY for dev/test only
        raw = settings.SECRET_KEY.encode()
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
        key = derived.decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_pii(pii_dict: dict) -> str:
    """Encrypt a dict of PII fields. Returns a URL-safe base64 token string."""
    if not pii_dict:
        return ""
    payload = json.dumps(pii_dict, ensure_ascii=False).encode("utf-8")
    return _get_fernet().encrypt(payload).decode("utf-8")


def decrypt_pii(token: str) -> dict:
    """
    Decrypt a PII token. Returns the original dict.
    Returns {} on decryption failure (key mismatch, corrupted data) so a bad
    token never crashes a view — callers must handle the empty-dict case.
    Unexpected exceptions are re-raised so programming errors surface.
    """
    if not token:
        return {}
    try:
        payload = _get_fernet().decrypt(token.encode("utf-8"))
        return json.loads(payload.decode("utf-8"))
    except InvalidToken:
        logger.warning("decrypt_pii: invalid or expired token — key mismatch or data corruption")
        return {}
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("decrypt_pii: JSON decode failed after decryption: %s", exc)
        return {}
