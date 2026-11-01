#!/usr/bin/env python3
"""HTML card -> PNG.

Usage: copy next to your card HTML, edit the constants below, then
  python3 html_card_to_png.py

Chain: weasyprint (HTML -> PDF, @page pins the size) -> pdftoppm (2x PNG) -> PIL crops the
 trailing background rows. Needs weasyprint in the venv plus poppler (pdftoppm); no browser,
 no CDP, no headless Chrome.

After rendering, run vision_analyze on the PNG (columns actually side by side, numbers on the
same line as their text, CJK glyphs real, nothing clipped) before delivering it.
"""
import os
import subprocess

from PIL import Image
from weasyprint import CSS, HTML

SRC = 'card.html'        # input HTML
OUT = 'card.png'         # output PNG
W_PX, H_PX = 750, 1120   # render 750px wide; H is generous on purpose, the excess gets cropped
BG = (13, 17, 23)        # the card's ground color: the rows to crop are the ones matching it
DPI = 192                # 192dpi ~= 2x
TAIL = 56                # whitespace to keep below the last content row

pdf = OUT.replace('.png', '.pdf')
raw = OUT.replace('.png', '_raw.png')
prefix = raw[:-4]

# weasyprint does not shrink to content height: pin the page, crop afterwards.
css = CSS(string=f'@page{{size:{W_PX * 0.75}pt {H_PX * 0.75}pt;margin:0}} html,body{{margin:0}}')
HTML(filename=SRC).write_pdf(pdf, stylesheets=[css])
print('pdf bytes', os.path.getsize(pdf))

subprocess.run(['pdftoppm', '-png', '-r', str(DPI), '-singlefile', pdf, prefix], check=True)
img = Image.open(raw).convert('RGB')
print('raw size', img.size)

# Scan upward for the first row that is not pure background, sampling across the width so a
# solid ground does not fool a center-column-only scan into cropping into the content.
px = img.load()
w, h = img.size
bottom = h
for y in range(h - 1, -1, -1):
    hit = False
    for x in range(0, w, 5):
        r, g, b = px[x, y]
        if abs(r - BG[0]) + abs(g - BG[1]) + abs(b - BG[2]) > 10:
            hit = True
            break
    if hit:
        bottom = y + 1
        break
bottom = min(bottom + TAIL, h)

img.crop((0, 0, w, bottom)).save(OUT)
print('FINAL', OUT, Image.open(OUT).size, os.path.getsize(OUT), 'bytes')
