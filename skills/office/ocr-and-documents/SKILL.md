---
name: ocr-and-documents
description: "Extract text from PDFs/scans (pymupdf, marker-pdf)."
version: 2.3.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [PDF, Documents, Research, Arxiv, Text-Extraction, OCR]
    related_skills: [powerpoint]
---

# PDF & Document Extraction

For DOCX: use `python-docx` (parses actual document structure, far better than OCR).
For PPTX: see the `powerpoint` skill (uses `python-pptx` with full slide/notes support).
This skill covers **PDFs and scanned documents**.

## Step 0: Quick Diagnosis — Does the PDF Have a Text Layer?

Before installing anything, check whether the PDF is text-based or image-based:

```bash
# Quick test: does pdftotext produce anything?
pdftotext document.pdf - | head -20

# Get metadata: page count, dimensions, format
pdfinfo document.pdf
```

**Heuristics from metadata:**
- Page size `2560 x 1440 pts` → widescreen presentation, likely exported from PPT/Keynote as images
- `pdftotext` returns empty + widescreen dimensions → almost certainly image-based, need OCR (marker-pdf)
- `pdftotext` returns text → use pymupdf (faster, no heavy models)

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| **Text-based PDF** | ✅ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ✅ |
| **Code blocks** | ❌ | ✅ |
| **Forms** | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ✅ |
| **Reading order detection** | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ |
| **EPUB** | ✅ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Decision**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis.

If the user needs marker capabilities but the system lacks ~5GB free disk:
> "This document needs OCR/advanced extraction (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can use web_extract, or I can try pymupdf which works for text-based PDFs but not scanned documents or equations."

---

## pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm
```

### Installation Pitfalls

**Externally-managed-environment error:** On Debian/Ubuntu systems with PEP 668, `pip install` may fail with "externally-managed-environment". Use `--break-system-packages`:

```bash
pip install pymupdf --break-system-packages
```

**System pip vs venv pip mismatch:** The default `pip`/`python3` on the PATH may point to a different Python than the active Hermes venv. If `import fitz` fails after install, check which Python is active and use the venv's pip explicitly:

```bash
# Find which python is actually running
python3 -c "import sys; print(sys.executable)"

# Install into the active venv
/path/to/venv/bin/python3 -m pip install pymupdf

# Verify
/path/to/venv/bin/python3 -c "import fitz; print('OK')"
```

**Module name:** The import is `fitz`, not `pymupdf` — the package is named `pymupdf` but the module is `fitz`.

**Via helper script**:
```bash
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

**Inline**:
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

pymupdf handles these natively — use `execute_code` or inline Python:

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

```python
# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

```python
# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

No extra dependencies needed — pymupdf covers split, merge, search, and text extraction in one package.

---

## LLM-Based OCR (Long Documents, Batch, Production)

For long documents (dozens of pages), batch PDF processing, or production pipelines, traditional OCR hits limits. LLM-based OCR models like Unlimited-OCR (Baidu, MIT-licensed) use vision-language models with constant-KV-cache attention to transcribe long documents at stable speed. No local GPU? Use the Baidu Cloud API.

→ See [references/llm-based-ocr.md](references/llm-based-ocr.md) for comparison table, API options, pricing, and deployment modes.

## Text off a graphic: card faces, tiles, screenshots

Rulebooks and publisher FAQs do not carry the printed text of physical
components — that lives on the card/tile image. Work this ladder, and stop as
soon as a **text-native** source answers the question (component/setup list,
card database, publisher news post, patch notes). Pixel forensics is the last
resort, not the first: it costs many calls and returns partial words.

1. Grab the largest image offered (card-database `og`/`xl` asset), not the
   thumbnail embedded in the page HTML.
2. **PIL preprocess**: crop to the text box, upscale ×3–4 (LANCZOS), grayscale,
   contrast ×2.0–2.2; also emit a binarized variant (thresholds ~110/140/170).
3. `tesseract crop.png - --psm 6`, then repeat with `--psm 4` and `--psm 11`;
   for a single scanned line use `--psm 7`.
4. Column blending is the usual failure: a whole-image pass merges the sides of
   a card. Find text bands first (pure Python: count bright pixels per row on a
   downsampled mask, treat runs above a threshold as lines) and OCR each band
   alone.
5. One vision pass over a busy layout is a cheap probe, not a loop: if it does
   not come back with usable text, spend the remaining budget on steps 2–4.

**Cap the effort**: after two rounds of crop + PSM variants still missing a
clause, quote what you did read, label it a card-face transcription, and ask the
user for a photo of the physical card — their localised wording is often what
they were quoting anyway.

→ Runnable recipe + band-slicing snippet: [references/image-text-ocr.md](references/image-text-ocr.md)

## PPTX / DOCX without python-pptx (zip + XML)

Office 文件就是 zip 里一堆 XML，标准库就能读——没装 `python-pptx`/`python-docx` 的主机上照样能通读一份 deck。

```python
import zipfile, re
from xml.etree import ElementTree as ET
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
z = zipfile.ZipFile(path)
names = [n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)]
names.sort(key=lambda n: int(re.search(r'(\d+)', n).group(1)))   # slide2 在 slide10 之前
for n in names:
    t = ET.fromstring(z.read(n))
    lines = [''.join(x.text or '' for x in p.iter(A+'t')).strip() for p in t.iter(A+'p')]
    print(n, [l for l in lines if l])
```

- 按 `<a:p>`（段落）收集文本，不要按 `<a:t>`（run）——一句话被格式拆成多个 run 时会碎成几段。
- 文件名要按数字排序，字典序会把 slide10 排在 slide2 前面。
- .docx：`word/document.xml`，段落 `w:p`、run `w:t`；.xlsx：`xl/sharedStrings.xml` + `xl/worksheets/sheet1.xml`。
- 备注在 `ppt/notesSlides/notesSlideN.xml`；图表/组合/图片里的文字不在 `slideN.xml`——某页看着空，先查 `ppt/media/` 再判定。

## Notes

- `web_extract` is always first choice for **remote** URLs (https://). Do NOT use `file://` URLs — they are blocked as private/internal network addresses. For local files, use the local extractors below.
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)
