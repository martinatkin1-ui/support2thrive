# Phase 6: AI Assistant — Research

**Researched:** 2026-04-13
**Domain:** RAG pipeline, LightRAG/RAGAnything, pgvector, HTMX SSE, Django chat UI
**Confidence:** HIGH (all critical claims verified against installed package source code and PyPI registry)

---

<user_constraints>
## User Constraints (from PHASE-6-CONTEXT.md)

### Locked Decisions
1. RAG framework: raganything==1.2.10 (pip install raganything --no-deps) — HKUDS/RAG-Anything
2. Dev vector store: Docker Postgres with pgvector (update existing docker-compose.yml)
3. LLM: Gemini 2.5 Flash via LightRAG `llm_model_func` callback
4. Embeddings: sentence-transformers==5.4.0 (already installed)
5. Content indexed: Orgs + Services + ServiceCategories + Pathways + PathwayGuideItems + Org-uploaded PDFs
6. Chat UI: Dedicated /assistant/ page, HTMX streaming via SSE, Django session history
7. Tone: Warm + plain English, always cite sources, crisis keyword detection -> immediate signpost
8. Vault path: ./Community brain/ (OBSIDIAN_VAULT_PATH already set in .env) — DEFERRED
9. Email: SendGrid via django-anymail (already configured)

### Claude's Discretion
- Embedding model selection (all-MiniLM-L6-v2 vs all-mpnet-base-v2)
- Session history cap (suggested 10 exchanges)
- Rate limit thresholds (suggested 20/session)
- PDF upload size limit (suggested 20MB)
- Crisis keyword list

### Deferred Ideas (OUT OF SCOPE)
- Obsidian vault file watcher sync (OBSIDIAN_VAULT_PATH in .env — future phase)
- AI response translation (English-only for Phase 6)
- Floating assistant widget on all pages
- Events indexing (time-sensitive)
- Newsfeed indexing (app stubbed)
- Conversation DB persistence / user history across sessions
</user_constraints>

---

## Area 1: RAG-Anything Integration Pattern for Django

**Finding:**

`raganything==1.2.10` is confirmed on PyPI. However, `pip install raganything==1.2.10` FAILS on Python 3.14.3 because it lists `mineru[core]` as a hard dependency, and `mineru` does not publish a `[core]` extra on PyPI for Python 3.14 (mineru requires Python `<3.14, >=3.10`). [VERIFIED: pip dry-run on Python 3.14.3, 2026-04-13]

**The fix is confirmed:** `pip install raganything==1.2.10 --no-deps` installs the wheel without pulling mineru. The wheel itself is pure Python (`py3-none-any.whl`) and contains no Python-version-specific code. LightRAG-hku==1.4.14 is already installed in the venv and is the real runtime dependency. [VERIFIED: wheel inspection, 2026-04-13]

MineruParser (the default RAGAnything parser) calls the `mineru` CLI as a subprocess — it does not `import mineru`. This means `from raganything import RAGAnything` succeeds without mineru installed. Only calling `RAGAnything.process_document_complete()` with parser="mineru" would fail. [VERIFIED: raganything/parser.py MineruParser._run_mineru_command, 2026-04-13]

**The bypass: `insert_content_list()`**

RAGAnything has a first-class API to insert pre-parsed content without any parser. [VERIFIED: raganything/processor.py line 1867]

```python
await rag.insert_content_list(
    content_list=[
        {"type": "text", "text": "...", "page_idx": 0},
        {"type": "table", "table_body": "| col | col |", "table_caption": [], "page_idx": 1},
    ],
    file_path="orgs/my-org.md",   # used for citation/source attribution
    doc_id="org-123",             # optional stable ID for deduplication
)
```

For PDF uploads, parse with `pymupdf4llm.to_markdown()` (already researched in RESEARCH.md), convert to this content_list format, then call `insert_content_list`. This completely bypasses the mineru dependency. [VERIFIED: processor.py API + RESEARCH.md]

For org/service/pathway content (structured Django model data), build the content_list directly from Python objects — no PDF parsing needed at all.

**Custom parser alternative (lower priority):** `raganything.parser.register_parser("pymupdf4llm", PyMuPDF4LLMParser)` allows registering a custom Parser subclass. The Parser ABC requires implementing `parse_document(file_path, method, output_dir, **kwargs) -> List[Dict]` and `check_installation() -> bool`. This is viable but `insert_content_list` is simpler. [VERIFIED: raganything/parser.py register_parser]

**RAGAnything instantiation:**

