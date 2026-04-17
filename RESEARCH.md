# PDF Processing for RAG Pipeline — Research

**Researched:** 2026-04-13
**Domain:** Python PDF parsing, OCR, multimodal RAG, Celery task integration
**Confidence:** HIGH (all library versions verified against PyPI registry; architecture patterns cross-referenced with official docs and 2025/2026 benchmarks)

---

## Summary

This research compares six Python PDF processing libraries for the Support2Thrive Phase 6 RAG pipeline. The use case is admin-uploaded PDFs (service directories, guidance documents, org brochures) processed into text chunks + image descriptions for vector embedding into pgvector via Celery background tasks.

The candidate libraries split into two tiers: **rule-based extractors** (PyMuPDF, pdfplumber, pypdf/PyPDF2) that parse PDF internals fast with no ML overhead, and **ML-based converters** (unstructured, marker-pdf, docling) that apply AI models for layout understanding and OCR. For the Support2Thrive use case — lightweight Celery workers, no GPU, existing PyTorch CPU install, Gemini 2.5 Flash already integrated — the right answer is a rule-based extractor paired with targeted Gemini vision calls for image pages. This avoids downloading gigabytes of competing ML models.

**Primary recommendation:** Use `pymupdf4llm==1.27.2.2` as the text extraction core, with PyMuPDF's `page.get_pixmap()` to render image-heavy or scanned pages as PNGs sent to Gemini 2.5 Flash vision for description. Replace the existing `PyPDF2==3.0.1` (deprecated) in requirements.txt. Add `pytesseract` + Tesseract binary only as a fallback for offline/bulk-scanned-doc scenarios.

---

## Project Constraints (from CLAUDE.md)

- **Backend:** Django 6.0.x + DRF
- **Database:** SQLite dev / PostgreSQL + pgvector prod
- **Task Queue:** Celery 5.6.3 + Redis (already configured)
- **AI/RAG:** pgvector 0.4.2, sentence-transformers 5.4.0 (already installed), Gemini 2.5 Flash
- **Python version:** 3.14.3 (verified in venv)
- **PyTorch:** 2.11.0+cpu (CPU-only, already installed for sentence-transformers)
- **Pillow:** 12.2.0 (already installed)
- **google-generativeai:** already installed
- **PyPDF2==3.0.1:** currently in requirements.txt — deprecated, must be replaced
- **No heavy cloud dependencies:** self-hosted/local preferred
- **Celery workers:** must be lean — no GPU ML model loading in workers
- **Security/privacy first:** GDPR, encrypted PII, audit logging are first-class

---

## Library Comparison Table

