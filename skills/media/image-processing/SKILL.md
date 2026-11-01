---
name: image-processing
description: Process and prepare images — background removal, social media resizing/cropping/compression, format conversion
tags: [image, processing, background-removal, resize, crop, compress, rembg, imagemagick, pillow, social-media, media]
author: MasterBenC
license: MIT
platforms: [linux, macos, windows]
---

# Image Processing

Transform and prepare existing images for various purposes. Two primary workflows: background removal and platform-specific formatting.

## Quick Decision

| Need | Section |
|------|---------|
| Remove/replace image background | [Background Removal](#background-removal) |
| Resize/crop/compress for social platforms | [Social Media Formatting](#social-media-formatting) |

---

## Background Removal

Remove image backgrounds and replace with a solid color (typically white). Two methods in priority order.

### Method 1: rembg (AI-based, best quality)

Uses the u2net ONNX model for ML-based background removal. Requires model download (~176MB) on first use.

```bash
pip install "rembg[cpu]" filetype --break-system-packages
```

Full code and pitfalls in `references/background-removal.md`.

### Method 2: Chroma-Key (Pillow + scipy, instant fallback)

Works when the background is relatively uniform. Samples border pixels to detect background color, then replaces similar pixels. Instant, no model download.

Full code in `references/background-removal.md`.

### Decision Flow
1. Start rembg model download in background with `notify_on_complete=true`
2. While waiting, produce chroma-key version as instant fallback
3. Replace with rembg version once model download completes
4. If rembg fails (network issues), chroma-key is the final output

---

## Social Media Formatting

Resize, crop, and compress images for common social media platform requirements.

### Platform Size Reference

| Platform | Asset Type | Size | Format | Max Size |
|----------|------------|------|--------|----------|
| Douyin (抖音) | Profile Avatar | 500×500 px (square) | JPG/PNG | <100KB |
| TikTok | Profile Avatar | 200×200 px minimum | JPG/PNG | — |
| WeChat | Avatar | 132×132 px minimum | JPG/PNG | — |

### Avatar Workflow
1. Install ImageMagick if not present: `apt install -y imagemagick`
2. Center-crop to square (`-gravity center -crop 1:1`)
3. Resize to target dimensions
4. Set quality for file-size control

```bash
# Example: arbitrary image → 500×500 square Douyin avatar
convert input.jpg -gravity center -crop 1:1 -resize 500x500^ -quality 85 output_avatar.jpg
```

### Pitfalls
- **Non-square inputs**: Always center-crop to 1:1 first to preserve the main subject
- **Pillow vs ImageMagick**: Pillow availability varies by environment. On sandboxed envs, prefer ImageMagick CLI. On the volcengine cloud server (118.145.218.111), Pillow works fine — use whichever is more convenient
- **Python path**: The terminal tool uses a venv Python. For system-level packages (Pillow, ImageMagick), use `/usr/bin/python3` explicitly