```python
from raganything import RAGAnything, RAGAnythingConfig

config = RAGAnythingConfig(
    working_dir="./rag_storage",   # LightRAG file cache (used even with PG backend)
    enable_image_processing=True,
    enable_table_processing=True,
    enable_equation_processing=False,  # not needed for social services content
)

rag = RAGAnything(
    config=config,
    llm_model_func=gemini_model_complete,       # from lightrag.llm.gemini
    vision_model_func=gemini_model_complete,    # same function works for vision
    embedding_func=embedding_func,              # EmbeddingFunc-wrapped sentence-transformers
    lightrag_kwargs={
        "kv_storage": "PGKVStorage",
        "vector_storage": "PGVectorStorage",
        "graph_storage": "PGGraphStorage",
        "doc_status_storage": "PGDocStatusStorage",
        "vector_db_storage_cls_kwargs": {
            "cosine_better_than_threshold": 0.2
        },
    },
)
await rag._ensure_lightrag_initialized()
```

[VERIFIED: raganything/raganything.py __post_init__, lightrag LightRAG.__init__ signature, 2026-04-13]

**LightRAG Gemini integration — use existing `lightrag.llm.gemini` module:**

LightRAG 1.4.14 ships a production-ready Gemini binding at `lightrag/llm/gemini.py` that uses the new `google-genai` SDK (v1.72.0 installed). `google.generativeai` is deprecated and should NOT be used. [VERIFIED: installed package source + deprecation warning, 2026-04-13]

```python
from lightrag.llm.gemini import gemini_model_complete
from functools import partial

# llm_model_func reads llm_model_name from LightRAG global_config
# Pass model_name as a kwarg using partial
llm_model_func = partial(gemini_model_complete, model_name="gemini-2.5-flash")
```

The `gemini_model_complete` async function signature is:

```python
async def gemini_model_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict] | None = None,
    keyword_extraction: bool = False,
    **kwargs,
) -> str | AsyncIterator[str]
```

It uses built-in tenacity retry on rate-limit errors (ResourceExhausted, ServiceUnavailable, GatewayTimeout). [VERIFIED: lightrag/llm/gemini.py, 2026-04-13]

The LightRAG Gemini module reads `GEMINI_API_KEY` from the environment. Since `base.py` already loads this via `environ.Env.read_env`, it will be available. No additional config needed. [VERIFIED: base.py + lightrag/llm/gemini.py _get_gemini_client]

**sentence-transformers EmbeddingFunc wrapper:**

```python
from lightrag.utils import EmbeddingFunc
from sentence_transformers import SentenceTransformer
import numpy as np

# Module-level singleton — load once, reuse across tasks
_st_model = SentenceTransformer("all-MiniLM-L6-v2")   # 384-dim, fast

@EmbeddingFunc(embedding_dim=384, max_token_size=512)
async def embedding_func(texts: list[str]) -> np.ndarray:
    return _st_model.encode(texts, normalize_embeddings=True)
```

`EmbeddingFunc` is a class-based decorator from `lightrag.utils` that validates dimension and handles batching. Embedding dim for `all-MiniLM-L6-v2` is 384. For better retrieval quality, `all-mpnet-base-v2` (768-dim) is available — ~2x slower but more semantically accurate for nuanced queries. [VERIFIED: lightrag/utils.py EmbeddingFunc, sentence-transformers tested in venv]

**Asyncio from Celery (confirmed working):**

LightRAG's APIs are fully async (`ainsert`, `aquery`, `insert_content_list`). Celery tasks are synchronous. `asyncio.run()` works correctly from a sync context on Python 3.14.3. [VERIFIED: asyncio.run() tested in this session]

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def index_organization(self, org_id: int):
    import asyncio
    from apps.assistant.rag_service import get_rag_instance, build_org_content_list
    
    async def _index():
        rag = await get_rag_instance()
        content_list = build_org_content_list(org_id)
        await rag.insert_content_list(
            content_list,
            file_path=f"orgs/{org_id}",
            doc_id=f"org-{org_id}",
        )
    
    try:
        asyncio.run(_index())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**LightRAG streaming query with conversation history:**

```python
from lightrag import QueryParam

param = QueryParam(
    mode="mix",                        # hybrid KG + vector (best for service discovery)
    stream=True,                       # returns AsyncIterator[str]
    conversation_history=[             # list of {"role": "user"/"assistant", "content": "..."}
        {"role": "user", "content": "I need housing help"},
        {"role": "assistant", "content": "Here are some options..."},
    ],
    response_type="Single Paragraph",  # warm, readable responses
)
# aquery returns AsyncIterator[str] when stream=True
response_iter = await rag.lightrag.aquery(user_message, param=param)
async for chunk in response_iter:
    yield f"data: {chunk}\n\n"
```

[VERIFIED: lightrag/lightrag.py aquery, QueryParam source — conversation_history + stream fields confirmed]

**Recommended approach:** Install `raganything==1.2.10 --no-deps`. Use `insert_content_list()` for all indexing (orgs, services, pathways, PDFs). Use `lightrag.llm.gemini.gemini_model_complete` as llm_model_func. Wrap sentence-transformers with `EmbeddingFunc`. Use `asyncio.run()` in Celery tasks.

