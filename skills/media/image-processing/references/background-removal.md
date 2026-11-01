# Background Removal — Full Methods

## Method 1: rembg (AI-based, best quality)

Uses the u2net ONNX model for ML-based background removal.

### Installation

```bash
pip install "rembg[cpu]" filetype --break-system-packages
```

### Usage

```bash
/usr/bin/python3 -c "
from rembg import remove
from PIL import Image

img = Image.open('input.jpg')
result = remove(img)

white_bg = Image.new('RGBA', result.size, (255, 255, 255, 255))
white_bg.paste(result, (0, 0), result)
final = white_bg.convert('RGB')
final.save('output.png')
"
```

### Pitfalls

- **Python path**: 机器上常有好几个解释器，`rembg` 只装在你装过它的那个里。先摸清哪个能 `import rembg`，之后全程显式用绝对路径调它——用错解释器时症状是 `ModuleNotFoundError`，看起来像"没装"。
- **Model download**: The u2net model is ~176MB, downloaded from GitHub on first use. In China, this is slow (5-10 min). Run in background with `notify_on_complete=true` and offer a chroma-key fallback while waiting.
- **CLI is unreliable**: rembg CLI requires `asyncer` and other deps that may not install cleanly. Prefer Python API directly.
- **Not available in execute_code**: The execute_code sandbox has its own Python env without rembg. Only use `terminal()`.

---

## Method 2: Chroma-Key (Pillow + scipy, instant fallback)

Works when the background is relatively uniform (e.g., dark studio backdrop). Samples border pixels to detect background color, then replaces similar pixels with white.

```bash
/usr/bin/python3 << 'PYEOF'
from PIL import Image
import numpy as np
from scipy.ndimage import binary_closing, binary_dilation

img = Image.open("input.jpg").convert("RGBA")
arr = np.array(img).astype(np.float32)
h, w = arr.shape[:2]

# Sample border pixels
border = []
for x in range(0, w, 5):
    border.append(arr[0, x, :3])
    border.append(arr[h-1, x, :3])
for y in range(0, h, 5):
    border.append(arr[y, 0, :3])
    border.append(arr[y, w-1, :3])
border = np.array(border)

bg_mean = np.mean(border, axis=0)
bg_std = np.std(border, axis=0)
threshold = np.maximum(bg_std * 2.0, 25)

diff = np.abs(arr[:,:,:3] - bg_mean)
mask = np.all(diff < threshold, axis=2)

# Protect subject center from being masked
margin = 60
mask[margin:h-margin, margin:w-margin] = False

# Morphological cleanup
mask = binary_closing(mask, structure=np.ones((3,3)), iterations=2)
mask = binary_dilation(mask, iterations=2)

arr[mask, :3] = [255, 255, 255]
final = Image.fromarray(arr.astype(np.uint8), "RGBA").convert("RGB")
final.save("output.png")
PYEOF
```

### Limitations of chroma-key

- Only works on uniform/semi-uniform backgrounds
- Dark backgrounds near dark hair/edges may leave halos
- Complex/gradient backgrounds produce poor results
- Subject dark areas (clothing, hair) near background color get partially masked
