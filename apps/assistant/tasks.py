"""
apps/assistant/tasks.py
Celery tasks for indexing platform content into LightRAG.

Pattern follows apps/referrals/tasks.py:
  - bind=True for self.retry() access
  - max_retries=3, exponential backoff
  - Import service functions inside task body (avoids circular imports at module load)
  - logger.exception() on failure (not logger.error — ensures traceback is captured)

IMPORTANT: asyncio.run() inside tasks is safe on Python 3.14. LightRAG APIs are fully
async; we bridge with asyncio.run() since Celery workers are sync.
"""
import asyncio

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, rate_limit="2/m")
def index_organization(self, org_id: int):
    """
    Index a single organisation (profile + services) into LightRAG.
    Triggered by post_save signal on Organization and OrganizationService.
    rate_limit="2/m" — prevents flooding Gemini API during bulk indexing.
    """
    from apps.assistant.rag_service import build_org_content_list, get_rag_instance

    async def _index():
        content_list = build_org_content_list(org_id)
        if not content_list:
            logger.warning("index_organization: empty content_list for org_id=%s, skipping", org_id)
            return
        rag = await get_rag_instance()
        await rag.insert_content_list(
            content_list,
            file_path=f"orgs/{org_id}",
            doc_id=f"org-{org_id}",
        )
        logger.info("index_organization: indexed org_id=%s (%d chunks)", org_id, len(content_list))

    try:
        asyncio.run(_index())
    except Exception as exc:
        logger.exception("index_organization failed for org_id=%s", org_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=60, rate_limit="2/m")
def index_pathway(self, pathway_id: int):
    """
    Index a single Pathway (intro + sections + guide items) into LightRAG.
    Triggered by post_save signal on Pathway, PathwaySection, PathwayGuideItem.
    """
    from apps.assistant.rag_service import build_pathway_content_list, get_rag_instance

    async def _index():
        content_list = build_pathway_content_list(pathway_id)
        if not content_list:
            logger.warning("index_pathway: empty content_list for pathway_id=%s, skipping", pathway_id)
            return
        rag = await get_rag_instance()
        await rag.insert_content_list(
            content_list,
            file_path=f"pathways/{pathway_id}",
            doc_id=f"pathway-{pathway_id}",
        )
        logger.info("index_pathway: indexed pathway_id=%s (%d chunks)", pathway_id, len(content_list))

    try:
        asyncio.run(_index())
    except Exception as exc:
        logger.exception("index_pathway failed for pathway_id=%s", pathway_id)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def index_org_document(self, document_id: int):
    """
    Parse an org-uploaded PDF with pymupdf4llm and index it into LightRAG.
    Triggered by post_save signal on OrgDocument when file is set.
    Sets indexed_at on success; sets index_error on failure.
    """
    from apps.assistant.services import process_org_document

    try:
        process_org_document(document_id)
    except Exception as exc:
        logger.exception("index_org_document failed for document_id=%s", document_id)
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