**Caveats:**
- `--no-deps` install must be documented in requirements.txt and in Wave 0 setup instructions. [VERIFIED blocker]
- RAGAnything's `working_dir` creates local JSON files even with PG backend (LightRAG's LLM cache). Plan must ensure this directory is writable. [ASSUMED: directory must exist]
- Set `TIKTOKEN_CACHE_DIR` env var to a local path to prevent tiktoken network requests on cold start. [ASSUMED: standard LightRAG practice]

---

## Area 2: pgvector Docker Setup

**Finding:**

The current `docker-compose.yml` uses `postgres:16-alpine` — this does NOT include pgvector. One line must change. [VERIFIED: docker-compose.yml read, 2026-04-13]

**Correct image:** `pgvector/pgvector:pg16` — the official pgvector Docker image. Current version: 0.8.2-pg16. [VERIFIED: hub.docker.com/r/pgvector/pgvector, 2026-04-13]

**Updated docker-compose.yml db service (only change is the image line):**

```yaml
services:
  db:
    image: pgvector/pgvector:pg16     # was: postgres:16-alpine
    environment:
      POSTGRES_DB: support2thrive
      POSTGRES_USER: support2thrive
      POSTGRES_PASSWORD: support2thrive_dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

**pgvector Django migration — use `VectorExtension`:**

`pgvector.django` does NOT require an INSTALLED_APPS entry — confirmed: no AppConfig in the package. [VERIFIED: pgvector.django package inspection, 2026-04-13]

The migration approach uses `VectorExtension` (a `CreateExtension` subclass that Django 6.0 natively supports):

```python
# apps/assistant/migrations/0001_initial.py
from pgvector.django import VectorExtension

class Migration(migrations.Migration):
    operations = [
        VectorExtension(),   # CREATE EXTENSION IF NOT EXISTS vector
        # ... all model creation operations below
    ]
```

`VectorExtension` handles `IF NOT EXISTS` — safe to run multiple times. [VERIFIED: pgvector.django.extensions source]

**LightRAG PostgreSQL config — environment variables only:**

LightRAG's `ClientManager.get_config()` reads exclusively from environment variables (or `config.ini` fallback). No additional Python config object is needed. The required env vars are: [VERIFIED: lightrag/kg/postgres_impl.py ClientManager.get_config, 2026-04-13]

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=support2thrive
POSTGRES_PASSWORD=support2thrive_dev_password
POSTGRES_DATABASE=support2thrive
POSTGRES_WORKSPACE=support2thrive_rag    # namespace for LightRAG rows — isolates from Django app rows
POSTGRES_MAX_CONNECTIONS=10
```

These must be added to `.env` for Docker-based development. Django's `DATABASE_URL` is separate and should also be updated to `postgresql://support2thrive:support2thrive_dev_password@localhost:5432/support2thrive`. [VERIFIED: base.py DATABASE_URL read via env.db()]

**LightRAG tables auto-created in Postgres (no Django migration needed):**

LightRAG handles its own DDL on first `_ensure_lightrag_initialized()` call. The tables it creates: [VERIFIED: postgres_impl.py, 2026-04-13]

- `LIGHTRAG_DOC_FULL` — full document content + metadata
- `LIGHTRAG_DOC_CHUNKS` — chunked text
- `LIGHTRAG_DOC_STATUS` — per-document indexing status
- `LIGHTRAG_LLM_CACHE` — cached LLM call responses
- `LIGHTRAG_FULL_ENTITIES` — knowledge graph entities
- `LIGHTRAG_FULL_RELATIONS` — knowledge graph relations
- `LIGHTRAG_VDB_CHUNKS` — vector embeddings for chunks (pgvector column)
- `LIGHTRAG_VDB_ENTITY` — vector embeddings for entities
- `LIGHTRAG_VDB_RELATION` — vector embeddings for relations
- `LIGHTRAG_ENTITY_CHUNKS` — chunk-to-entity links
- `LIGHTRAG_RELATION_CHUNKS` — chunk-to-relation links

These coexist with Django's tables in the same database. The `POSTGRES_WORKSPACE` setting adds a workspace column for row-level namespace isolation. Plan should document these table names to avoid confusion.

**asyncpg vs psycopg2:** LightRAG uses `asyncpg==0.31.0` (already installed, confirmed). Django uses `psycopg2-binary==2.9.11` (already installed). Both connect to the same Postgres instance simultaneously without conflict. [VERIFIED: pip show asyncpg]

**Recommended approach:** Change docker-compose.yml image to `pgvector/pgvector:pg16`. Add 7 POSTGRES_* env vars + updated DATABASE_URL to `.env`. Add `VectorExtension()` as first operation in `apps/assistant/migrations/0001_initial.py`.

---

## Area 3: Obsidian Vault Sync Strategy

**DEFERRED per PHASE-6-CONTEXT.md.** Obsidian vault sync is explicitly out of scope for Phase 6.

**What Phase 6 does instead:** Post-save signals on Organization, OrganizationService, ServiceCategory, Pathway, PathwaySection, PathwayGuideItem dispatch Celery tasks that call `insert_content_list()` directly from Django model instances. No filesystem writes, no watchdog daemon, no Markdown vault files in Phase 6.

