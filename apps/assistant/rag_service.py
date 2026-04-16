"""
apps/assistant/rag_service.py

Provides:
  get_rag_instance()             — async, returns initialised RAGAnything singleton
  build_org_content_list(org_id) — sync, returns content_list for insert_content_list
  build_pathway_content_list(pathway_id) — sync, returns content_list for insert_content_list

IMPORTANT: raganything must be installed with --no-deps (mineru is Python <3.14 only).
LightRAG manages its own Postgres tables (LIGHTRAG_DOC_FULL, LIGHTRAG_VDB_CHUNKS, etc.)
via environment variables POSTGRES_HOST/PORT/USER/PASSWORD/DATABASE/WORKSPACE.
"""
import asyncio
import logging
from functools import partial

import numpy as np
from django.conf import settings
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Module-level embedding model — loaded once on worker startup
_st_model: SentenceTransformer | None = None
_rag_instance = None
_rag_lock = asyncio.Lock()


def _get_sentence_transformer() -> SentenceTransformer:
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _st_model


async def _embedding_func_impl(texts: list[str]) -> np.ndarray:
    """sentence-transformers implementation for LightRAG EmbeddingFunc."""
    model = _get_sentence_transformer()
    return model.encode(texts, normalize_embeddings=True)


# EmbeddingFunc is a dataclass in lightrag 1.4.14 — instantiate directly
embedding_func = EmbeddingFunc(
    embedding_dim=384,
    max_token_size=512,
    func=_embedding_func_impl,
)


async def get_rag_instance():
    """
    Returns the RAGAnything singleton, initialising on first call.
    Thread-safe via asyncio.Lock(). Call from Celery with asyncio.run().

    Requires environment variables set (via .env):
      POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD,
      POSTGRES_DATABASE, POSTGRES_WORKSPACE, POSTGRES_MAX_CONNECTIONS
      GEMINI_API_KEY (read by lightrag.llm.gemini automatically)
    """
    global _rag_instance
    async with _rag_lock:
        if _rag_instance is not None:
            return _rag_instance

        from lightrag.llm.gemini import gemini_model_complete
        from raganything import RAGAnything, RAGAnythingConfig

        llm_func = partial(gemini_model_complete, model_name="gemini-2.5-flash")

        config = RAGAnythingConfig(
            working_dir=settings.LIGHTRAG_WORKING_DIR,
            enable_image_processing=False,  # org docs are text-heavy, no image extraction needed
            enable_table_processing=True,
            enable_equation_processing=False,
        )

        rag = RAGAnything(
            config=config,
            llm_model_func=llm_func,
            vision_model_func=llm_func,
            embedding_func=embedding_func,
            lightrag_kwargs={
                "kv_storage": "PGKVStorage",
                "vector_storage": "PGVectorStorage",
                "graph_storage": "PGGraphStorage",
                "doc_status_storage": "PGDocStatusStorage",
                "vector_db_storage_cls_kwargs": {
                    "cosine_better_than_threshold": 0.2,
                },
                "llm_model_max_async": 2,  # limit concurrent Gemini calls during indexing
            },
        )
        await rag._ensure_lightrag_initialized()
        _rag_instance = rag
        logger.info("RAGAnything singleton initialised with LightRAG PG backend")
        return _rag_instance


def build_org_content_list(org_id: int) -> list[dict]:
    """
    Build insert_content_list payload from an Organisation and its services.
    Returns a list of {"type": "text", "text": "...", "page_idx": N} dicts.
    Called synchronously from Celery tasks (no async needed here).
    """
    from apps.organizations.models import Organization

    try:
        org = Organization.objects.prefetch_related(
            "services__category"
        ).get(pk=org_id)
    except Organization.DoesNotExist:
        logger.warning("build_org_content_list: org_id=%s not found", org_id)
        return []

    chunks = []
    # Core org profile
    profile = (
        f"Organisation: {org.name}\n"
        f"Description: {org.description}\n"
        f"Short description: {org.short_description}\n"
        f"Address: {org.address_line_1}, {org.city}, {org.postcode}\n"
        f"Phone: {org.phone}\n"
        f"Email: {org.email}\n"
        f"Website: {org.website}\n"
    )
    chunks.append({"type": "text", "text": profile, "page_idx": 0})

    # Services
    for i, svc in enumerate(org.services.all(), start=1):
        svc_text = (
            f"Service offered by {org.name}: {svc.name}\n"
            f"Description: {svc.description}\n"
        )
        if svc.category:
            svc_text += f"Category: {svc.category.name}\n"
        chunks.append({"type": "text", "text": svc_text, "page_idx": i})

    return chunks


def build_pathway_content_list(pathway_id: int) -> list[dict]:
    """
    Build insert_content_list payload from a Pathway and its sections + guide items.
    """
    from apps.pathways.models import Pathway

    try:
        pathway = Pathway.objects.prefetch_related(
            "sections__guide_items"
        ).get(pk=pathway_id)
    except Pathway.DoesNotExist:
        logger.warning("build_pathway_content_list: pathway_id=%s not found", pathway_id)
        return []

    chunks = []
    intro = (
        f"Pathway: {pathway.title}\n"
        f"Audience: {pathway.get_audience_tag_display()}\n"
        f"Description: {pathway.description}\n"
    )
    chunks.append({"type": "text", "text": intro, "page_idx": 0})

    page = 1
    for section in pathway.sections.order_by("display_order"):
        section_text = f"Section: {section.title}\n{section.body}\n"
        chunks.append({"type": "text", "text": section_text, "page_idx": page})
        page += 1
        for item in section.guide_items.order_by("display_order"):
            item_text = f"Guide: {item.title}\n{item.body}\n"
            chunks.append({"type": "text", "text": item_text, "page_idx": page})
            page += 1

    return chunks
