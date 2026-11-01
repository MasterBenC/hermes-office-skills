#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文公文体 docx 构建模板（GB/T 9704-2012）。改 ORG/DATE/正文即可复用。"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FS, HT, XBS, ST = "仿宋_GB2312", "黑体", "方正小标宋简体", "宋体"
SZ3, SZ2, SZ4, SZ5 = 32, 44, 28, 21          # 三号/二号/四号/五号
ORG, DATE = "×××有限公司", "2026年1月1日"


def set_run(run, name, size, bold=False):
    run.font.size = Pt(size / 2)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    rf.set(qn("w:ascii"), "Times New Roman")
    rf.set(qn("w:hAnsi"), "Times New Roman")
    rf.set(qn("w:eastAsia"), name)


def fmt_para(p, line=560, indent=0, align=None, before=0, after=0,
             right_chars=0, left_chars=0):
    """line=560 -> 固定值28磅；line=0 -> 不设行距（大标题/单元格用）"""
    if align is not None:
        p.alignment = align
    ppr = p._element.get_or_add_pPr()
    if line:
        sp = ppr.find(qn("w:spacing"))
        if sp is None:
            sp = OxmlElement("w:spacing"); ppr.append(sp)
        sp.set(qn("w:line"), str(line)); sp.set(qn("w:lineRule"), "exact")
    sp = ppr.find(qn("w:spacing"))
    if sp is not None:
        sp.set(qn("w:before"), str(before)); sp.set(qn("w:after"), str(after))
    if indent or right_chars or left_chars:
        ind = ppr.find(qn("w:ind"))
        if ind is None:
            ind = OxmlElement("w:ind"); ppr.append(ind)
        if indent:
            ind.set(qn("w:firstLineChars"), str(int(indent * 100)))
            ind.set(qn("w:firstLine"), str(int(indent * 16 * 20)))
        if right_chars:
            ind.set(qn("w:rightChars"), str(int(right_chars * 100)))
            ind.set(qn("w:right"), str(int(right_chars * 16 * 20)))
        if left_chars:
            ind.set(qn("w:leftChars"), str(int(left_chars * 100)))
            ind.set(qn("w:left"), str(int(left_chars * 16 * 20)))
    return p


def add(doc, text, name=FS, size=SZ3, indent=2, align=None, line=560,
        before=0, after=0, right_chars=0):
    p = doc.add_paragraph()
    fmt_para(p, line=line, indent=indent, align=align, before=before,
             after=after, right_chars=right_chars)
    set_run(p.add_run(text), name, size)
    return p


def title(doc, text):
    """text 里的 \n 会变成手动断行"""
    p = doc.add_paragraph()
    fmt_para(p, line=0, indent=0, align=WD_ALIGN_PARAGRAPH.CENTER,
             before=240, after=240)
    for i, seg in enumerate(text.split("\n")):
        if i:
            br = p.add_run(); set_run(br, XBS, SZ2); br.add_break(WD_BREAK.LINE)
        set_run(p.add_run(seg), XBS, SZ2)
    return p


def h1(doc, text):
    return add(doc, text, name=HT, size=SZ3, indent=2)


def setup(doc):
    s = doc.sections[0]
    s.top_margin, s.bottom_margin = Cm(3.7), Cm(3.5)
    s.left_margin, s.right_margin = Cm(2.8), Cm(2.6)
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"; st.font.size = Pt(16)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FS)
    st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.space_after = Pt(0)


def page_numbers(doc, section):
    """单页页码右空一字、双页左空一字"""
    settings = doc.settings.element
    if settings.find(qn("w:evenAndOddHeaders")) is None:
        settings.append(OxmlElement("w:evenAndOddHeaders"))
    for footer, right in ((section.footer, True), (section.even_page_footer, False)):
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        fmt_para(p, line=280, right_chars=1 if right else 0,
                 left_chars=0 if right else 1,
                 align=WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.LEFT)
        set_run(p.add_run("\u2014 "), ST, SZ4)
        fld = OxmlElement("w:fldSimple"); fld.set(qn("w:instr"), " PAGE ")
        run = OxmlElement("w:r"); rpr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        rf.set(qn("w:ascii"), "Times New Roman")
        rf.set(qn("w:hAnsi"), "Times New Roman")
        rf.set(qn("w:eastAsia"), ST); rpr.append(rf)
        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), str(SZ4)); rpr.append(sz)
        run.append(rpr); fld.append(run); p._element.append(fld)
        set_run(p.add_run(" \u2014"), ST, SZ4)


def signature(doc, org, date, before=320):
    p = doc.add_paragraph()
    fmt_para(p, line=560, indent=0, align=WD_ALIGN_PARAGRAPH.RIGHT,
             before=before, right_chars=2)
    set_run(p.add_run(org), FS, SZ3)
    p2 = doc.add_paragraph()
    fmt_para(p2, line=560, indent=0, align=WD_ALIGN_PARAGRAPH.RIGHT, right_chars=4)
    set_run(p2.add_run(date), FS, SZ3)


def fixed_table(doc, rows, w1=2900, w2=5945, h_short=440, h_tall=580):
    """固定版式两列表格，避免 Word 自动重排列宽"""
    t = doc.add_table(rows=len(rows), cols=2)
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed")
    t._tbl.tblPr.append(lay)
    for gc, w in zip(t._tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol")), (w1, w2)):
        gc.set(qn("w:w"), str(w))
    for i, (a, b) in enumerate(rows):
        for j, txt in enumerate((a, b)):
            cell = t.cell(i, j)
            tcW = cell._tc.get_or_add_tcPr().find(qn("w:tcW"))
            tcW.set(qn("w:type"), "dxa"); tcW.set(qn("w:w"), str(w1 if j == 0 else w2))
            cp = cell.paragraphs[0]
            fmt_para(cp, line=320, indent=0, align=WD_ALIGN_PARAGRAPH.LEFT)
            set_run(cp.add_run(txt), FS, SZ5)
        trPr = t.rows[i]._tr.get_or_add_trPr()
        h = OxmlElement("w:trHeight")
        h.set(qn("w:val"), str(h_short if i < 3 else h_tall))
        h.set(qn("w:hRule"), "atLeast"); trPr.append(h)
    return t


if __name__ == "__main__":
    d = Document(); setup(d)
    title(d, "关于×××工作\n开展情况的报告")
    add(d, "现将有关情况报告如下。")
    h1(d, "一、基本情况")
    add(d, "（正文）")
    signature(d, ORG, DATE)
    page_numbers(d, d.sections[0])
    d.save("/tmp/gongwen.docx")
    print("saved /tmp/gongwen.docx")