`watchdog==6.0.0` is already installed in requirements.txt and will be used in a future phase. No action in Phase 6.

---

## Area 4: OrgDocument Model for PDF Uploads

**Finding:**

`apps/assistant/models.py` is currently empty (1 line). All models must be built from scratch.

`MEDIA_URL = "media/"` and `MEDIA_ROOT = BASE_DIR / "media"` are already configured in `base.py`. [VERIFIED: config/settings/base.py]

**Recommended OrgDocument model:**

```python
from django.db import models
from django.core.validators import FileExtensionValidator
from apps.core.models import TimeStampedModel

def org_doc_upload_path(instance, filename):
    return f"org_documents/{instance.org.slug}/{filename}"

class OrgDocument(TimeStampedModel):
    org = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=org_doc_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    indexed_at = models.DateTimeField(null=True, blank=True)
    index_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Org Document"
        verbose_name_plural = "Org Documents"
```

**Size validation in form (preferred over model.clean):**

```python
# In apps/assistant/forms.py
class OrgDocumentForm(forms.ModelForm):
    def clean_file(self):
        f = self.cleaned_data.get("file")
        if f and f.size > 20 * 1024 * 1024:
            raise forms.ValidationError("PDF must be under 20MB.")
        return f
```

**Celery task pattern — follows referrals/tasks.py exactly:**

```python
# apps/assistant/tasks.py
@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def index_org_document(self, document_id: int):
    from .services import process_org_document
    try:
        process_org_document(document_id)
    except Exception as exc:
        logger.exception("PDF indexing failed for document %s", document_id)
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))
```

**Service layer (apps/assistant/services.py):**

```python
def process_org_document(document_id: int):
    import asyncio, pymupdf4llm
    from .models import OrgDocument
    from django.utils import timezone

    doc = OrgDocument.objects.select_related("org").get(pk=document_id)
    pdf_path = doc.file.path

    # Extract text via pymupdf4llm
    md_text = pymupdf4llm.to_markdown(pdf_path, show_progress=False)
    content_list = [
        {"type": "text", "text": chunk, "page_idx": i}
        for i, chunk in enumerate(split_markdown(md_text))
    ]

    async def _index():
        from apps.assistant.rag_service import get_rag_instance
        rag = await get_rag_instance()
        await rag.insert_content_list(
            content_list,
            file_path=f"documents/{doc.org.slug}/{doc.title}",
            doc_id=f"orgdoc-{document_id}",
        )

    asyncio.run(_index())
    doc.indexed_at = timezone.now()
    doc.index_error = ""
    doc.save(update_fields=["indexed_at", "index_error"])
```

**Recommended approach:** Single `OrgDocument` model in `apps/assistant/models.py`. Upload via org portal. Celery task on upload; `asyncio.run()` calls RAGAnything's `insert_content_list`. `indexed_at` set on success; `index_error` captures failure message.

---

## Area 5: HTMX Streaming with SSE

**Finding:**

HTMX 2.0.4 is loaded in `base.html`. SSE is a SEPARATE extension in HTMX 2.0 — it was removed from core and must be loaded explicitly. [VERIFIED: templates/base.html, htmx.org SSE extension docs, 2026-04-13]

**SSE extension CDN:** `https://unpkg.com/htmx-ext-sse@2.2.4/sse.js` [VERIFIED: npmjs.com/package/htmx-ext-sse]

Load ONLY in the assistant template's `{% block extra_head %}` — not in base.html globally.

**HTML pattern:**

```html
<!-- In templates/assistant/chat.html -->
{% block extra_head %}
<script src="https://unpkg.com/htmx-ext-sse@2.2.4/sse.js"></script>
{% endblock %}

<!-- Chat history display -->
<div id="chat-messages" class="...">
  <!-- Previous messages rendered here -->
</div>

<!-- Streaming response target -->
<div id="response-area"
     hx-ext="sse"
     sse-connect="/en/assistant/stream/?sid={{ stream_id }}"
     sse-swap="message"
     sse-close="done">
</div>

<!-- Send message form -->
<form hx-post="{% url 'assistant:chat' %}"
      hx-target="#chat-messages"
      hx-swap="beforeend"
      hx-on::after-request="this.reset()">
  {% csrf_token %}
  <input name="message" type="text" autocomplete="off" required
         placeholder="{% trans 'Ask about services...' %}">
  <button type="submit">{% trans "Send" %}</button>
</form>
```

**Django SSE view:**

```python
# apps/assistant/views.py

def assistant_stream(request):
    """SSE endpoint — streams LightRAG response chunk-by-chunk."""
    import asyncio
    from apps.assistant.rag_service import get_rag_instance
    from lightrag import QueryParam

    message = request.session.get("pending_assistant_message", "")
    history = request.session.get("chat_history", [])

    def event_stream():
        async def _stream_chunks():
            rag = await get_rag_instance()
            param = QueryParam(
                mode="mix",
                stream=True,
                conversation_history=history[-20:],  # cap at 10 turns
            )
            async for chunk in await rag.lightrag.aquery(message, param=param):
                yield f"data: {chunk}\n\n"
            yield "event: done\ndata: \n\n"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            agen = _stream_chunks()
            while True:
                try:
                    yield loop.run_until_complete(agen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    response = StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"   # critical for nginx not to buffer SSE
    return response
```

