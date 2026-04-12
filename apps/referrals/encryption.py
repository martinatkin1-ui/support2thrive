"""
Fernet symmetric encryption for referral PII fields.

The encryption key is read from settings.FIELD_ENCRYPTION_KEY (a URL-safe
base64-encoded 32-byte key). In development, if no key is set, a key is
derived from settings.SECRET_KEY so tests run without extra config.

In production, FIELD_ENCRYPTION_KEY MUST be set to a real random key generated
once via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

IMPORTANT: Losing the key means losing access to all PII. Store it in a secrets
manager (AWS Secrets Manager, HashiCorp Vault, etc.) and never commit it.
"""
import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _get_fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
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
    Returns {} on failure (key mismatch, corrupted data) rather than raising,
    so a bad token never crashes a view — the caller should handle empty dict.
    """
    if not token:
        return {}
    try:
        payload = _get_fernet().decrypt(token.encode("utf-8"))
        return json.loads(payload.decode("utf-8"))
    except (InvalidToken, Exception):
        return {}
