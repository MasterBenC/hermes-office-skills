#!/usr/bin/env python3
"""把表格渲染成小字号 PNG（飞书宽表格显示不全时用）。
用法: python3 tbl2img.py data.json out.png [--fs 15] [--title "标题"]
data.json: {"head": ["列1","列2"], "rows": [["a","b"], ...]}
"""
import json
import sys
import argparse
from PIL import Image, ImageDraw, ImageFont

FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

INK = (34, 34, 34, 255)          # #222
HEAD_BG = (62, 73, 89, 255)      # #3E4959
HEAD_FG = (255, 255, 255, 255)
ZEBRA = (244, 245, 247, 255)     # #f4f5f7
LINE = (222, 226, 230, 255)
BG = (255, 255, 255, 255)


def _hard_split(tok, font, max_w, draw):
    """单个 token 本身超宽时按字符硬切。"""
    out, buf = [], ""
    for ch in tok:
        if not buf or draw.textlength(buf + ch, font=font) <= max_w:
            buf += ch
        else:
            out.append(buf)
            buf = ch
    if buf:
        out.append(buf)
    return out


def wrap(text, font, max_w, draw):
    """按像素宽度折行（中英混排）：中文按字断，西文单词整体不拆。"""
    if not max_w:
        return [text]
    import re
    toks = re.findall(r"[A-Za-z0-9]+[A-Za-z0-9\.\-+_/:]*|[ \t]+|.", text)
    lines, cur = [], ""
    for tk in toks:
        if draw.textlength(cur + tk, font=font) <= max_w:
            cur += tk
            continue
        if cur.strip():
            lines.append(cur.rstrip())
            cur = ""
        if draw.textlength(tk, font=font) <= max_w:
            cur = tk.lstrip()
        else:
            parts = _hard_split(tk.lstrip(), font, max_w, draw)
            lines.extend(parts[:-1])
            cur = parts[-1]
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out")
    ap.add_argument("--fs", type=int, default=15, help="正文字号(px)，越小表格越窄")
    ap.add_argument("--title", default="")
    ap.add_argument("--max-col", type=int, default=0, help="单列最大像素宽，超出折行")
    ap.add_argument("--scale", type=int, default=2, help="超采样倍率(视觉更清晰)")
    a = ap.parse_args()

    d = json.load(open(a.data, encoding="utf-8"))
    head, rows = d["head"], d["rows"]

    s = a.scale
    fs = a.fs * s
    f_reg = ImageFont.truetype(FONT_REG, fs)
    f_bold = ImageFont.truetype(FONT_BOLD, fs)
    pad_x, pad_y = 12 * s, 8 * s

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    max_col = a.max_col * s if a.max_col else 0

    # 每格先折行
    cells = []
    for r in rows:
        row_cells = []
        for c in r:
            row_cells.append(wrap(str(c), f_reg, max_col, probe))
        cells.append(row_cells)
    head_cells = [[h] for h in head]

    ncol = len(head)
    col_w = []
    for i in range(ncol):
        w = probe.textlength(head[i], font=f_bold)
        for r in cells:
            for ln in r[i]:
                w = max(w, probe.textlength(ln, font=f_reg))
        col_w.append(int(w) + pad_x * 2)

    W = sum(col_w)
    line_h = int(fs * 1.55)
    head_h = line_h + pad_y * 2
    body_hs = [max(1, max(len(c) for c in r)) * line_h + pad_y * 2 for r in cells]
    title_h = (int(fs * 1.1) + 20 * s) if a.title else 0
    H = title_h + head_h + sum(body_hs)

    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)

    y = 0
    if a.title:
        dr.text((pad_x // 2, 6 * s), a.title, font=f_bold, fill=HEAD_BG)
        y += title_h

    # 表头
    dr.rectangle([0, y, W, y + head_h], fill=HEAD_BG)
    x = 0
    for i, h in enumerate(head):
        dr.text((x + pad_x, y + pad_y), h, font=f_bold, fill=HEAD_FG)
        x += col_w[i]
    y += head_h

    # 表体
    for ri, r in enumerate(cells):
        h = body_hs[ri]
        if ri % 2 == 1:
            dr.rectangle([0, y, W, y + h], fill=ZEBRA)
        x = 0
        for i, lines in enumerate(r):
            ty = y + pad_y
            for ln in lines:
                dr.text((x + pad_x, ty), ln, font=f_reg, fill=INK)
                ty += line_h
            x += col_w[i]
        dr.line([(0, y), (W, y)], fill=LINE, width=max(1, s // 2))
        y += h
    dr.rectangle([0, 0, W - 1, H - 1], outline=LINE, width=max(1, s // 2))

    img.save(a.out)
    print(f"{a.out}  {W}x{H}  fs={a.fs}px  cols={ncol}  rows={len(rows)}")


if __name__ == "__main__":
    main()
