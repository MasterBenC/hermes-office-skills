#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Markdown → 中文 .docx（AI培训项目回填稿）。
字体：微软雅黑(eastAsia) / Segoe UI(拉丁)；A4，左右 2.4cm，上下 2.2cm。
用法: python3 md2docx.py part1.md [part2.md ...] -o 输出.docx
"""
import re
import sys
import unicodedata
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

CJK = "微软雅黑"
LATIN = "Segoe UI"
INK = RGBColor(0x22, 0x22, 0x22)
NAVY = RGBColor(0x1F, 0x2E, 0x44)
GREY = RGBColor(0x66, 0x6B, 0x73)
ACCENT = RGBColor(0x3E, 0x49, 0x59)


def set_run(r, size=10.5, bold=False, color=INK, italic=False):
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = LATIN
    rPr = r._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rPr.insert(0, rf)
    rf.set(qn("w:eastAsia"), CJK)
    rf.set(qn("w:ascii"), LATIN)
    rf.set(qn("w:hAnsi"), LATIN)
    return r


def para_spacing(p, before=0, after=4, line=1.5, exact=None):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if exact:
        pPr = p._p.get_or_add_pPr()
        sp = pPr.find(qn("w:spacing"))
        if sp is None:
            sp = OxmlElement("w:spacing")
            pPr.append(sp)
        sp.set(qn("w:line"), str(exact))
        sp.set(qn("w:lineRule"), "exact")
    else:
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = line


def add_bottom_border(p, color="1F2E44", sz=8):
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "2")
    b.set(qn("w:color"), color)
    pBdr.append(b)
    pPr.insert(0, pBdr)          # pBdr 必须在 spacing/jc 之前


def add_left_border(p, color="3E4959", sz=12):
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    b = OxmlElement("w:left")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "6")
    b.set(qn("w:color"), color)
    pBdr.append(b)
    pPr.insert(0, pBdr)


def shade(p, fill="F4F5F7"):
    pPr = p._p.get_or_add_pPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), fill)
    bdr = pPr.find(qn("w:pBdr"))          # shd 必须排在 pBdr 之后、spacing 之前
    if bdr is not None:
        bdr.addnext(sh)
    else:
        pPr.insert(0, sh)


INLINE = re.compile(r"(\*\*.+?\*\*)")


def add_rich(p, text, size=10.5, color=INK, base_bold=False):
    for seg in INLINE.split(text):
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**"):
            set_run(p.add_run(seg[2:-2]), size=size, bold=True, color=ACCENT)
        else:
            set_run(p.add_run(seg), size=size, bold=base_bold, color=color)
    return p


def make_doc():
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name = LATIN
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), CJK)
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin = s.right_margin = Cm(2.4)
    s.top_margin = Cm(2.2)
    s.bottom_margin = Cm(2.0)
    return doc


def _disp_width(s):
    """东亚全角算 2、半角算 1，用来估列内容宽度。"""
    n = 0
    for ch in s:
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return n


def add_table(doc, rows):
    cols = max(len(r) for r in rows)
    t = doc.add_table(rows=0, cols=cols)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    total = 9071
    if cols == 3:
        widths = [1100, 6400, 1571]
    else:
        # 等宽会把「占比」「序号」这类窄列撑成大段留白，而长文列被挤成竖条。
        # 按各列最长文本定权，单列权重夹在 [1, 6]，再按版心总宽换算。
        weights = []
        for j in range(cols):
            mx = max(_disp_width(r[j]) for r in rows if j < len(r)) if rows else 1
            weights.append(min(6.0, max(1.0, mx / 8.0)))
        tw = sum(weights)
        widths = [max(600, int(total * w / tw)) for w in weights]
        widths[-1] = total - sum(widths[:-1])
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j in range(cols):
            txt = row[j] if j < len(row) else ""
            c = cells[j]
            c.width = Pt(widths[j] / 20.0)
            p = c.paragraphs[0]
            para_spacing(p, before=1, after=1, exact=280)
            add_rich(p, txt, size=9.5, base_bold=(i == 0))
            tcPr = c._tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:fill"), "EEF0F3" if i == 0 else "FFFFFF")
            tcPr.append(shd)
    # 表头跨页重复。长表（10 行以上）翻页后不重复表头，读者就分不清哪列是哪列。
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    grid = t._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(w))
    return t


def build(md_files, out):
    doc = make_doc()
    lines = []
    for f in md_files:
        lines += open(f, encoding="utf-8").read().split("\n")
    tbl_buf = []

    def flush_table():
        nonlocal tbl_buf
        if tbl_buf:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in tbl_buf]
            rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            add_table(doc, rows)
            p = doc.add_paragraph()
            para_spacing(p, before=0, after=6)
            tbl_buf = []

    for raw in lines:
        ln = raw.rstrip()
        if ln.startswith("|"):
            tbl_buf.append(ln)
            continue
        flush_table()
        if not ln.strip():
            continue
        if ln.startswith("# "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para_spacing(p, before=0, after=4)
            add_rich(p, ln[2:], size=17, base_bold=True)
            continue
        if ln.startswith("## "):
            p = doc.add_paragraph()
            para_spacing(p, before=14, after=6)
            add_rich(p, ln[3:], size=13.5, base_bold=True)
            for r in p.runs:
                r.font.color.rgb = NAVY
            add_bottom_border(p)
            continue
        if ln.startswith("### "):
            p = doc.add_paragraph()
            para_spacing(p, before=9, after=3)
            add_rich(p, ln[4:], size=11.5, base_bold=True)
            for r in p.runs:
                if not r.font.bold:
                    r.font.bold = True
            continue
        if ln.startswith("#### "):
            p = doc.add_paragraph()
            para_spacing(p, before=6, after=2)
            add_rich(p, ln[5:], size=10.5, base_bold=True)
            continue
        if ln.startswith("> "):
            p = doc.add_paragraph()
            para_spacing(p, before=2, after=2)
            add_left_border(p)
            shade(p)
            add_rich(p, ln[2:], size=10, color=GREY)
            continue
        if re.match(r"^\s*[-*] ", ln):
            p = doc.add_paragraph()
            para_spacing(p, before=0, after=2)
            pf = p.paragraph_format
            pf.left_indent = Cm(0.62)
            pf.first_line_indent = Cm(-0.62)
            set_run(p.add_run("• "), size=10.5, color=ACCENT)
            add_rich(p, re.sub(r"^\s*[-*] ", "", ln))
            continue
        if re.match(r"^\s*\d+[\.、] ", ln):
            p = doc.add_paragraph()
            para_spacing(p, before=0, after=2)
            pf = p.paragraph_format
            pf.left_indent = Cm(0.62)
            pf.first_line_indent = Cm(-0.62)
            add_rich(p, ln.strip())
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para_spacing(p, before=0, after=4)
        add_rich(p, ln.strip())
    flush_table()
    doc.save(out)
    print("written:", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    out = "out.docx"
    if "-o" in args:
        i = args.index("-o")
        out = args[i + 1]
        args = args[:i] + args[i + 2:]
    build(args, out)