**Critical production requirement:** Django's gunicorn WSGI server buffers responses — SSE requires a non-buffering worker. Options: [ASSUMED: deployment target not yet confirmed]
1. Use `gunicorn --worker-class=gthread` with `X-Accel-Buffering: no` (partial mitigation)
2. Switch to `uvicorn` ASGI server (recommended — fully non-buffering)
3. Fallback: HTMX polling every 2s to a regular JSON endpoint (simpler, loses streaming)

**Simpler fallback (polling pattern) if SSE proves too complex:**

```html
<div id="response-area"
     hx-get="{% url 'assistant:poll' %}?sid={{ sid }}"
     hx-trigger="every 2s [window.pendingResponse]"
     hx-swap="innerHTML">
</div>
```

**Recommended approach:** SSE with `htmx-ext-sse@2.2.4` for dev. Wave 0 must include a decision on production worker (uvicorn vs gunicorn). If uvicorn is not feasible, plan must include polling fallback.

---

## Area 6: Crisis Detection

**Finding:**

Crisis detection must happen BEFORE the RAG query — check user message, prepend emergency contacts if matched, then run RAG for the additional service information.

**Recommended `apps/assistant/crisis.py`:**

```python
CRISIS_KEYWORDS = {
    "self_harm": [
        "hurt myself", "self harm", "self-harm", "cutting myself",
        "burn myself", "harm myself",
    ],
    "suicidal": [
        "kill myself", "end my life", "suicide", "suicidal",
        "want to die", "not want to be here", "don't want to live",
        "no reason to live", "take my own life",
    ],
    "rough_sleeping_emergency": [
        "nowhere to sleep tonight", "sleeping outside tonight",
        "no shelter tonight", "rough sleeping", "sleeping rough",
        "emergency housing", "on the streets tonight",
    ],
    "domestic_violence": [
        "being hit", "partner hitting me", "domestic violence",
        "being abused", "afraid of my partner", "unsafe at home",
        "he hits me", "she hits me",
    ],
    "immediate_danger": [
        "in danger now", "being attacked", "help me now",
    ],
}

# Numbers verified [ASSUMED — user must confirm before deployment]
WM_CRISIS_RESPONSE = (
    "**If you're in immediate danger, please call 999 now.**\n\n"
    "**Free 24/7 support:**\n"
    "- Samaritans: **116 123** (free, any time)\n"
    "- Crisis text line: Text SHOUT to **85258**\n"
    "- BVSC Wellbeing (West Midlands): **0800 111 4187**\n\n"
    "**Emergency housing (West Midlands):**\n"
    "- Wolverhampton Housing Advice: **01902 556789** [VERIFY BEFORE DEPLOY]\n"
    "- Birmingham City Council: **0121 303 7410** [VERIFY BEFORE DEPLOY]\n\n"
    "---\n\n"
)


def detect_crisis(message: str) -> bool:
    msg_lower = message.lower()
    for keywords in CRISIS_KEYWORDS.values():
        if any(kw in msg_lower for kw in keywords):
            return True
    return False


def build_crisis_prefix(message: str) -> str:
    """Returns crisis signpost text if crisis detected, else empty string."""
    if detect_crisis(message):
        return WM_CRISIS_RESPONSE
    return ""
```

In the chat view:

```python
crisis_prefix = build_crisis_prefix(user_message)
# crisis_prefix prepended to the streamed response if non-empty
```

**Recommended approach:** Standalone `crisis.py` module. Simple substring matching on lowercased message. Never refuse — prepend help then continue with RAG. Phone numbers must be verified by user before deployment.

**Caveats:** [ASSUMED] WM local authority phone numbers — must be verified.

---

## Area 7: Django Model Design for apps/assistant/

**Finding:** `apps/assistant/models.py` is currently empty. All models built from scratch. LightRAG manages its own 11 internal tables — no `ContentEmbedding` model is needed in Django models.

**Full model file:**