| Library | Latest Version | Python Support | Install Size (wheel) | ML Models? | OCR Built-in? | Image Extraction | Tables | License | Celery-Safe? |
|---------|---------------|----------------|---------------------|------------|---------------|------------------|--------|---------|-------------|
| **pymupdf4llm** | 1.27.2.2 (2026-03-20) | 3.10–3.14 | ~85 MB (PyMuPDF base) + 84 kB (wrapper) | None | Via Tesseract (optional) | Yes — pixels + path refs | Good (ported from pdfplumber) | AGPL-3.0 | Yes |
| **PyMuPDF** (fitz) | 1.27.2.2 (2026-03-19) | 3.10–3.14 | ~85 MB | None | Via Tesseract (optional) | Yes — pixmap render per page | Good | AGPL-3.0 | Yes |
| **pdfplumber** | 0.11.9 (2026-01-05) | 3.8+ | ~60 kB (+ pdfminer.six, pypdfium2) | None | No | Metadata only — no image bytes | Excellent | MIT | Yes |
| **pypdf** (replaces PyPDF2) | 6.9.2 (stable) | 3.8+ | ~200 kB | None | No | Broken/distorted (known issue) | None | BSD-3-Clause | Yes |
| **PyPDF2** | 3.0.1 (DEPRECATED) | 3.8+ | ~300 kB | None | No | Limited, buggy | None | BSD-3-Clause | Yes (but don't use) |
| **marker-pdf** | 1.10.2 | 3.10+ | PyTorch + 4 ML models (~several GB total) | Yes (4 models) | Yes (built-in) | Inline images in markdown | Good | GPL-3.0 + Rail-M weights | Risky (model init per task) |
| **unstructured** | 0.22.18 (2026-04-08) | 3.11–3.13 | 1.6 MB (+ poppler, tesseract system deps) | Optional (hi_res) | Via Tesseract/PaddleOCR | Via hi_res strategy | Good (hi_res) | Apache-2.0 | Yes (strategy-dependent) |
| **docling** | 2.88.0 | 3.10+ | PyTorch + HuggingFace models (~9.74 GB Docker default; 1.74 GB CPU-only) | Yes (TableFormer, Layout) | Yes (built-in) | Yes | Excellent | MIT | Risky (model init, first-run HF download) |

[VERIFIED: PyPI registry — all versions and dates confirmed 2026-04-13]
[VERIFIED: PyPI — Python version ranges confirmed from package metadata]

---

## Detailed Candidate Analysis

### 1. pymupdf4llm (RECOMMENDED)

**pip package:** `pymupdf4llm`
**Install:** `pip install pymupdf4llm` (auto-installs PyMuPDF + PyMuPDFb)
**Size:** PyMuPDF wheel ~85 MB, pymupdf4llm wrapper 84 kB — no additional model downloads
**Python:** 3.10–3.14 (Python 3.14 wheels confirmed available)

`pymupdf4llm` is a thin official wrapper around PyMuPDF designed specifically for LLM/RAG output. It converts any PDF page to clean Markdown with table formatting, heading detection, and image path references baked in. The `write_images=True` parameter saves extracted embedded images to disk; the `image_size_limit` parameter (default 0.05) filters out tiny decorative elements.

**Celery behaviour:** Stateless — opens document, extracts, closes. Safe to use from multiple workers simultaneously. No global model state, no warm-up latency.

**OCR strategy with PyMuPDF:** `page.get_textpage_ocr(language="eng", dpi=300, full=False)` delegates to Tesseract if installed. As of v1.27.2, the `full=False` mode now also OCRs vector graphics regions and illegible text — not just image areas. The result TextPage object is then reused for all subsequent extractions on that page (avoiding repeated OCR calls). [VERIFIED: PyMuPDF changelog 1.27.2, 2026-03-10]

**Image handling pattern:** For pages that are predominantly images (scanned documents, photo-heavy brochures):
1. Detect image-heavy pages: `page.get_image_info()` returns list — if images cover > 70% of page area, treat as image page
2. Render full page as PNG: `pix = page.get_pixmap(dpi=150); img_bytes = pix.tobytes("png")`
3. Send `img_bytes` to Gemini 2.5 Flash vision via `google.generativeai` (already installed) for a description
4. Store the description as a text chunk, tagged with page number and source PDF

**License caveat:** PyMuPDF is AGPL-3.0. For an open-source or internal community platform this is fine. If Support2Thrive becomes commercially distributed software, a commercial license from Artifex is required. [VERIFIED: Artifex licensing page]

---

### 2. PyMuPDF (fitz) — Core of Option 1

This is the underlying engine of `pymupdf4llm`. Can be used directly if lower-level control is needed (e.g., per-block text extraction with coordinates, selective OCR). For this use case, `pymupdf4llm` is preferred as it handles LLM-oriented chunking automatically.

---

### 3. pdfplumber — Supporting Role Only

**pip package:** `pdfplumber`
**Install:** `pip install pdfplumber`
**Size:** 60 kB wheel; pulls in pdfminer.six and pypdfium2

Excellent for structured tables (uses exact character position data, not whitespace heuristics). However it **does not extract image bytes** — only reports image metadata (coordinates, dimensions). [VERIFIED: pdfplumber 0.11.9 PyPI page, documentation]

**Use case:** If a PDF is known to be a structured table-heavy document (e.g., a service tariff or funding matrix), pdfplumber's table extraction is more reliable than PyMuPDF's. Consider a routing step in the Celery task: detect table-heavy PDFs and run pdfplumber for table chunks, pymupdf4llm for all other content.

---

### 4. pypdf (replaces PyPDF2)

**pip package:** `pypdf`
**Install:** `pip install pypdf`
**Current version in project:** PyPDF2==3.0.1 (deprecated predecessor)

**PyPDF2 is deprecated.** pypdf is the maintained successor; PyPDF2==3.0.1 should be removed from requirements.txt and replaced. However, neither PyPDF2 nor pypdf should be used as the primary extractor for this use case because:
- Image extraction has known distortion/scaling bugs (X/Y scale factors ignored, open issue as of April 2025) [CITED: https://github.com/py-pdf/pypdf/issues/3263]
- No OCR capability
- No table detection

**Action required:** Replace `PyPDF2==3.0.1` with `pypdf` in requirements.txt (or remove entirely once pymupdf4llm covers the use case — the two don't conflict).

---

### 5. marker-pdf — Not Recommended for This Stack

**pip package:** `marker-pdf`
**Latest version:** 1.10.2
**License:** GPL-3.0 code + modified AI Pubs Open Rail-M model weights (free for orgs under $2M revenue)

marker-pdf produces stunning layout-accurate markdown including inline images. In 2025 benchmarks it scored 95.67 vs competitors. However for Support2Thrive it has two blockers:

1. **Size and model loading:** Requires downloading ~several GB of PyTorch ML models on first run. With CPU-only torch already in the venv, these models will be slow (11.3 seconds per page in CPU benchmarks vs 0.14s for pymupdf4llm). [CITED: Medium 2025 benchmark]
2. **GPL-3.0 code license:** The project may not want to accept GPL copyleft obligations on the application code that imports marker-pdf.

If Support2Thrive ever deploys a dedicated PDF processing service (separate container, GPU available), marker-pdf becomes attractive. For the current Celery worker setup, it is impractical.

---

### 6. unstructured — Good Concept, Complexity Cost

**pip package:** `unstructured[pdf]`
**Latest version:** 0.22.18 (2026-04-08)
**License:** Apache-2.0

unstructured is purpose-built for RAG pre-processing and provides semantically labelled chunks (Title, NarrativeText, Table, Image). The `strategy="hi_res"` mode applies computer vision for layout detection. However:

1. Requires **system-level** `tesseract` and `poppler-utils` — these must be installed in the Docker container or on the server OS, not just via pip. [VERIFIED: unstructured PyPI page, 0.22.18]
2. `unstructured[pdf]` does not support Python 3.14 — it specifies `python_requires >= 3.11, < 3.14`. The project venv uses **Python 3.14.3**. [VERIFIED: unstructured 0.22.18 PyPI metadata]
3. Fast mode (no OCR) is similar quality to pymupdf4llm but with more dependencies.

**Python 3.14 incompatibility is a hard blocker** for the current environment. [VERIFIED: pip index confirms 0.18.32 is the highest version installable — cross-check needed before use]

---

### 7. docling (IBM) — Overkill for This Use Case

**pip package:** `docling`
**Latest version:** 2.88.0
**License:** MIT

docling is impressive for enterprise document intelligence — it uses TableFormer (a transformer model) and a layout detection model, downloaded from HuggingFace on first run. Docker image with default PyTorch: 9.74 GB. CPU-only optimised image: 1.74 GB. [VERIFIED: Shekhar Gulati blog, 2025-02-05]

The rapid release cadence (weekly version bumps from 2.66 to 2.88 in ~4 months) is a maintenance concern for a project where the PDF pipeline is not the core product. The HuggingFace model download on first Celery worker startup is also a deployment hazard.

---

## Image Handling Strategy Comparison

| Strategy | How It Works | Pros | Cons | Recommended For |
|----------|-------------|------|------|-----------------|
| **PyMuPDF + Gemini 2.5 Flash vision** | Render page as PNG via `page.get_pixmap(dpi=150)`, send bytes to Gemini vision API, store description as chunk | Uses already-integrated Gemini API; no new dependencies; very high description quality; handles scanned + embedded images equally | API cost per image (~$0.075/1K input tokens, ~258 tokens/image); requires internet for processing | **RECOMMENDED: All image-containing or scanned pages** |
| **PyMuPDF + pytesseract OCR** | `page.get_textpage_ocr()` delegates to Tesseract binary; produces text layer from image pages | Fully offline; no API cost; good for text-dense scanned docs | Requires Tesseract binary installed on server; ~80% accuracy on real-world docs; poor on handwriting/complex layouts; no understanding of diagrams | Offline fallback, bulk processing of text-heavy scanned docs |
| **marker-pdf built-in models** | 4 ML models process layout, OCR, image captioning end-to-end | Highest accuracy (95.67 benchmark score); inline images in markdown | GPL license; GBs of model downloads; 11.3s/page CPU; not practical in Celery workers without GPU | Dedicated GPU container, not Support2Thrive current setup |
| **pdfplumber image metadata only** | Reports image coordinates — no content extraction | Zero new deps | Cannot describe or extract image content | Not suitable for image-content RAG |

**Decision:** Implement Gemini vision as primary strategy. Pytesseract as optional offline fallback (org admin can configure per-upload or per-org). [ASSUMED — this specific routing decision is Claude's recommendation, not locked by user]

---

## Architecture Pattern for Celery Task

### Recommended Task Flow

```python
# apps/assistant/tasks.py
# Source: PyMuPDF4LLM docs + Gemini vision API pattern

import pymupdf4llm
import pymupdf
import base64
from celery import shared_task
from django.conf import settings
import google.generativeai as genai

@shared_task(bind=True, max_retries=3)
def process_pdf_document(self, document_id: int):
    """
    Process an uploaded PDF into text chunks + image descriptions
    for vector embedding into pgvector.
    
    Strategy:
    1. pymupdf4llm extracts text + table chunks as Markdown
    2. Image-heavy pages rendered as PNG and described by Gemini vision
    3. Text chunks embedded with sentence-transformers
    4. Vectors stored in ContentEmbedding model
    """
    from apps.assistant.models import DocumentUpload, ContentEmbedding
    
    doc_obj = DocumentUpload.objects.get(id=document_id)
    pdf_path = doc_obj.file.path
    
    # Step 1: Text extraction via pymupdf4llm
    md_text = pymupdf4llm.to_markdown(
        pdf_path,
        write_images=False,   # we handle images ourselves below
        show_progress=False,
    )
    text_chunks = chunk_markdown(md_text)  # custom chunker, ~500 tokens
    
    # Step 2: Image page detection + Gemini vision description
    doc = pymupdf.open(pdf_path)
    image_descriptions = []
    for page_num, page in enumerate(doc):
        if is_image_heavy_page(page):
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            description = describe_with_gemini(img_bytes, page_num + 1)
            if description:
                image_descriptions.append({
                    "page": page_num + 1,
                    "text": description,
                })
    doc.close()
    
    # Step 3: Embed + store
    all_chunks = text_chunks + image_descriptions
    embed_and_store_chunks(doc_obj, all_chunks)


def is_image_heavy_page(page) -> bool:
    """True if images cover >60% of page area."""
    page_area = page.rect.width * page.rect.height
    image_area = sum(
        (i["width"] * i["height"])
        for i in page.get_image_info()
    )
    # Also treat pages with very little native text as image pages
    text = page.get_text().strip()
    return (image_area / page_area > 0.60) or (len(text) < 50 and len(page.get_image_info()) > 0)


def describe_with_gemini(img_bytes: bytes, page_num: int) -> str:
    """Send page PNG to Gemini 2.5 Flash vision for description."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    img_b64 = base64.b64encode(img_bytes).decode()
    response = model.generate_content([
        f"Describe the content of page {page_num} of this community service document. "
        "Extract any text, describe any diagrams, tables, or images shown. "
        "Focus on information useful for someone seeking community support services.",
        {"mime_type": "image/png", "data": img_b64}
    ])
    return response.text
```

[ASSUMED: exact Gemini API call signature — verify against google-generativeai docs before finalising]

### Chunk Strategy

```python
def chunk_markdown(md_text: str, max_tokens: int = 500) -> list[dict]:
    """
    Split markdown into semantic chunks.
    Respect heading boundaries — never split a heading from its content.
    """
    import re
    # Split on H2/H3 headings as natural boundaries
    sections = re.split(r'\n(?=#{1,3} )', md_text)
    chunks = []
    for section in sections:
        if len(section.split()) <= max_tokens:
            chunks.append({"text": section.strip(), "type": "text"})
        else:
            # Further split long sections on paragraph breaks
            paragraphs = section.split('\n\n')
            current = []
            for para in paragraphs:
                current.append(para)
                if len(' '.join(current).split()) >= max_tokens:
                    chunks.append({"text": '\n\n'.join(current).strip(), "type": "text"})
                    current = []
            if current:
                chunks.append({"text": '\n\n'.join(current).strip(), "type": "text"})
    return chunks
```

---

## Standard Stack

### Core (PDF Processing)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pymupdf4llm` | 1.27.2.2 | LLM/RAG-oriented PDF extraction to Markdown | Official RAG wrapper over PyMuPDF; purpose-built for this use case; no ML models; Python 3.14 wheels available |
| `PyMuPDF` | 1.27.2.2 | Auto-installed by pymupdf4llm; also used directly for pixmap rendering and OCR | Fast, no deps, Python 3.14 supported, most complete PDF feature set |

### Supporting (OCR Fallback)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytesseract` | 0.3.13 | Python wrapper for Tesseract OCR | Offline/bulk scanned PDFs where Gemini API calls are cost-prohibitive |
| `Tesseract-OCR` (binary) | 5.x | OCR engine | Required if pytesseract is used; must be installed in Docker image |

### Remove

| Library | Action | Reason |
|---------|--------|--------|
| `PyPDF2==3.0.1` | Remove from requirements.txt | Deprecated; image extraction broken; superseded by pymupdf4llm |

### Libraries NOT Recommended

| Library | Reason Not Selected |
|---------|---------------------|
| `unstructured[pdf]` | Incompatible with Python 3.14 (requires < 3.14); requires system poppler + tesseract |
| `marker-pdf` | GPL-3.0 license; GBs of ML models; 11.3s/page on CPU; impractical for Celery workers |
| `docling` | 9.74 GB Docker image (1.74 GB CPU-only); weekly-breaking release cadence; HuggingFace download on first worker start |
| `pdfplumber` | No image content extraction; keeps as optional supplement for table-heavy documents only |

**Installation:**
```bash
pip install pymupdf4llm==1.27.2.2
# Remove: pip uninstall PyPDF2
```

---

## Common Pitfalls

### Pitfall 1: Assuming All PDFs Have Native Text
**What goes wrong:** `pymupdf4llm.to_markdown()` returns empty or near-empty string for scanned PDFs. Chunks stored in pgvector contain nothing useful.
**Why it happens:** Scanned PDFs are image layers with no embedded text; the PDF internals contain only image objects.
**How to avoid:** After extraction, check `len(md_text.strip()) < 100` relative to page count. Flag such documents for the image-page pipeline. Log a warning to the audit log so admins know the doc was processed with vision fallback.
**Warning signs:** Empty markdown from multi-page PDF; `page.get_text()` returns whitespace.

### Pitfall 2: PyMuPDF AGPL Licence Obligation Not Tracked
**What goes wrong:** Platform is later commercialised or white-labelled; Artifex sends a licence compliance notice.
**Why it happens:** AGPL requires open-sourcing all code that uses the library if the software is distributed commercially.
**How to avoid:** Note in CLAUDE.md or a LICENSE-NOTES file that PyMuPDF is AGPL-3.0. If Support2Thrive becomes a commercial SaaS, obtain Artifex commercial licence (~$500-3000/year depending on tier) or switch to pdfplumber+pypdfium2 for text-only paths.
**Warning signs:** Any commercial licensing discussion about the platform.

### Pitfall 3: Celery Worker Running Gemini Vision on Every Page
**What goes wrong:** Every page of every PDF triggers a Gemini API call, creating runaway API costs and rate-limit errors.
**Why it happens:** `is_image_heavy_page()` check not implemented; all pages sent to vision API.
**How to avoid:** Implement the image-heavy detection heuristic (image area > 60% OR text < 50 chars). Store a `vision_pages_processed` counter on the document model so admins can monitor usage.

### Pitfall 4: Memory Exhaustion in Celery Worker (Large PDFs)
**What goes wrong:** Celery worker OOM-killed when processing a 200-page PDF with high-res images; task retried indefinitely.
**Why it happens:** `page.get_pixmap(dpi=300)` on a full A4 page at 300 DPI produces ~25 MB per page; 200 pages = 5 GB in memory.
**How to avoid:** Cap DPI at 150 for Gemini vision (sufficient for text recognition; reduces memory 4x vs 300 DPI). Process pages in batches within the task. Add a file size limit on Django admin upload (e.g., 50 MB max). Set Celery `task_time_limit` and `task_soft_time_limit`.

### Pitfall 5: Tesseract Not Available in Production Container
**What goes wrong:** `page.get_textpage_ocr()` raises `FileNotFoundError: tesseract not found` in production; scanned PDFs yield no text.
**Why it happens:** Tesseract is a system binary, not a Python package. It must be in the Docker image.
**How to avoid:** Add `RUN apt-get install -y tesseract-ocr tesseract-ocr-eng` to Dockerfile. Or make OCR a feature flag (`ENABLE_OCR = env.bool("ENABLE_OCR", False)`) so failure is graceful. Use Gemini vision as primary so OCR is only needed as fallback.

### Pitfall 6: PyPDF2 Left in requirements.txt Causing Confusion
**What goes wrong:** A future developer uses `import PyPDF2` for new code assuming it is the project standard.
**Why it happens:** PyPDF2==3.0.1 still in requirements.txt.
**How to avoid:** Remove PyPDF2 from requirements.txt in Wave 0. If any existing code uses it, audit now — check all `import PyPDF2` references.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom pdfminer parsing | `pymupdf4llm.to_markdown()` | Handles multi-column, ligatures, RTL text, encoding edge cases |
| Table detection and extraction | Regex-based column parsing | PyMuPDF table API (ported from pdfplumber) | PDF coordinate math is complex; existing solutions handle merged cells, spanned rows |
| Image page detection | Pixel-colour analysis | `page.get_image_info()` + `page.get_text()` area check | PyMuPDF already knows image bounding boxes from PDF internals |
| PDF page rendering to PNG | Pillow + poppler subprocess | `page.get_pixmap(dpi=N).tobytes("png")` | Pure Python, no subprocess, no poppler dependency |
| Text chunking | Hard character-count splits | Heading-boundary Markdown splitter (see code above) | Character splits cut sentences mid-stream; heading splits preserve semantic units |
| OCR on image pages | Custom Tesseract subprocess call | `page.get_textpage_ocr()` | PyMuPDF's integration caches the TextPage; reuse for multiple extractions |

---

## State of the Art (2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyPDF2 | pypdf (maintained fork) or pymupdf4llm | 2023 | PyPDF2 is deprecated; drop it |
| Extract text only for RAG | Extract text + describe images with vision LLM | 2024–2025 | Multimodal PDFs (service directories with diagrams) now fully indexed |
| Run ML PDF models in-process | Dedicated ML container or API call | 2025 | Celery workers stay lean; models warm once, not per-task |
| LangChain/LlamaIndex loader abstractions | Direct pymupdf4llm → sentence-transformers pipeline | 2025 | Fewer dependencies; direct control over chunking strategy |
| Fixed-size character chunking | Semantic heading-boundary chunking | 2025 | RAG retrieval accuracy significantly improved |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | Yes | 3.14.3 | — |
| PyTorch CPU | sentence-transformers (existing) | Yes | 2.11.0+cpu | — |
| Pillow | Image handling | Yes | 12.2.0 | — |
| google-generativeai | Gemini vision API calls | Yes | installed | — |
| Celery | Background task processing | Yes | 5.6.3 | — |
| Redis | Celery broker | Yes (configured) | — | — |
| pymupdf4llm | PDF extraction | Not yet installed | 1.27.2.2 available | — |
| Tesseract binary | Optional OCR | Unknown — not checked | — | Use Gemini vision; skip OCR |
| poppler-utils | NOT needed with PyMuPDF approach | N/A | — | — |
| unstructured | Not recommended | Blocked (Python 3.14) | — | pymupdf4llm |

**Missing dependencies with no fallback:**
- None (all required packages are installable; Tesseract is optional with Gemini vision as primary)

**Missing dependencies with fallback:**
- `pytesseract` / `Tesseract` binary: not installed; Gemini 2.5 Flash vision is the primary image strategy

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 2.5 Flash vision API call format uses `{"mime_type": "image/png", "data": b64}` inline part | Code Examples | Code will fail at runtime if SDK format differs — verify against google-generativeai docs before implementation |
| A2 | Image-heavy detection threshold of 60% page area is appropriate | Architecture Patterns | May miss some mixed-content pages; threshold should be tunable |
| A3 | 150 DPI is sufficient resolution for Gemini vision to extract text from scanned pages | Architecture Patterns | Quality may be insufficient for small print; may need 200 DPI for some document types |
| A4 | PyMuPDF AGPL is acceptable for Support2Thrive (non-commercial community platform) | Standard Stack | If project is ever commercially licensed, Artifex licence required |
| A5 | PyPDF2 usage in existing codebase is limited to placeholder/legacy code only | Project Constraints | If any existing feature depends on PyPDF2 behaviour, removing it could break functionality |

---

## Open Questions

1. **Gemini API rate limits during bulk PDF processing**
   - What we know: Gemini 2.5 Flash is fast; batch API available
   - What's unclear: What rate limits apply to the project's API key tier; whether Celery task retries with Gemini rate-limit errors need exponential backoff
   - Recommendation: Implement `@shared_task(rate_limit="10/m")` on the Gemini vision sub-task; use `max_retries=5` with exponential backoff

2. **Existing PyPDF2 usage in codebase**
   - What we know: `PyPDF2==3.0.1` is in requirements.txt; it is deprecated
   - What's unclear: Whether any existing app code imports and uses PyPDF2
   - Recommendation: Run `grep -r "PyPDF2\|import pypdf" apps/` before removing from requirements.txt

3. **Tesseract installation in production Docker**
   - What we know: docker-compose.yml exists; Tesseract is a system binary
   - What's unclear: Whether the production Docker image includes Tesseract
   - Recommendation: Make OCR a feature flag; rely on Gemini vision as primary strategy so Tesseract absence is non-blocking

4. **pgvector dev strategy (SQLite vs Docker)**
   - What we know: STATE.md lists "Decide dev RAG strategy" as first Phase 6 action
   - What's unclear: Whether pgvector Docker is available in dev environment
   - Recommendation: This is a separate research question; PDF processing is independent of vector storage backend

---

## Sources

### Primary (HIGH confidence)
- [PyPI: PyMuPDF 1.27.2.2](https://pypi.org/project/PyMuPDF/) — version, size, Python support, changelog verified
- [PyPI: pymupdf4llm 1.27.2.2](https://pypi.org/project/pymupdf4llm/) — version, size, dependencies verified
- [PyPI: pdfplumber 0.11.9](https://pypi.org/project/pdfplumber/) — version, image limitations verified
- [PyPI: unstructured 0.22.18](https://pypi.org/project/unstructured/) — Python version constraint (<3.14) verified
- [PyPI: marker-pdf 1.10.2](https://pypi.org/project/marker-pdf/) — version, license, ML model requirements verified
- [PyPI: docling 2.88.0](https://pypi.org/project/docling/) — version confirmed via pip index
- [PyMuPDF changelog](https://pymupdf.readthedocs.io/en/latest/changes.html) — v1.27.2 OCR improvements verified
- Project venv: PyTorch 2.11.0+cpu, sentence-transformers 5.4.0, Pillow 12.2.0, google-generativeai, Celery 5.6.3, Python 3.14.3 — all confirmed via `pip show`

### Secondary (MEDIUM confidence)
- [Artifex blog: multimodal RAG with PyMuPDF4LLM](https://artifex.com/blog/building-a-multimodal-llm-application-with-pymupdf4llm) — image extraction pattern
- [Shekhar Gulati: Docling Docker size](https://shekhargulati.com/2025/02/05/reducing-size-of-docling-pytorch-docker-image/) — 9.74 GB default, 1.74 GB CPU-only
- [Aman Kumar: 7 PDF extractors comparison 2025](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257) — benchmark timings (pymupdf4llm 0.14s, marker-pdf 11.3s)
- [Artifex licensing page](https://artifex.com/licensing) — AGPL / commercial dual licence

### Tertiary (LOW confidence — flagged)
- Gemini 2.5 Flash pricing (~$0.075/1K tokens, ~258 tokens/image) from LaoZhang-AI blog; verify against current Google pricing page before budgeting
- Gemini vision API inline part format — assumed from training knowledge; verify against official google-generativeai Python SDK docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI registry 2026-04-13
- Architecture: MEDIUM — pattern is well-documented but Gemini SDK call signature is ASSUMED
- Pitfalls: HIGH — most from official docs and verified issues trackers
- Python 3.14 compatibility: HIGH — PyMuPDF wheels confirmed; unstructured blocker confirmed

**Research date:** 2026-04-13
**Valid until:** 2026-07-13 (90 days — PyMuPDF has stable release cadence; docling/unstructured release frequently but are not recommended)
