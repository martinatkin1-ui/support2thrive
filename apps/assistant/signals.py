"""
apps/assistant/signals.py
Post-save signal handlers that trigger LightRAG indexing tasks.

Signals registered in AssistantConfig.ready() to avoid import-time side effects.

WHY signals (not overriding save()): Consistent with project pattern (referrals app
does not override save for async work). Signals decouple the indexing concern from
the model layer cleanly.

IMPORTANT: Organization and OrganizationService saves both trigger re-indexing of
the parent org (since build_org_content_list fetches related services together).
"""
import logging

logger = logging.getLogger(__name__)


def _dispatch_org_index(org_id: int) -> None:
    """Helper: dispatch index_organization task, logging errors without raising."""
    try:
        from apps.assistant.tasks import index_organization
        index_organization.delay(org_id)
        logger.debug("Queued index_organization for org_id=%s", org_id)
    except Exception:
        logger.exception("Failed to queue index_organization for org_id=%s", org_id)


def register_signals() -> None:
    """
    Called from AssistantConfig.ready().
    All signal registrations are here, not at module import level,
    to avoid AppRegistryNotReady during migrations.
    """
    from django.db.models.signals import post_save
    from django.dispatch import receiver

    from apps.organizations.models import Organization, OrganizationService
    from apps.pathways.models import Pathway, PathwayGuideItem, PathwaySection
    from apps.assistant.models import OrgDocument

    @receiver(post_save, sender=Organization)
    def on_organization_save(sender, instance, created, **kwargs):
        _dispatch_org_index(instance.pk)

    @receiver(post_save, sender=OrganizationService)
    def on_org_service_save(sender, instance, created, **kwargs):
        # Re-index the parent org (services are fetched together in build_org_content_list)
        if hasattr(instance, "organization_id"):
            _dispatch_org_index(instance.organization_id)

    @receiver(post_save, sender=Pathway)
    def on_pathway_save(sender, instance, created, **kwargs):
        try:
            from apps.assistant.tasks import index_pathway
            index_pathway.delay(instance.pk)
        except Exception:
            logger.exception("Failed to queue index_pathway for pathway_id=%s", instance.pk)

    @receiver(post_save, sender=PathwaySection)
    def on_pathway_section_save(sender, instance, created, **kwargs):
        try:
            from apps.assistant.tasks import index_pathway
            index_pathway.delay(instance.pathway_id)
        except Exception:
            logger.exception("Failed to queue index_pathway via section for pathway_id=%s", instance.pathway_id)

    @receiver(post_save, sender=PathwayGuideItem)
    def on_pathway_guide_item_save(sender, instance, created, **kwargs):
        try:
            from apps.assistant.tasks import index_pathway
            index_pathway.delay(instance.section.pathway_id)
        except Exception:
            logger.exception("Failed to queue index_pathway via guide_item")

    @receiver(post_save, sender=OrgDocument)
    def on_org_document_save(sender, instance, created, **kwargs):
        """Index PDF when OrgDocument is saved with a file."""
        if instance.file:
            try:
                from apps.assistant.tasks import index_org_document
                index_org_document.delay(instance.pk)
            except Exception:
                logger.exception("Failed to queue index_org_document for doc_id=%s", instance.pk)