```python
# apps/assistant/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class Conversation(models.Model):
    """
    Ties a chat session to a Django session key.
    Created on first message; no login required.
    """
    session_key = models.CharField(_("session key"), max_length=40, db_index=True, unique=True)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    last_active = models.DateTimeField(_("last active"), auto_now=True)

    class Meta:
        ordering = ["-last_active"]
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")

    def __str__(self):
        return f"Conversation {self.session_key[:8]}..."


class ConversationMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = [
        (ROLE_USER, _("User")),
        (ROLE_ASSISTANT, _("Assistant")),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("conversation"),
    )
    role = models.CharField(_("role"), max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(_("content"))
    sources = models.JSONField(_("sources"), null=True, blank=True)
    # sources format: [{"name": "org name", "url": "/en/organizations/slug/"}]
    crisis_detected = models.BooleanField(_("crisis detected"), default=False)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Conversation Message")
        verbose_name_plural = _("Conversation Messages")


def org_doc_upload_path(instance, filename):
    return f"org_documents/{instance.org.slug}/{filename}"


class OrgDocument(TimeStampedModel):
    """Org-uploaded PDFs — parsed and indexed into LightRAG knowledge graph."""
    org = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("organisation"),
    )
    title = models.CharField(_("title"), max_length=255)
    file = models.FileField(
        _("file"),
        upload_to=org_doc_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("uploaded by"),
    )
    indexed_at = models.DateTimeField(_("indexed at"), null=True, blank=True)
    index_error = models.TextField(_("index error"), blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Org Document")
        verbose_name_plural = _("Org Documents")

    def __str__(self):
        return f"{self.org.name} — {self.title}"
```

**Session history strategy:**
- `request.session["chat_history"]` stores `[{"role": ..., "content": ...}]` — cap at 20 items (10 turns)
- `Conversation` + `ConversationMessage` models are for admin visibility and rate-limit counting
- After each exchange: append to session AND save to DB (DB records are not used for RAG context — session is)
- `request.session.save()` must be called before reading `request.session.session_key` [ASSUMED: Django lazy session creation]

---

## Area 8: Python 3.14 Compatibility

**All findings verified against installed packages and PyPI, 2026-04-13:**

| Package | Status | Version | Notes |
|---------|--------|---------|-------|
| `lightrag-hku` | INSTALLED, WORKING | 1.4.14 | cpython-314 bytecache confirmed |
| `sentence-transformers` | INSTALLED, WORKING | 5.4.0 | Tested in this session |
| `google-genai` | INSTALLED, WORKING | 1.72.0 | New SDK; use this NOT google.generativeai |
| `google.generativeai` | DEPRECATED | 0.8.6 | FutureWarning shown — do not use |
| `asyncpg` | INSTALLED, WORKING | 0.31.0 | Used by LightRAG PG backend |
| `aiohttp` | INSTALLED, WORKING | 3.13.5 | Used by LightRAG internally |
| `raganything==1.2.10` | NOT INSTALLED | available | Install with `--no-deps` only |
| `pymupdf4llm==1.27.2.2` | NOT INSTALLED | available | No Python 3.14 blockers in dry-run |
| `mineru` (any version) | PERMANENTLY BLOCKED | requires <3.14 | Never install — use insert_content_list |

**BLOCKER RESOLVED:** `pip install raganything --no-deps` confirmed clean on Python 3.14.3. All required functionality is accessible through `insert_content_list()` which bypasses the parser layer entirely.

**requirements.txt additions needed:**

```
# Install with: pip install raganything==1.2.10 --no-deps (mineru dep incompatible with Python 3.14)
raganything==1.2.10
pymupdf4llm==1.27.2.2
# Remove:
# PyPDF2==3.0.1   (deprecated, replace with pymupdf4llm)
```

---

## Area 9: Rate Limiting

**Finding:**

No existing rate-limiting infrastructure for the assistant endpoint. Django-axes is for login brute-force only. The session-based approach fits Phase 6 scope.

**Recommended `apps/assistant/rate_limit.py`:**

```python
from django.utils import timezone

RATE_LIMIT_SESSION_MAX = 20   # total messages per session lifecycle
RATE_LIMIT_MINUTE_MAX = 5     # messages per rolling 60-second window


def check_rate_limit(request) -> tuple[bool, str]:
    """
    Returns (is_allowed, error_message).
    All state stored in request.session.
    """
    session = request.session

    # Session budget check
    total = session.get("assistant_msg_count", 0)
    if total >= RATE_LIMIT_SESSION_MAX:
        return False, "You've reached the session message limit. Please start a new session to continue."

    # Per-minute throttle
    now = timezone.now().timestamp()
    recent = [t for t in session.get("assistant_msg_times", []) if now - t < 60]
    if len(recent) >= RATE_LIMIT_MINUTE_MAX:
        return False, "Please wait a moment before sending another message."

    # Update counters
    recent.append(now)
    session["assistant_msg_count"] = total + 1
    session["assistant_msg_times"] = recent
    session.modified = True

    return True, ""
```

**HTMX-friendly error response (return 200 with error markup):**

HTMX 2.0 does not swap 4xx responses by default. Return HTTP 200 with error HTML to ensure HTMX swaps it into the target:

```python
def chat_view(request):
    if request.method == "POST":
        allowed, error_msg = check_rate_limit(request)
        if not allowed:
            return HttpResponse(
                f'<div class="rounded-xl p-3 bg-amber-50 border border-amber-200 text-amber-800 text-sm">'
                f'{error_msg}</div>',
                status=200,
                content_type="text/html",
            )
        # ... proceed with RAG
```

