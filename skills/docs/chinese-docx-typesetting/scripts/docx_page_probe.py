#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量把目录里的 .docx 转成 PDF，量出每页“内容底部”与“剩余可用高度”。

为什么不用 PDF 页数判断：溢出 3 行和溢出 30 行都显示 2 页，看不出危险程度。

用法:
    python3 docx_page_probe.py <dir> [--dpi 100] [--page-mm 297] [--bottom-margin 13]
    python3 docx_page_probe.py out --bottom-margin 13

输出: 每个 PDF 每页的 内容底部 mm / 余量 mm，并在余量 <10mm 时标注 DANGER。
依赖: python-docx 非必需；需要 soffice、pdftoppm、Pillow、numpy。
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image


def convert_all(d):
    docx = sorted(glob.glob(os.path.join(d, "*.docx")))
    docx = [f for f in docx if not os.path.basename(f).startswith("~")]
    if docx:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", d] + docx,
            check=False,
            capture_output=True,
        )
    return sorted(glob.glob(os.path.join(d, "*.pdf")))


def page_bottoms_mm(pdf, dpi=100, threshold=200, min_dark_px=2):
    """渲染 PDF 每一页，返回 [(页号, 内容底部 mm), ...]；空白页为 None。"""
    tmp = tempfile.mkdtemp(prefix="probe_")
    prefix = os.path.join(tmp, "pg")
    try:
        subprocess.run(
            ["pdftoppm", "-r", str(dpi), "-png", pdf, prefix],
            check=True,
            capture_output=True,
        )
        out = []
        for i, png in enumerate(sorted(glob.glob(prefix + "*.png")), start=1):
            a = np.array(Image.open(png).convert("L"))
            dark = np.where((a < threshold).sum(axis=1) > min_dark_px)[0]
            out.append((i, None if dark.size == 0 else round(dark.max() / dpi * 25.4, 1)))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def pdf_pages(pdf):
    try:
        r = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split()[1])
    except FileNotFoundError:
        pass
    return None


def main():
    args = sys.argv[1:]
    d = args[0] if args and not args[0].startswith("-") else "."

    def opt(name, default):
        return type(default)(args[args.index(name) + 1]) if name in args else default

    dpi = opt("--dpi", 100)
    page_mm = opt("--page-mm", 297.0)
    bottom = opt("--bottom-margin", 13.0)
    avail = page_mm - bottom

    pdfs = convert_all(d)
    if not pdfs:
        print("no pdf/docx found in", os.path.abspath(d))
        return 1

    warn = False
    for pdf in pdfs:
        name = os.path.basename(pdf)
        total = pdf_pages(pdf)
        rows = page_bottoms_mm(pdf, dpi=dpi)
        print("== %s  (%s 页，可用高度 %.0fmm)" % (name, total, avail))
        for page, b in rows:
            if b is None:
                print("   p%d  空白页" % page)
                continue
            slack = round(avail - b, 1)
            flag = ""
            if slack < 10:
                flag = "  <-- DANGER: Word 可能溢出"
                warn = True
            elif slack > 40:
                flag = "  <-- 内容偏薄，考虑加内容"
            print("   p%d  内容底部 %6.1fmm  余量 %6.1fmm%s" % (page, b, slack, flag))
    return 2 if warn else 0


if __name__ == "__main__":
    sys.exit(main())
