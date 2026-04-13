"""
Referral delivery service.

Handles the no-loss delivery guarantee:
  1. Referral is always saved to DB first.
  2. A ReferralDelivery record is created for each requested channel.
  3. Celery tasks process each delivery asynchronously with retries.
  4. The in_platform channel always succeeds (stored in DB = delivered).
  5. Failures are logged; after max retries the referral is flagged delivery_failed.

Public API
----------
  create_referral(org, form_data, pii_dict, referring_user=None) -> Referral
  queue_deliveries(referral) -> list[ReferralDelivery]
  send_email_delivery(delivery_id)
  send_webhook_delivery(delivery_id)
"""
import hashlib
import hmac
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.audit.models import AuditEntry

from .encryption import encrypt_pii
from .models import Referral, ReferralDelivery, ReferralFormField

logger = logging.getLogger(__name__)

MAX_EMAIL_ATTEMPTS = 3
MAX_WEBHOOK_ATTEMPTS = 5


# ---------------------------------------------------------------------------
# Create + store a referral
# ---------------------------------------------------------------------------

def create_referral(
    org,
    form_data: dict,
    pii_dict: dict,
    referring_user=None,
    referring_org=None,
    priority: str = "normal",
    consent_statement: str = "",
) -> Referral:
    """
    Persist a new referral. Always succeeds (no external calls at this stage).

    Args:
        org: The receiving Organisation instance.
        form_data: Non-PII form fields (service_needed, notes, etc.).
        pii_dict: PII fields — will be Fernet-encrypted before storage.
        referring_user: The User making the referral (None for self-referral).
        referring_org: The referring Organisation (cross-org referral).
        priority: 'normal' | 'urgent' | 'emergency'.
        consent_statement: The exact text the client agreed to.
    """
    referral = Referral(
        organization=org,
        referring_user=referring_user,
        referring_org=referring_org,
        form_data=form_data,
        priority=priority,
        consent_given=bool(pii_dict.get("consent")),
        consent_timestamp=timezone.now() if pii_dict.get("consent") else None,
        consent_statement=consent_statement,
    )
    referral.set_pii({k: v for k, v in pii_dict.items() if k != "consent"})
    referral.save()

    AuditEntry.log(
        action="referral_created",
        actor=referring_user,
        target=referral,
        delta={"status": [None, "submitted"], "priority": [None, priority]},
        metadata={"org_id": str(org.pk)},
    )

    return referral


# ---------------------------------------------------------------------------
# Queue deliveries for all org-configured channels
# ---------------------------------------------------------------------------

def queue_deliveries(referral: Referral) -> list:
    """
    Create ReferralDelivery records for all channels the org supports.
    The in_platform channel is always included and marked as 'sent' immediately
    (no external call needed — it's visible in the org's portal inbox).
    """
    org = referral.organization
    channels = list(org.referral_delivery_channels or [])
    if "in_platform" not in channels:
        channels.insert(0, "in_platform")

    deliveries = []
    for channel in channels:
        delivery, created = ReferralDelivery.objects.get_or_create(
            referral=referral,
            channel=channel,
            defaults={"status": "queued"},
        )
        if not created:
            continue

        if channel == "in_platform":
            # In-platform = stored in DB = already delivered
            delivery.status = "sent"
            delivery.attempts = 1
            delivery.last_attempted_at = timezone.now()
            delivery.save(update_fields=["status", "attempts", "last_attempted_at"])
            AuditEntry.log(
                action="delivery_sent",
                actor=None,
                target=referral,
                metadata={"channel": "in_platform"},
            )
        elif channel == "email":
            from .tasks import send_referral_email
            send_referral_email.delay(str(delivery.pk))
        elif channel == "crm_webhook":
            from .tasks import send_referral_webhook
            send_referral_webhook.delay(str(delivery.pk))
        # csv and print are on-demand (pulled from portal) — no async task needed

        deliveries.append(delivery)

    return deliveries


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

def send_email_delivery(delivery_id: str):
    """Send referral details to the org's referral_email. Called by Celery task."""
    try:
        delivery = ReferralDelivery.objects.select_related(
            "referral__organization"
        ).get(pk=delivery_id)
    except ReferralDelivery.DoesNotExist:
        logger.error("ReferralDelivery %s not found", delivery_id)
        return

    referral = delivery.referral
    org = referral.organization
    recipient = org.referral_email or org.email

    if not recipient:
        delivery.status = "failed"
        delivery.error_log = "No referral_email or email set on organisation."
        delivery.save(update_fields=["status", "error_log"])
        return

    delivery.attempts += 1
    delivery.last_attempted_at = timezone.now()

    try:
        pii = referral.get_pii()
        subject = f"[WMCS] New referral {referral.reference_number} — {referral.priority.upper()}"
        body = render_to_string("referrals/email/referral_notification.txt", {
            "referral": referral,
            "org": org,
            "pii": pii,
        })
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        delivery.status = "sent"
        AuditEntry.log(
            action="delivery_sent",
            target=referral,
            metadata={"channel": "email", "recipient": recipient},
        )
    except Exception as exc:
        delivery.error_log = str(exc)
        if delivery.attempts >= MAX_EMAIL_ATTEMPTS:
            delivery.status = "failed"
            _escalate_delivery_failure(delivery)
        # else: task will retry
        logger.exception("Email delivery failed for %s", referral.reference_number)
    finally:
        delivery.save(update_fields=["status", "attempts", "last_attempted_at", "error_log"])