**Django settings for configurability:**

```python
# config/settings/base.py additions
ASSISTANT_RATE_LIMIT_SESSION = env.int("ASSISTANT_RATE_LIMIT_SESSION", default=20)
ASSISTANT_RATE_LIMIT_MINUTE = env.int("ASSISTANT_RATE_LIMIT_MINUTE", default=5)
```

**Recommended approach:** Session-based counter + rolling timestamp list. Thresholds configurable via env vars. HTMX-safe 200 response with styled error markup. IP-based rate limiting deferred.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Django test runner |
| Config file | `config/settings/test.py` (existing, uses SQLite) |
| Quick run | `python manage.py test apps.assistant --settings=config.settings.test` |
| Full suite | `python manage.py test --settings=config.settings.test` |

**SQLite note:** Test settings must skip or mock all LightRAG/pgvector calls. Add `SKIP_RAG_TESTS = env.bool("SKIP_RAG_TESTS", default=True)` to test settings.

### Phase Requirements to Test Map

| Behavior | Test Type | Strategy |
|----------|-----------|----------|
| `index_organization` task builds correct content_list shape | Unit | Mock `insert_content_list`, assert content_list items have required keys |
| `index_org_document` extracts PDF text and calls insert_content_list | Unit | Mock pymupdf4llm + RAG, assert call args |
| `/assistant/stream/` returns `text/event-stream` content-type | Integration | `self.assertEqual(response["Content-Type"], "text/event-stream")` |
| SSE stream closes with `event: done` | Integration | Consume stream, assert "event: done" present |
| `detect_crisis("want to die")` returns True | Unit | 15+ keyword assertions across all 5 crisis categories |
| `detect_crisis("find housing near me")` returns False | Unit | Assert no false positives on common service queries |
| Response contains Samaritans number when crisis detected | Integration | Mock RAG, post crisis message, assert "116 123" in response |
| Session history capped at 20 items (10 turns) | Unit | Add 25 messages, assert session["chat_history"] len <= 20 |
| `QueryParam.conversation_history` populated from session | Unit | Mock aquery, assert param passed with history items |
| PDF > 20MB rejected | Unit | Upload 21MB file in form, assert validation error |
| Non-PDF extension rejected | Unit | Upload .docx, assert FileExtensionValidator error |
| 21st message returns rate limit error | Unit | Set session count=20, assert check_rate_limit returns False |
| Per-minute throttle: 6th message in 60s rejected | Unit | Set 5 recent timestamps within 60s, assert throttled |
| `indexed_at` set after successful Celery task | Integration | Run task with mocked RAG, assert indexed_at not null |
| `index_error` set after Celery task failure | Integration | Raise exception in mock, assert index_error contains message |
| VectorExtension migration runs on Postgres | Integration | Requires Postgres — skip with SKIP_RAG_TESTS flag |

### Wave 0 Test Gaps

- `apps/assistant/tests/__init__.py` — create test package
- `apps/assistant/tests/test_crisis.py` — crisis detection unit tests
- `apps/assistant/tests/test_rate_limit.py` — rate limiting unit tests
- `apps/assistant/tests/test_views.py` — chat view + SSE endpoint
- `apps/assistant/tests/test_tasks.py` — Celery task mocking (mock insert_content_list)
- `apps/assistant/tests/test_models.py` — OrgDocument validation (file size, extension)

---

## Sources

### Primary (HIGH confidence — verified in this session via code inspection)
- `lightrag-hku==1.4.14` — `kg/postgres_impl.py` (tables, env vars, ClientManager), `llm/gemini.py` (gemini_model_complete), `lightrag.py` (aquery, QueryParam), `utils.py` (EmbeddingFunc)
- `raganything-1.2.10.whl` — extracted and inspected: `__init__.py`, `raganything.py`, `processor.py` (insert_content_list), `parser.py` (register_parser, MineruParser, Parser ABC), `batch.py`
- `pip install raganything==1.2.10 --dry-run` — confirmed `mineru[core]` blocker
- `pip install raganything==1.2.10 --no-deps --dry-run` — confirmed clean
- `asyncio.run()` — confirmed working in Python 3.14.3 sync context
- `pip show asyncpg` — 0.31.0 installed
- `pip show google-genai` — 1.72.0; `google.generativeai` deprecated (FutureWarning confirmed)
- PyPI `mineru` page — Python `<3.14, >=3.10` confirmed (via WebFetch)
- `pgvector.django` source — VectorExtension confirmed, no AppConfig
- `config/settings/base.py`, `docker-compose.yml`, `templates/base.html`, `config/urls.py` — all read in this session

