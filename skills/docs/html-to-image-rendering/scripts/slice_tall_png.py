#!/usr/bin/env python3
"""Slice a tall PNG into chat-sized segments.

Why: a whole-page render (article preview, long report) comes out 10k-15k px tall, which is
unreadable as a single attachment. Segments of ~4000px are comfortably viewable.

Usage:
  python3 slice_tall_png.py <tall.png> [out_prefix] [--slice 4000]

Output: <prefix>-p1.png, <prefix>-p2.png, ... in the source image's directory.
Send them in order with MEDIA:/abs/path lines.
"""
import os
import sys

from PIL import Image

DEFAULT_SLICE = 4000


def trim_background(im, threshold=250):
    """Crop the trailing uniform band. Sample across the width, not just the centre --
    a solid-dark design has nothing to find in a centre-only scan."""
    gray = im.convert("L")
    bbox = gray.point(lambda p: 255 if p < threshold else 0).getbbox()
    if not bbox:
        return im
    return im.crop((0, bbox[1], im.width, bbox[3]))


def slice_image(im, prefix, slice_h):
    paths = []
    n = max(1, (im.height + slice_h - 1) // slice_h)
    for i in range(n):
        top = i * slice_h
        bottom = im.height if i == n - 1 else (i + 1) * slice_h
        path = f"{prefix}-p{i + 1}.png"
        im.crop((0, top, im.width, bottom)).save(path, optimize=True)
        paths.append((path, (im.width, bottom - top)))
    return paths


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        raise SystemExit(1)

    src = os.path.abspath(args[0])
    prefix = os.path.abspath(args[1]) if len(args) > 1 else os.path.splitext(src)[0]
    slice_h = DEFAULT_SLICE
    if "--slice" in sys.argv:
        slice_h = int(sys.argv[sys.argv.index("--slice") + 1])

    im = trim_background(Image.open(src).convert("RGB"))
    paths = slice_image(im, prefix, slice_h)
    print(f"trimmed {im.size} -> {len(paths)} segment(s)")
    for path, size in paths:
        print(path, size, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
