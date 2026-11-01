# Reading text off a graphic (card faces, tiles, screenshots)

Use when the needed text exists only as pixels: game card faces, board tiles,
UI screenshots, scanned labels. Check first that no text-native source covers
the same fact (component list in a rulebook, a card database page, a publisher
news post).

## Tooling check

```bash
which tesseract
python3 -c "import PIL; print(PIL.__version__)"   # may only exist in a tooling venv
```

If the system interpreter lacks PIL, use whichever venv on the host has pillow
and tesseract installed rather than pip-installing into a new one.

## 1. Crop + upscale + threshold

```python
from PIL import Image, ImageOps, ImageEnhance
im = Image.open("card.webp").convert("L")
W, H = im.size
box = (int(0.03*W), int(0.60*H), int(0.42*W), int(0.95*H))   # left text box
c = im.crop(box).resize(((box[2]-box[0])*4, (box[3]-box[1])*4), Image.LANCZOS)
c = ImageEnhance.Contrast(c).enhance(2.0)
c.save("crop_gray.png")
c.point(lambda p: 255 if p > 140 else 0).save("crop_bin140.png")
```

Emit the grayscale variant plus 2–3 thresholds; which one wins varies with the
art behind the text. Wrapping is preserved by keeping the crop box full-width
of the text column.

## 2. Band detection without numpy

A full-image OCR blends adjacent boxes/columns. Slice lines first:

```python
from PIL import Image
im = Image.open("crop_gray.png").convert("L")
W, H = im.size
STEP, MIN_PX, BAND = 2, 9, 8      # sample every 2px; >=9 bright px = text row
rows, y = [], 0
while y < H:
    n = sum(1 for x in range(0, W, STEP) if im.getpixel((x, y)) > 150)
    rows.append(n >= MIN_PX)
    y += 1
bands, start = [], None
for i, on in enumerate(rows):
    if on and start is None:
        start = i
    elif not on and start is not None:
        if i - start >= BAND:
            bands.append((start, i))
        start = None
for k, (a, b) in enumerate(bands):
    im.crop((0, max(0, a-6), W, min(H, b+6))).save(f"band{k}.png")
print(bands)
```

Then OCR each band: `tesseract band3.png - --psm 7`.

## 3. PSM cheat sheet

| PSM | Use for |
|-----|---------|
| 6 | uniform block of text (the default first try) |
| 7 | single text line (per band) |
| 4 / 11 | columns / sparse text, icons mixed with words |
| 3 | fully automatic, when the layout is unknown |

Run the same crop through 2–3 PSMs and compare: agreement across PSMs is the
confidence signal. Icons standing in for words (a spice/persuasion glyph at the
end of a sentence) never OCR — expect the sentence to end mid-clause and say so
instead of inventing the missing word.

## Reporting

Label the result as a transcription from the image, and pair it with one
structural source (rulebook component list, FAQ, card database, patch notes).
If the user plays a localised edition, their printed wording is the authority —
ask for a photo when a clause stays ambiguous.
