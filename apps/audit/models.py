"""
Hash-chained audit log.

Every significant action (referral create/update, PII access, status change,
delivery attempt) is appended here. Each entry includes a SHA-256 hash of
(prev_hash + this record's content), forming a tamper-evident chain.

The chain can be verified by replaying all entries in order and recomputing hashes.
"""
import hashlib
import json
import uuid
from datetime import timezone as dt_timezone

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AuditEntry(models.Model):
    """
    Append-only, hash-chained audit record.

    Never update or delete these rows — integrity depends on immutability.
    """

    ACTION_CHOICES = [
        # Referral lifecycle
        ("referral_created", _("Referral created")),
        ("referral_status_changed", _("Referral status changed")),
        ("referral_pii_accessed", _("Referral PII accessed")),
        ("referral_deleted", _("Referral deleted")),
        # Delivery
        ("delivery_queued", _("Delivery queued")),
        ("delivery_sent", _("Delivery sent")),
        ("delivery_failed", _("Delivery failed")),
        ("delivery_acknowledged", _("Delivery acknowledged")),
        # Org management
        ("org_created", _("Organisation created")),
        ("org_updated", _("Organisation updated")),
        ("onboarding_step_completed", _("Onboarding step completed")),
        ("onboarding_completed", _("Onboarding completed")),
        # Auth
        ("user_login", _("User login")),
        ("user_approved", _("User approved")),
        ("user_role_changed", _("User role changed")),
        # Admin
        ("admin_action", _("Admin action")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Actor
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("actor"),
    )
    actor_email = models.EmailField(
        _("actor email"), blank=True, default="",
        help_text=_("Snapshot at time of action in case user is later deleted"),
    )

    action = models.CharField(_("action"), max_length=40, choices=ACTION_CHOICES)

    # Generic FK — can point to any model (Referral, Organization, User, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("target type"),
    )
    object_id = models.CharField(
        _("target ID"), max_length=64, blank=True, default=""
    )
    target = GenericForeignKey("content_type", "object_id")

    # What changed
    delta = models.JSONField(
        _("delta"),
        default=dict,
        blank=True,
        help_text=_("Dict of changed fields: {field: [old, new]}"),
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        blank=True,
        help_text=_("Extra context: IP address, channel, etc."),
    )

    timestamp = models.DateTimeField(_("timestamp"), default=timezone.now, db_index=True)

    # Hash chain
    prev_hash = models.CharField(
        _("previous hash"), max_length=64, blank=True, default="",
        help_text=_("SHA-256 of the previous AuditEntry, or empty for first entry"),
    )
    entry_hash = models.CharField(
        _("entry hash"), max_length=64, unique=True,
        help_text=_("SHA-256 of (prev_hash + action + object_id + timestamp_iso)"),
    )

    class Meta:
        ordering = ["timestamp"]
        verbose_name = _("Audit Entry")
        verbose_name_plural = _("Audit Entries")
        # No update permission — append only enforced at service layer

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.action} by {self.actor_email}"

    @classmethod
    def compute_hash(cls, prev_hash, action, object_id, timestamp_iso, delta):
        payload = json.dumps(
            {
                "prev_hash": prev_hash,
                "action": action,
                "object_id": str(object_id),
                "timestamp": timestamp_iso,
                "delta": delta,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @classmethod
    def log(
        cls,
        action,
        actor=None,
        target=None,
        delta=None,
        metadata=None,
    ):
        """
        Create a new AuditEntry linked to the hash chain.

        Usage::

            AuditEntry.log(
                action="referral_created",
                actor=request.user,
                target=referral,
                delta={"status": [None, "submitted"]},
                metadata={"ip": request.META.get("REMOTE_ADDR")},
            )
        """
        delta = delta or {}
        metadata = metadata or {}

        object_id = ""
        content_type = None
        if target is not None:
            content_type = ContentType.objects.get_for_model(target)
            object_id = str(target.pk)

        actor_email = ""
        if actor and hasattr(actor, "email"):
            actor_email = actor.email

        now = timezone.now()
        # Normalise to UTC so verify_chain produces the same string after a
        # DB round-trip regardless of the local timezone representation.
        timestamp_iso = now.astimezone(dt_timezone.utc).isoformat()

        with transaction.atomic():
            # select_for_update() serialises concurrent log() calls in
            # PostgreSQL so the prev_hash is always the latest entry's hash.
            last = cls.objects.select_for_update().order_by("-timestamp").first()
            prev_hash = last.entry_hash if last else ""

            entry_hash = cls.compute_hash(
                prev_hash, action, object_id, timestamp_iso, delta
            )

            return cls.objects.create(
                actor=actor,
                actor_email=actor_email,
                action=action,
                content_type=content_type,
                object_id=object_id,
                delta=delta,
                metadata=metadata,
                timestamp=now,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )

    @classmethod
    def verify_chain(cls):
        """
        Replay all entries and verify the hash chain is unbroken.
        Returns (True, []) on success or (False, [broken_ids]) on failure.
        """
        broken = []
        prev_hash = ""
        for entry in cls.objects.order_by("timestamp"):
            # Normalise to UTC with the same isoformat() representation used
            # during log() so the hash can be reproduced after a DB round-trip.
            ts_iso = entry.timestamp.astimezone(dt_timezone.utc).isoformat()
            expected = cls.compute_hash(
                prev_hash,
                entry.action,
                entry.object_id,
                ts_iso,
                entry.delta,
            )
            if entry.entry_hash != expected:
                broken.append(str(entry.id))
            prev_hash = entry.entry_hash
        return (len(broken) == 0, broken)