# ---------------------------------------------------------------------------
# Webhook delivery
# ---------------------------------------------------------------------------

def send_webhook_delivery(delivery_id: str):
    """POST referral JSON to org's CRM webhook URL. Called by Celery task."""
    import urllib.request

    try:
        delivery = ReferralDelivery.objects.select_related(
            "referral__organization"
        ).get(pk=delivery_id)
    except ReferralDelivery.DoesNotExist:
        return

    referral = delivery.referral
    org = referral.organization

    if not org.crm_webhook_url:
        delivery.status = "failed"
        delivery.error_log = "No crm_webhook_url configured."
        delivery.save(update_fields=["status", "error_log"])
        return

    delivery.attempts += 1
    delivery.last_attempted_at = timezone.now()

    payload = json.dumps({
        "reference_number": referral.reference_number,
        "organization_slug": org.slug,
        "status": referral.status,
        "priority": referral.priority,
        "created_at": referral.created_at.isoformat(),
        "form_data": referral.form_data,
        # PII not included in webhook by default — org must request via secure channel
    }, ensure_ascii=False).encode("utf-8")

    # HMAC signature — warn if no secret configured (unsigned webhook)
    if not org.crm_webhook_secret:
        logger.warning(
            "Sending unsigned webhook for referral %s to org %s — "
            "set crm_webhook_secret to enable HMAC verification",
            referral.reference_number,
            org.slug,
        )
    secret = org.crm_webhook_secret.encode() if org.crm_webhook_secret else b""
    sig = hmac.new(secret, payload, hashlib.sha256).hexdigest() if secret else ""

    try:
        req = urllib.request.Request(
            org.crm_webhook_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-WMCS-Signature": sig,
                "X-WMCS-Reference": referral.reference_number,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            delivery.last_response_code = resp.status
            if 200 <= resp.status < 300:
                delivery.status = "sent"
                AuditEntry.log(
                    action="delivery_sent",
                    target=referral,
                    metadata={"channel": "crm_webhook", "status_code": resp.status},
                )
            else:
                raise ValueError(f"HTTP {resp.status}")
    except Exception as exc:
        delivery.error_log = str(exc)
        if delivery.attempts >= MAX_WEBHOOK_ATTEMPTS:
            delivery.status = "failed"
            _escalate_delivery_failure(delivery)
        logger.exception(
            "Webhook delivery failed for %s", referral.reference_number
        )
    finally:
        delivery.save(
            update_fields=["status", "attempts", "last_attempted_at",
                           "error_log", "last_response_code"]
        )


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------

def _escalate_delivery_failure(delivery: ReferralDelivery):
    """Flag referral and notify platform admins when all delivery retries exhausted."""
    referral = delivery.referral
    referral.escalated = True
    referral.save(update_fields=["escalated"])
    AuditEntry.log(
        action="delivery_failed",
        target=referral,
        metadata={"channel": delivery.channel, "attempts": delivery.attempts},
    )
    logger.critical(
        "All delivery attempts failed for referral %s via %s",
        referral.reference_number,
        delivery.channel,
    )
    # TODO: send admin alert email (Phase 4.4)


def check_unacknowledged_referrals():
    """
    Called by Celery beat. Sends reminders and escalates overdue referrals.
    - 24h unacknowledged → reminder email to org
    - 48h unacknowledged → escalate (set escalated=True, notify admin)
    """
    now = timezone.now()
    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)

    # 48h escalation
    to_escalate = list(Referral.objects.filter(
        status="submitted",
        acknowledged_at__isnull=True,
        escalated=False,
        created_at__lte=cutoff_48h,
    ))
    for referral in to_escalate:
        referral.escalated = True
        referral.save(update_fields=["escalated"])
        AuditEntry.log(
            action="referral_status_changed",
            target=referral,
            delta={"escalated": [False, True]},
            metadata={"reason": "48h_unacknowledged"},
        )
        logger.warning("Referral %s escalated (48h unacknowledged)", referral.reference_number)

    # 24h reminder (not yet escalated, not yet acknowledged)
    to_remind = list(Referral.objects.filter(
        status="submitted",
        acknowledged_at__isnull=True,
        escalated=False,
        created_at__lte=cutoff_24h,
        created_at__gt=cutoff_48h,
    ))
    for referral in to_remind:
        _send_acknowledgment_reminder(referral)

    return len(to_escalate), len(to_remind)


def _send_acknowledgment_reminder(referral: Referral):
    org = referral.organization
    recipient = org.referral_email or org.email
    if not recipient:
        return
    try:
        send_mail(
            subject=f"[WMCS] Reminder: referral {referral.reference_number} needs acknowledgment",
            message=(
                f"Referral {referral.reference_number} was submitted "
                f"{referral.created_at:%Y-%m-%d %H:%M} and has not been acknowledged.\n\n"
                f"Please log in to acknowledge it: {settings.SITE_URL}/portal/referrals/"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception:
        pass
