#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文简历版式引擎：一套事实底座，N 个求职方向。

配套 content_template.py 使用。关键点（别改坏）：
  - lh>0 时走固定行距 w:lineRule=exact，Word 与 LibreOffice 渲染逐毫米一致
  - pf.widow_control=False，否则最后一段会被整段挤到第 2 页
  - EA 字体可用环境变量 RESUME_EA 覆盖（出 PDF 用本机真有的字体）
"""
import os
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

EA = os.environ.get("RESUME_EA", "微软雅黑")   # 中文字体（出 PDF 时可用 RESUME_EA 换成本机可用的字体）
LAT = "Arial"        # 西文字体
NAVY = "1F3A5F"
GREY = "555555"
BODY = "262626"
CONTENT_W = 174      # mm（由页边距推算，build() 里会覆写）

COMPACT = False      # 紧凑模式：给内容多的版本用
LN = 1.0             # 行距系数（<1 收紧）
SP = 1.0             # 段间距系数（<1 收紧）

LF = 1.0             # 字号系数（出 PDF 时按字体度量微调）
LH = 0.0             # >0 时用固定行距 = line * LH (pt)：Word 与 LibreOffice 渲染完全一致

# ---------------------------------------------------------------- low level
def _ea(run, font_ea=EA):
    rPr = run._element.get_or_add_rPr()
    rf = rPr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts'); rPr.append(rf)
    rf.set(qn('w:ascii'), LAT); rf.set(qn('w:hAnsi'), LAT); rf.set(qn('w:eastAsia'), font_ea)

def style_run(run, size=10.5, bold=False, color=BODY, italic=False, ea=EA):
    run.font.size = Pt(size * LF); run.bold = bold; run.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    run.font.name = LAT
    _ea(run, ea)

def para(doc, space_before=0, space_after=2, line=1.22, align=None, left=0, first=0, exact=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before * SP); pf.space_after = Pt(space_after * SP)
    if exact is not None:
        pf.line_spacing = Pt(exact)
    elif LH:
        pf.line_spacing = Pt(line * LH)      # 固定行距，与字体度量无关
    else:
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE; pf.line_spacing = line * LN
    if align is not None: p.alignment = align
    pf.widow_control = False   # 关掉孤行控制：否则最后一段会被整段挤到第 2 页
    if left: pf.left_indent = Mm(left)
    if first: pf.first_line_indent = Mm(first)
    return p

def bottom_border(p, color=NAVY, sz=8, space=3):
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr')
    b = OxmlElement('w:bottom')
    b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), str(sz))
    b.set(qn('w:space'), str(space)); b.set(qn('w:color'), color)
    pbdr.append(b); pPr.append(pbdr)

def right_tab(p):
    p.paragraph_format.tab_stops.add_tab_stop(Mm(CONTENT_W), WD_TAB_ALIGNMENT.RIGHT)

# ---------------------------------------------------------------- blocks
def add_section(doc, text):
    p = para(doc, space_before=6 if COMPACT else 9, space_after=3 if COMPACT else 4, line=1.0)
    r = p.add_run(text); style_run(r, size=11.5 if COMPACT else 12, bold=True, color=NAVY, ea=EA)
    bottom_border(p)

def add_head_row(doc, left_texts, right_text, space_before=None):
    if space_before is None:
        space_before = 2.0 if COMPACT else 4
    p = para(doc, space_before=space_before, space_after=0.5 if COMPACT else 1, line=1.05 if COMPACT else 1.12)
    right_tab(p)
    for t, bold in left_texts:
        r = p.add_run(t); style_run(r, size=10.5, bold=bold, color="111111" if bold else BODY)
    r = p.add_run("\t" + right_text); style_run(r, size=10 if not COMPACT else 9.5, color=GREY)

def add_bullets(doc, items):
    for it in items:
        p = para(doc, space_after=0.5 if COMPACT else 1,
                 line=1.06 if COMPACT else 1.2, left=5.2, first=-5.2)
        r = p.add_run("▪  "); style_run(r, size=10.5, color=NAVY, bold=True)
        for i, seg in enumerate(it.split("**")):
            if not seg: continue
            r = p.add_run(seg); style_run(r, size=10.5, bold=(i % 2 == 1),
                                          color="111111" if i % 2 == 1 else BODY)

def add_kv_line(doc, k, v):
    p = para(doc, space_after=0.5 if COMPACT else 1, line=1.06 if COMPACT else 1.2,
             left=5.2, first=-5.2)
    r = p.add_run("▪  "); style_run(r, size=10.5, color=NAVY, bold=True)
    r = p.add_run(k); style_run(r, size=10.5, bold=True, color="111111")
    r = p.add_run("：" + v); style_run(r, size=10.5, color=BODY)

def build(data, out_path):
    global COMPACT, LN, SP, CONTENT_W, LF, LH
    COMPACT = bool(data.get("compact"))
    LN = float(data.get("ln", 1.0))
    SP = float(data.get("sp", 1.0))
    LF = float(data.get("lf", 1.0))
    LH = float(data.get("lh", 0.0))

    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Mm(210); sec.page_height = Mm(297)
    top, bot, left, right = data.get("margins") or ((13, 13, 18, 18) if COMPACT else (15, 14, 18, 18))
    sec.top_margin = Mm(top); sec.bottom_margin = Mm(bot)
    sec.left_margin = Mm(left); sec.right_margin = Mm(right)
    CONTENT_W = 210 - left - right

    st = doc.styles['Normal']
    st.font.size = Pt(10.5 * LF); st.font.name = LAT
    st.element.rPr.rFonts.set(qn('w:eastAsia'), EA)

    # ---- 抬头
    p = para(doc, space_after=1, line=1.0, exact=(26 if LH else None))
    r = p.add_run(data["name"]); style_run(r, size=20 if COMPACT else 21, bold=True, color=NAVY)
    r = p.add_run("    " + data["tagline"]); style_run(r, size=10.5, color=GREY)
    p = para(doc, space_after=4, line=1.1)
    r = p.add_run(data["contact"]); style_run(r, size=9.5, color=GREY)
    bottom_border(p, color=NAVY, sz=12, space=4)

    # ---- 个人概述
    add_section(doc, "个人概述")
    p = para(doc, space_after=2, line=1.2 if COMPACT else 1.32,
             align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    for i, seg in enumerate(data["summary"].split("**")):
        if not seg: continue
        r = p.add_run(seg); style_run(r, size=10.5, bold=(i % 2 == 1),
                                      color=NAVY if i % 2 == 1 else BODY)

    # ---- 核心能力
    add_section(doc, "核心能力")
    add_bullets(doc, data["skills_core"])

    def render_projects():
        add_section(doc, data["projects_title"])
        for pj in data["projects"]:
            add_head_row(doc, [(pj["name"], True), ("　|　" + pj["role"], False)], pj.get("period", ""))
            add_bullets(doc, pj["bullets"])

    def render_jobs():
        add_section(doc, "工作经历")
        for job in data["jobs"]:
            add_head_row(doc, [(job["org"], True), ("　|　" + job["title"], False)], job["period"])
            add_bullets(doc, job["bullets"])

    if data.get("projects") and data.get("projects_first"):
        render_projects(); render_jobs()
    else:
        render_jobs()
        if data.get("projects"):
            render_projects()

    # ---- 教育背景
    add_section(doc, "教育背景")
    for ed in data["education"]:
        add_head_row(doc, [(ed["school"], True), ("　|　" + ed["degree"], False)], ed["period"])

    # ---- 资质与技能
    add_section(doc, "资质与技能")
    for k, v in data["certs"]:
        add_kv_line(doc, k, v)

    doc.save(out_path)
    return out_path