### Secondary (MEDIUM confidence)
- [htmx.org/extensions/sse/](https://htmx.org/extensions/sse/) — SSE extension attributes confirmed
- [npmjs.com/package/htmx-ext-sse](https://www.npmjs.com/package/htmx-ext-sse/v/2.2.0) — version 2.2.4 confirmed
- [hub.docker.com/r/pgvector/pgvector](https://hub.docker.com/r/pgvector/pgvector) — pg16 image, version 0.8.2 confirmed

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `asyncio.run()` in Celery tasks has no event-loop conflict on Python 3.14 | Area 1 | Could raise "event loop already running" — mitigation: check `asyncio.get_running_loop()` before calling run() |
| A2 | Django dev server (`runserver`) streams SSE without buffering | Area 5 | Streaming may appear frozen during development — mitigation: test early with curl |
| A3 | Production deployment needs ASGI worker (uvicorn/daphne) for true SSE streaming | Area 5 | gunicorn WSGI buffers SSE — users see blank response until complete |
| A4 | WM emergency housing phone numbers (Wolverhampton 01902 556789, Birmingham 0121 303 7410) | Area 6 | Phone numbers change — MUST be verified by user before launch |
| A5 | `request.session.session_key` available after explicit `request.session.save()` | Area 7 | Django creates sessions lazily — missing save() call means session_key is None |
| A6 | LightRAG `working_dir` local JSON cache is writable in production container | Area 1 | If container is read-only filesystem, LightRAG init will fail — set working_dir to /tmp |
| A7 | `TIKTOKEN_CACHE_DIR` must be set to prevent tiktoken downloading data at runtime | Area 1 | First request may be slow/fail if network is restricted in production |
| A8 | `all-MiniLM-L6-v2` (384-dim) retrieval quality is sufficient for community services queries | Area 1 | Recommendation: use all-mpnet-base-v2 (768-dim) if early testing shows poor recall |

---

## Open Questions

1. **ASGI vs WSGI for SSE in production**
   - What we know: Django runserver supports streaming; gunicorn WSGI buffers
   - What's unclear: Production deployment target not specified in CONTEXT.md
   - Recommendation: Plan must include Wave 0 decision — add `uvicorn` to requirements.txt, or design polling fallback

2. **LightRAG working_dir in production container**
   - What we know: LightRAG writes JSON cache files to working_dir even with PG backend
   - What's unclear: Whether production Docker container has a writable working directory
   - Recommendation: Set `LIGHTRAG_WORKING_DIR=/tmp/rag_storage` env var; add to .env template

3. **Gemini API call count during LightRAG indexing**
   - What we know: LightRAG's knowledge graph construction calls the LLM multiple times per document for entity/relation extraction
   - What's unclear: Exact call count per document and cost implications for bulk indexing of all orgs
   - Recommendation: Set `llm_model_max_async=2` in LightRAG init; add `@shared_task(rate_limit="2/m")`; run initial index on a subset first

4. **pgvector migration ordering constraint**
   - What we know: `VectorExtension()` must be first operation before any VectorField column
   - What's unclear: Since LightRAG manages its own tables (no VectorField in Django models), this is precautionary
   - Recommendation: Still include `VectorExtension()` as first op in `0001_initial.py` — safe to include, required for correctness

5. **Conversation + ConversationMessage vs session-only history**
   - What we know: CONTEXT.md says "no DB persistence for Phase 6" but Conversation/ConversationMessage models are useful for rate-limit counting and admin visibility
   - What's unclear: Whether admin visibility of conversations is in scope
   - Recommendation: Include the models (they add no user-facing complexity), but mark them as internal admin tooling

---

## Environment Availability

| Dependency | Required By | Available | Version | Action |
|------------|------------|-----------|---------|--------|
| Python | All | Yes | 3.14.3 | — |
| lightrag-hku | RAG core | Yes | 1.4.14 | — |
| sentence-transformers | Embeddings | Yes | 5.4.0 | — |
| google-genai | Gemini LLM | Yes | 1.72.0 | — |
| asyncpg | LightRAG PG backend | Yes | 0.31.0 | — |
| aiohttp | LightRAG internals | Yes | 3.13.5 | — |
| psycopg2-binary | Django + Postgres | Yes | 2.9.11 | — |
| pgvector (Django) | VectorExtension migration | Yes | 0.4.2 | — |
| raganything | RAG pipeline | No | 1.2.10 on PyPI | Wave 0: pip install raganything==1.2.10 --no-deps |
| pymupdf4llm | PDF text extraction | No | 1.27.2.2 on PyPI | Wave 0: pip install pymupdf4llm==1.27.2.2 |
| pgvector/pgvector:pg16 | Vector DB | No (wrong Docker image) | 0.8.2-pg16 | Wave 0: update docker-compose.yml image |
| htmx-ext-sse | SSE streaming | No (CDN, not bundled) | 2.2.4 | Load via CDN in assistant template |
| mineru | Parser (NOT NEEDED) | Blocked (Python 3.14) | never | Use insert_content_list bypass |

**Missing dependencies blocking Phase 6:**
- `raganything==1.2.10 --no-deps` — Wave 0 pip install
- `pymupdf4llm==1.27.2.2` — Wave 0 pip install
- `pgvector/pgvector:pg16` — Wave 0 docker-compose.yml change (single line)
