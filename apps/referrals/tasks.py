"""Celery tasks for referral delivery and acknowledgment escalation."""
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_referral_email(self, delivery_id: str):
    """Send a referral by email. Retries up to 3 times with 5-min backoff."""
    from .services import send_email_delivery
    try:
        send_email_delivery(delivery_id)
    except Exception as exc:
        logger.exception("Email delivery task failed for %s", delivery_id)
        raise self.retry(exc=exc, countdown=300 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def send_referral_webhook(self, delivery_id: str):
    """POST referral to org CRM webhook. Retries up to 5 times with exponential backoff."""
    from .services import send_webhook_delivery
    try:
        send_webhook_delivery(delivery_id)
    except Exception as exc:
        logger.exception("Webhook delivery task failed for %s", delivery_id)
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))


@shared_task
def escalate_unacknowledged_referrals():
    """
    Run every hour via Celery beat.
    Sends 24h reminders and 48h escalations for unacknowledged referrals.
    """
    from .services import check_unacknowledged_referrals
    escalated, reminded = check_unacknowledged_referrals()
    logger.info(
        "Acknowledgment check: %d escalated, %d reminded", escalated, reminded
    )
    return {"escalated": escalated, "reminded": reminded}
