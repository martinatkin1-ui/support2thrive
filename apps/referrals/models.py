"""
Referral system models.

Design principles:
- All referrals are stored in the DB regardless of delivery channel (no-loss guarantee).
- PII is encrypted at rest using Fernet (symmetric) via apps.referrals.encryption.
- Delivery is decoupled from storage: a ReferralDelivery record is created per channel
  and processed asynchronously by Celery.
- Status changes are hash-chained via AuditEntry (see apps/audit/models.py).
"""
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


# ---------------------------------------------------------------------------
# Custom referral form fields (defined by each org during onboarding)
# ---------------------------------------------------------------------------

class ReferralFormField(TimeStampedModel):
    """
    A single field in an organisation's custom referral form.

    Orgs design their own intake form during onboarding. These fields drive the
    dynamic form rendered to the referring volunteer or self-referral client.
    """

    FIELD_TYPES = [
        # Text inputs
        ("text", _("Short text")),
        ("textarea", _("Long text")),
        ("email", _("Email address")),
        ("phone", _("Phone number")),
        ("url", _("URL / link")),
        # Date / numeric
        ("date", _("Date")),
        ("dob", _("Date of birth")),
        ("number", _("Number")),
        # Identity documents (all PII)
        ("nhs_number", _("NHS number")),
        ("ni_number", _("National Insurance number")),
        ("passport_number", _("Passport number")),
        ("dbs_reference", _("DBS reference number")),
        ("id_number", _("Other ID number")),
        # Location
        ("postcode", _("Postcode")),
        ("address", _("Full address")),
        # Choice fields
        ("select", _("Dropdown (single choice)")),
        ("radio", _("Radio buttons")),
        ("checkbox", _("Checkboxes (multi-select)")),
        ("boolean", _("Yes / No")),
        # File
        ("file", _("File upload")),
        # Consent (always appended, cannot be removed)
        ("consent", _("GDPR consent statement")),
    ]

    # PII field types — data in these fields is always encrypted
    PII_TYPES = {
        "email", "phone", "dob", "nhs_number", "ni_number",
        "passport_number", "dbs_reference", "id_number", "postcode",
        "address", "text",  # text may contain name etc — encrypt by default
        "textarea",
    }

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="referral_form_fields",
        verbose_name=_("organisation"),
    )
    field_type = models.CharField(
        _("field type"), max_length=30, choices=FIELD_TYPES
    )
    label = models.CharField(_("label"), max_length=200)
    help_text = models.CharField(
        _("help text"), max_length=300, blank=True, default=""
    )
    placeholder = models.CharField(
        _("placeholder"), max_length=200, blank=True, default=""
    )
    is_required = models.BooleanField(_("required"), default=False)
    # Options for select / radio / checkbox — stored as JSON list of strings
    options = models.JSONField(
        _("options"), default=list, blank=True,
        help_text=_("For select/radio/checkbox fields: list of option strings"),
    )
    display_order = models.PositiveSmallIntegerField(_("display order"), default=0)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["organization", "display_order"]
        verbose_name = _("Referral Form Field")
        verbose_name_plural = _("Referral Form Fields")

    def __str__(self):
        return f"{self.organization.name} — {self.label}"

    @property
    def is_pii(self):
        return self.field_type in self.PII_TYPES

    @property
    def slug(self):
        """Machine-safe key used as JSON key in Referral.form_data."""
        from django.utils.text import slugify
        return slugify(self.label).replace("-", "_")


# ---------------------------------------------------------------------------
# Referral
# ---------------------------------------------------------------------------

def _referral_ref():
    """Generate a human-readable reference: WM-YYYY-NNNNNN."""
    from datetime import date
    suffix = str(uuid.uuid4().int)[:6]
    return f"WM-{date.today().year}-{suffix}"


