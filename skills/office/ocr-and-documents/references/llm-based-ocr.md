# LLM-Based OCR: State of the Art (2026)

When traditional OCR (pymupdf, marker-pdf) isn't enough — long documents, complex layouts, batch PDF processing — consider LLM-based OCR.

## Unlimited-OCR (Baidu, June 2026)

**GitHub**: https://github.com/baidu/Unlimited-OCR
**Paper**: https://arxiv.org/abs/2606.23050
**Stars**: 13K+ (2 weeks)
**License**: MIT

### Core Innovation

R-SWA (Reference Sliding Window Attention) — replaces all decoder attention layers with a constant-KV-cache mechanism. Unlike DeepSeek OCR (where KV cache grows linearly with output length, causing progressive slowdown), Unlimited-OCR maintains **constant memory and speed** regardless of document length. Can transcribe dozens of pages in one 32K-token forward pass.

### vs DeepSeek OCR

| Aspect | DeepSeek OCR | Unlimited-OCR |
|--------|-------------|---------------|
| Long-doc speed | Slows down over time | Constant |
| KV Cache | Linear growth | Constant |
| 32K context | Bottlenecked | Native support |
| Best for | Short documents | Long docs, PDFs, batch |

### Deployment Options

| Method | Complexity | Use Case |
|--------|-----------|----------|
| **Transformers** | ⭐ Simple | Single-machine research |
| **vLLM** | ⭐⭐ Docker one-liner | Production high-concurrency |
| **SGLang** | ⭐⭐⭐ Manual wheel | Max performance, batch |

Dependencies: torch 2.10+, transformers 4.57+, CUDA 12.9+, ~40GB+ VRAM.

### API Options (No Self-Hosting)

**Option 1: Baidu Cloud API (Recommended)**
- Docs: https://cloud.baidu.com/doc/OCR/s/fmr1p39gb
- Auth: AK/SK → access_token (standard Baidu Cloud)
- Free tier: Yes (register + real-name auth)
- Billing: Per-page (price TBD; PaddleOCR-VL reference: ~9 CNY per 1000 pages)
- API: REST, POST with base64 images

**Option 2: HuggingFace Spaces (Free, Unstable)**
- Demo: https://huggingface.co/spaces/baidu/Unlimited-OCR
- Gradio-based, may queue, not production-grade

### When to Use

- ✅ Batch PDF digitization (archives, contracts, annual reports)
- ✅ Long-document OCR (100+ pages)
- ✅ Production OCR pipelines needing high concurrency (vLLM)
- ❌ Single-image OCR (overkill; use pymupdf or marker-pdf)
- ❌ No GPU available (use Baidu Cloud API instead)
