"""
apps/assistant/services.py
Service functions for the AI assistant.

process_org_document: parses PDF with pymupdf4llm, converts to content_list,
inserts into LightRAG, and updates OrgDocument.indexed_at / index_error.
"""
import asyncio
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 2000  # characters per content_list chunk


def _split_text(text: str, chunk_size: int = _CHUNK_SIZE) -> list[str]:
    """
    Split markdown text into chunks of up to chunk_size characters,
    breaking at newlines where possible to preserve semantic units.
    """
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        # Try to split at a newline boundary within the window
        split_at = text.rfind("\n", 0, chunk_size)
        if split_at == -1:
            split_at = chunk_size
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    return [c for c in chunks if c]


def process_org_document(document_id: int) -> None:
    """
    Parse a PDF with pymupdf4llm and insert into LightRAG via insert_content_list.
    Updates OrgDocument.indexed_at on success; sets index_error on failure.

    Called from index_org_document Celery task.
    """
    import pymupdf4llm  # deferred — not installed in test env; mocked in tests
    from apps.assistant.models import OrgDocument
    from apps.assistant.rag_service import get_rag_instance

    doc = OrgDocument.objects.select_related("org").get(pk=document_id)

    try:
        pdf_path = doc.file.path
        md_text = pymupdf4llm.to_markdown(pdf_path, show_progress=False)
        text_chunks = _split_text(md_text)
        content_list = [
            {"type": "text", "text": chunk, "page_idx": i}
            for i, chunk in enumerate(text_chunks)
        ]

        async def _index():
            rag = await get_rag_instance()
            await rag.insert_content_list(
                content_list,
                file_path=f"documents/{doc.org.slug}/{doc.title}",
                doc_id=f"orgdoc-{document_id}",
            )

        asyncio.run(_index())

        doc.indexed_at = timezone.now()
        doc.index_error = ""
        doc.save(update_fields=["indexed_at", "index_error", "updated_at"])
        logger.info("process_org_document: indexed doc_id=%s (%d chunks)", document_id, len(content_list))

    except Exception as exc:
        error_msg = str(exc)[:500]  # cap at 500 chars to avoid bloating the DB field
        doc.index_error = error_msg
        doc.save(update_fields=["index_error", "updated_at"])
        logger.exception("process_org_document failed for doc_id=%s", document_id)
        raise  # re-raise so Celery task can retry