class Referral(TimeStampedModel):
    """
    A single referral from a volunteer (or self-referral from a client).

    Storage guarantee: every submitted referral is saved to the DB immediately,
    before any delivery attempt. Delivery failures cannot lose data.
    """

    STATUS_CHOICES = [
        ("submitted", _("Submitted")),
        ("acknowledged", _("Acknowledged")),
        ("in_progress", _("In Progress")),
        ("resolved", _("Resolved")),
        ("rejected", _("Rejected")),
        ("withdrawn", _("Withdrawn")),
    ]

    PRIORITY_CHOICES = [
        ("normal", _("Normal")),
        ("urgent", _("Urgent")),
        ("emergency", _("Emergency")),
    ]

    reference_number = models.CharField(
        _("reference number"), max_length=30, unique=True, default=_referral_ref,
        help_text=_("Human-readable reference, e.g. WM-2026-123456"),
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="referrals",
        verbose_name=_("organisation"),
    )
    # Who made the referral
    referring_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals_made",
        verbose_name=_("referring user"),
        help_text=_("Null for anonymous self-referrals"),
    )
    referring_org = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals_sent",
        verbose_name=_("referring organisation"),
    )

    # Form data — split into non-PII (queryable) and PII (encrypted)
    form_data = models.JSONField(
        _("form data"),
        default=dict,
        help_text=_(
            "Non-PII fields: priority, service_needed, urgency_reason, etc."
        ),
    )
    encrypted_pii = models.TextField(
        _("encrypted PII"),
        blank=True,
        default="",
        help_text=_("Fernet-encrypted JSON of all PII fields"),
    )

    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="submitted"
    )
    priority = models.CharField(
        _("priority"), max_length=10, choices=PRIORITY_CHOICES, default="normal"
    )

    # Consent
    consent_given = models.BooleanField(_("consent given"), default=False)
    consent_timestamp = models.DateTimeField(
        _("consent timestamp"), null=True, blank=True
    )
    consent_statement = models.TextField(
        _("consent statement"), blank=True, default="",
        help_text=_("The exact consent text the client agreed to"),
    )

    # Acknowledgment (receiving org must acknowledge)
    acknowledged_at = models.DateTimeField(
        _("acknowledged at"), null=True, blank=True
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals_acknowledged",
        verbose_name=_("acknowledged by"),
    )
    escalated = models.BooleanField(
        _("escalated"), default=False,
        help_text=_("Set True when unacknowledged after 48h"),
    )

    # Internal notes (not shown to client)
    notes = models.TextField(_("internal notes"), blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Referral")
        verbose_name_plural = _("Referrals")
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["referring_user"]),
            models.Index(fields=["acknowledged_at", "escalated"]),
        ]

    def __str__(self):
        return f"{self.reference_number} → {self.organization.name}"

    def get_pii(self):
        """Decrypt and return PII dict. Returns {} if not set."""
        if not self.encrypted_pii:
            return {}
        from apps.referrals.encryption import decrypt_pii
        return decrypt_pii(self.encrypted_pii)

    def set_pii(self, pii_dict):
        """Encrypt and store PII dict."""
        from apps.referrals.encryption import encrypt_pii
        self.encrypted_pii = encrypt_pii(pii_dict)

    def transition_status(self, new_status, actor, note=""):
        """
        Move referral to new_status, record in history, write audit entry.
        """
        from django.utils import timezone
        old_status = self.status
        self.status = new_status
        if new_status == "acknowledged" and not self.acknowledged_at:
            self.acknowledged_at = timezone.now()
            self.acknowledged_by = actor
        self.save(update_fields=["status", "acknowledged_at", "acknowledged_by"])
        ReferralStatusHistory.objects.create(
            referral=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=actor,
            note=note,
        )


# ---------------------------------------------------------------------------
# Referral delivery tracking
# ---------------------------------------------------------------------------

class ReferralDelivery(TimeStampedModel):
    """
    Tracks one delivery attempt per channel for a Referral.

    Multiple deliveries can exist for one referral (e.g. email + webhook).
    The in_platform record is always created and never fails.
    """

    CHANNEL_CHOICES = [
        ("in_platform", _("In-platform inbox")),
        ("email", _("Email")),
        ("csv", _("CSV download")),
        ("print", _("Print / paper")),
        ("crm_webhook", _("CRM webhook")),
    ]

    DELIVERY_STATUS = [
        ("queued", _("Queued")),
        ("sent", _("Sent")),
        ("failed", _("Failed")),
        ("acknowledged", _("Acknowledged")),
    ]

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("referral"),
    )
    channel = models.CharField(
        _("channel"), max_length=20, choices=CHANNEL_CHOICES
    )
    status = models.CharField(
        _("status"), max_length=20, choices=DELIVERY_STATUS, default="queued"
    )
    attempts = models.PositiveSmallIntegerField(_("attempts"), default=0)
    last_attempted_at = models.DateTimeField(
        _("last attempted at"), null=True, blank=True
    )
    error_log = models.TextField(_("error log"), blank=True, default="")
    # For webhook: store the response code of the last attempt
    last_response_code = models.PositiveSmallIntegerField(
        _("last HTTP response"), null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Referral Delivery")
        verbose_name_plural = _("Referral Deliveries")
        constraints = [
            # Only one delivery record per referral per channel
            models.UniqueConstraint(
                fields=["referral", "channel"], name="unique_referral_channel"
            )
        ]

    def __str__(self):
        return f"{self.referral.reference_number} via {self.get_channel_display()}"


# ---------------------------------------------------------------------------
# Status history
# ---------------------------------------------------------------------------

class ReferralStatusHistory(models.Model):
    """Append-only log of every status transition on a Referral."""

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("referral"),
    )
    from_status = models.CharField(_("from"), max_length=20)
    to_status = models.CharField(_("to"), max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("changed by"),
    )
    note = models.TextField(_("note"), blank=True, default="")
    changed_at = models.DateTimeField(_("changed at"), auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]
        verbose_name = _("Status History")
        verbose_name_plural = _("Status Histories")

    def __str__(self):
        return (
            f"{self.referral.reference_number}: "
            f"{self.from_status} → {self.to_status}"
        )
