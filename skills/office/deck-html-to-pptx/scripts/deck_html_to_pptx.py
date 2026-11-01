#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deck_html_to_pptx.py — 把 business-deck-pdf 风格的自制 HTML 横版汇报稿
(1440x810px, @page size) 转成**可编辑**的 16:9 .pptx。

不是把 PDF 截图塞进去:文字全部是可选中可编辑的文本框/表格。

用法:
  python deck_html_to_pptx.py deck.html out.pptx [--font 微软雅黑] [--json report.json]

字号换算: HTML px * 2/3 = pt (1440px 宽 -> 13.333in = 960pt)
支持的 class(与 deck 模板一致):
  dark(封面/章节页/尾页) kicker cover-title cover-sub cover-rule cover-tags cover-foot
  sec-num sec-title sec-line hd h2 hdnote body brandfoot pn
  lead muted note quote cards card(grow) ctag two col steps step(sh/sb/sd)
  tbl tr(head/hi) th td(em) c1 c2 c3 c4 cA cB cC numrow numcell(n/l) databar(v/k) bigvs(vs1/vsdiv)
"""
import sys, os, re, json, math, argparse
from html.parser import HTMLParser

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml.ns import qn

# ---------------------------------------------------------------- 设计常量
PX2PT = 2.0 / 3.0
SLIDE_W_PX, SLIDE_H_PX = 1440.0, 810.0
PAD_L, PAD_R, PAD_T, PAD_B = 76.0, 76.0, 58.0, 54.0
BODY_GAP = 20.0

NAVY = RGBColor(0x1B, 0x3A, 0x5C)
GOLD = RGBColor(0xB8, 0x93, 0x4A)
GOLD_L = RGBColor(0xC8, 0xA4, 0x5C)
CREAM = RGBColor(0xF6, 0xF4, 0xF0)
NOTE_BG = RGBColor(0xFB, 0xF8, 0xF2)
NOTE_LN = RGBColor(0xC9, 0xBD, 0xA6)
BORDER = RGBColor(0xE3, 0xDE, 0xD6)
BORDER2 = RGBColor(0xE6, 0xE1, 0xD9)
TX = RGBColor(0x3C, 0x3C, 0x3C)
TX_DARK = RGBColor(0x33, 0x33, 0x33)
TX_MUTED = RGBColor(0x7D, 0x7D, 0x7D)
TX_GREY = RGBColor(0x8A, 0x8A, 0x8A)
TX_NOTE = RGBColor(0x5C, 0x53, 0x47)
TX_LABEL = RGBColor(0x6D, 0x6D, 0x6D)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FOOT = RGBColor(0xB3, 0xB3, 0xB3)
GOLD_TXT = RGBColor(0x8F, 0x6F, 0x2E)
GOLD_TODO = RGBColor(0xB8, 0x93, 0x4A)


def px(v):
    return Emu(int(round(v * 12700 * PX2PT)))  # px -> EMU via pt


# 当前页的全局字号缩放（整页装不下时整体缩一点，而不是让文字被后面的图形盖住）
SC = 1.0


def S(v):
    return v * SC


GEOM = {}


def cur_budget(avail_bottom, y0, hs, gap):
    return avail_bottom - y0


# ---------------------------------------------------------------- HTML 解析
class Node:
    __slots__ = ("tag", "cls", "attrs", "children", "parent", "text")

    def __init__(self, tag, attrs=None, text=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.cls = (self.attrs.get("class") or "").split()
        self.children = []
        self.parent = parent
        self.text = text or ""

    def has(self, c):
        return c in self.cls

    def find_all(self, tag=None, cls=None):
        out = []
        for ch in self.children:
            if ch.tag == "#text":
                continue
            if (tag is None or ch.tag == tag) and (cls is None or ch.has(cls)):
                out.append(ch)
            out.extend(ch.find_all(tag, cls))
        return out

    def direct(self, cls=None, tag=None):
        return [c for c in self.children
                if c.tag != "#text" and (cls is None or c.has(cls)) and (tag is None or c.tag == tag)]

    def one(self, cls=None, tag=None):
        d = self.direct(cls, tag)
        return d[0] if d else None


VOID = {"br", "img", "hr", "meta", "link", "input"}


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, parent=self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, parent=self.cur))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        if data.strip():
            self.cur.children.append(Node("#text", text=re.sub(r"\s+", " ", data), parent=self.cur))


# ---------------------------------------------------------------- 行内片段
def segs(node, bold=False, color=None, sf=1.0):
    """把一段 DOM 摊平成 [(text, bold, color, sf)]，br -> ('\\n',...)。"""
    out = []
    for ch in node.children:
        if ch.tag == "#text":
            t = ch.text
            if t.strip() or (out and out[-1][0] != "\n"):
                out.append((t if t.strip() else " ", bold, color, sf))
            continue
        b, c, s = bold, color, sf
        if ch.tag in ("b", "strong"):
            b = True
        if ch.has("muted"):
            c, s = (c or TX_MUTED), sf * 0.9
        if ch.has("todo"):
            c, b, s = GOLD_TODO, True, sf
        if ch.tag == "br":
            out.append(("\n", False, None, 1.0))
            continue
        out.extend(segs(ch, b, c, s))
    return out


def clean_segs(sl):
    txt = "".join(x[0] for x in sl).strip()
    out = []
    for x in sl:
        if x[0] == "":
            continue
        out.append(x)
    # 去掉行首尾空白段
    while out and out[0][0].strip() == "":
        out.pop(0)
    while out and out[-1][0].strip() == "":
        out.pop()
    return out, txt


def eff_len(t):
    return sum(0.56 if ord(c) < 0x2000 else 1.0 for c in t)


def est_lines(segs_list, width_in, pt):
    """segs_list: 段落(已按 br 拆好)的列表 -> 行数"""
    total = 0
    for para in segs_list:
        t = "".join(x[0] for x in para)
        cpl = max(4.0, width_in * 72.0 / max(pt, 1.0))
        total += max(1, math.ceil(eff_len(t) / cpl))
    return max(1, total)


def split_paras(sl):
    paras, cur = [], []
    for x in sl:
        if x[0] == "\n":
            paras.append(cur or [(" ", False, None, 1.0)])
            cur = []
        else:
            cur.append(x)
    paras.append(cur or [(" ", False, None, 1.0)])
    return paras


# ---------------------------------------------------------------- 绘图助手
class Deck:
    def __init__(self, font):
        self.font = font
        self.prs = Presentation()
        self.prs.slide_width = Inches(SLIDE_W_PX * PX2PT / 72.0)
        self.prs.slide_height = Inches(SLIDE_H_PX * PX2PT / 72.0)
        self.blank = self.prs.slide_layouts[6]
        self.warn = []

    # -- 基础
    def slide(self):
        return self.prs.slides.add_slide(self.blank)

    def _font(self, run, pt, bold, color):
        f = run.font
        # 注意：全脚本里字号都以「HTML 像素」为单位，这里统一换算成磅（1px = 0.75pt）
        f.size = Pt(pt * PX2PT)
        f.bold = bool(bold)
        f.name = self.font
        f.color.rgb = color if color is not None else TX
        rPr = run._r.get_or_add_rPr()
        ea = rPr.find(qn("a:ea"))
        if ea is None:
            ea = rPr.makeelement(qn("a:ea"), {})
            rPr.append(ea)
        ea.set("typeface", self.font)

    def rect(self, sl, x, y, w, h, fill=None, line=None, lw=0.75, dash=None, shape=MSO_SHAPE.RECTANGLE):
        s = sl.shapes.add_shape(shape, px(x), px(y), px(w), px(h))
        s.shadow.inherit = False
        if fill is None:
            s.fill.background()
        else:
            s.fill.solid()
            s.fill.fore_color.rgb = fill
        if line is None:
            s.line.fill.background()
        else:
            s.line.color.rgb = line
            s.line.width = Pt(lw)
            if dash:
                s.line.dash_style = dash
        return s

    def text_box(self, sl, x, y, w, h, paras, size, color=TX, align=PP_ALIGN.LEFT,
                 anchor=MSO_ANCHOR.TOP, lh=1.6, space_after=0, bold=False):
        """paras: 段落列表，每段是 segs 列表"""
        tb = sl.shapes.add_textbox(px(x), px(y), px(w), px(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        first = True
        for para in paras:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.alignment = align
            # 用"固定值"行距，使 PPT 行高 = pt*lh，与 HTML 的 line-height 语义一致
            # （若用倍数，PPT 会按字体单倍行距的 1.2 倍再乘，中文会高 20% 左右）
            p.line_spacing = Pt(size * lh * PX2PT)
            if space_after:
                p.space_after = Pt(space_after * PX2PT)
            for t, b, c, sf in para:
                if not t:
                    continue
                r = p.add_run()
                r.text = t
                self._font(r, size * sf, b or bold, c if c is not None else color)
        return tb

    def text_h(self, paras, w_in, pt, lh=1.6):
        return est_lines(paras, w_in, pt) * pt * lh * 72.0 / 72.0 / (72.0 / 72.0) / 1.0 * (96.0 / 72.0)


# 上面 text_h 单位换算容易出错，改为统一函数：
def h_px(paras, w_px, pt, lh=1.6):
    """返回需要的像素高度（HTML 坐标系）"""
    lines = est_lines(paras, w_px * PX2PT / 72.0, pt * PX2PT)
    # pt->
    return lines * pt * lh + 2


# ---------------------------------------------------------------- 各块渲染
def render_paragraph(D, sl, node, x, y, w):
    cls = node.cls
    if "lead" in cls:
        pt, color, lh, pad = 24.5, NAVY, 1.8, 10
    elif "muted" in cls:
        pt, color, lh, pad = 19.0, TX_MUTED, 1.7, 6
    else:
        pt, color, lh, pad = 22.0, TX_DARK, 1.8, 8
    sl_, _ = clean_segs(segs(node))
    paras = split_paras(sl_)
    h = h_px(paras, w, pt, lh) + pad
    D.text_box(sl, x, y, w, h, paras, pt, color, lh=lh)
    return h


def render_note(D, sl, node, x, y, w):
    sl_, _ = clean_segs(segs(node))
    paras = split_paras(sl_)
    pt, lh = 19.0, 1.72
    inner = w - 44
    th = h_px(paras, inner, S(pt), lh)
    h = th + 34
    D.rect(sl, x, y, w, h, fill=NOTE_BG, line=NOTE_LN, lw=0.75, dash=MSO_LINE_DASH_STYLE.DASH)
    D.text_box(sl, x + 20, y + 16, inner, th + 4, paras, S(pt), TX_NOTE, lh=lh)
    return h


def render_quote(D, sl, node, x, y, w):
    sl_, _ = clean_segs(segs(node))
    paras = split_paras(sl_)
    pt, lh = 23.0, 1.8
    inner = w - 56
    th = h_px(paras, inner, S(pt), lh)
    h = th + 40
    D.rect(sl, x, y, w, h, fill=CREAM)
    D.rect(sl, x, y, 4, h, fill=GOLD)
    D.text_box(sl, x + 28, y + 20, inner, th + 4, paras, S(pt), NAVY, lh=lh,
               anchor=MSO_ANCHOR.MIDDLE)
    return h


def render_numrow(D, sl, node, x, y, w):
    cells = node.direct("numcell")
    n = len(cells)
    gap = 22.0
    cw = (w - gap * (n - 1)) / n
    hs = []
    data = []
    for c in cells:
        nnum = c.one("n")
        nlab = c.one("l")
        nseg, _ = clean_segs(segs(nnum)) if nnum is not None else ([(" ", False, None, 1)], "")
        lseg, _ = clean_segs(segs(nlab)) if nlab is not None else ([(" ", False, None, 1)], "")
        npt = S(62.5)
        h1 = h_px(split_paras(nseg), cw - 24, npt, 1.1)
        h2 = h_px(split_paras(lseg), cw - 24, S(19.0), 1.6)
        hs.append(h1 + h2 + 22)
        data.append((nseg, lseg, h1, h2))
    h = max(hs)
    for i, (nseg, lseg, h1, h2) in enumerate(data):
        cx = x + i * (cw + gap)
        D.rect(sl, cx, y + 6, 4, h - 12, fill=NAVY)
        D.text_box(sl, cx + 20, y + 6, cw - 24, h1 + 4, split_paras(nseg), npt, NAVY, lh=1.1, bold=True)
        D.text_box(sl, cx + 20, y + 6 + h1 + 8, cw - 24, h2 + 4, split_paras(lseg), S(19.0), TX_LABEL, lh=1.6)
    return h


def render_databar(D, sl, node, x, y, w):
    cells = node.direct(tag="div")
    n = max(1, len(cells))
    cw = w / n
    rows = []
    for c in cells:
        v = c.one("v")
        k = c.one("k")
        vseg, _ = clean_segs(segs(v)) if v is not None else ([(" ", False, None, 1)], "")
        kseg, _ = clean_segs(segs(k)) if k is not None else ([(" ", False, None, 1)], "")
        h1 = h_px(split_paras(vseg), cw - 44, S(41.5), 1.1)
        h2 = h_px(split_paras(kseg), cw - 44, S(17.5), 1.5)
        rows.append((vseg, kseg, h1, h2))
    h = max(r[2] + r[3] for r in rows) + 44
    D.rect(sl, x, y, w, h, fill=NAVY)
    for i, (vseg, kseg, h1, h2) in enumerate(rows):
        cx = x + i * cw
        D.text_box(sl, cx + 22, y + 18, cw - 44, h1 + 2, split_paras(vseg), S(41.5), WHITE, lh=1.1,
                   align=PP_ALIGN.CENTER, bold=True)
        D.text_box(sl, cx + 22, y + 18 + h1 + 4, cw - 44, h2 + 2, split_paras(kseg), S(17.5),
                   RGBColor(0xC9, 0xD4, 0xE0), lh=1.5, align=PP_ALIGN.CENTER)
    return h


def render_bigvs(D, sl, node, x, y, w):
    kids = [c for c in node.children if c.tag != "#text"]
    pt = 70.0
    inner = w - 56
    # 先算高度
    heights = []
    for c in kids:
        if c.has("vs1"):
            nseg, _ = clean_segs(segs(c.one("n")))
            lseg, _ = clean_segs(segs(c.one("l")))
            h1 = h_px(split_paras(nseg), inner * 0.4, S(pt), 1.0)
            h2 = h_px(split_paras(lseg), inner * 0.4, S(19.5), 1.5)
            heights.append(h1 + h2 + 12)
        else:
            heights.append(0)
    h = max(heights) + 44
    D.rect(sl, x, y, w, h, fill=CREAM)
    # 横向均分
    n_vs = sum(1 for c in kids if c.has("vs1"))
    divw = 90.0
    cw = (w - 56 - divw * (len(kids) - n_vs)) / max(1, n_vs)
    cx = x + 28
    for c in kids:
        if c.has("vs1"):
            nseg, _ = clean_segs(segs(c.one("n")))
            lseg, _ = clean_segs(segs(c.one("l")))
            h1 = h_px(split_paras(nseg), cw, S(pt), 1.0)
            h2 = h_px(split_paras(lseg), cw, S(19.5), 1.5)
            top = y + (h - (h1 + h2 + 12)) / 2
            D.text_box(sl, cx, top, cw, h1 + 2, split_paras(nseg), S(pt), NAVY, lh=1.0,
                       align=PP_ALIGN.CENTER, bold=True)
            D.text_box(sl, cx, top + h1 + 10, cw, h2 + 2, split_paras(lseg), S(19.5), TX_LABEL,
                       lh=1.5, align=PP_ALIGN.CENTER)
            cx += cw
        else:
            seg, _ = clean_segs(segs(c))
            D.text_box(sl, cx, y + (h - 50) / 2, divw, 50, split_paras(seg), S(39.0), GOLD,
                       lh=1.0, align=PP_ALIGN.CENTER, bold=True)
            cx += divw
    return h


def render_steps(D, sl, node, x, y, w, min_h=0, dry=False):
    steps = node.direct("step")
    n = max(1, len(steps))
    gap = 12.0
    cw = (w - gap * (n - 1)) / n
    body_h = 0
    for s in steps:
        sb = s.one("sb")
        seg, _ = clean_segs(segs(sb)) if sb is not None else ([(" ", False, None, 1)], "")
        body_h = max(body_h, h_px(split_paras(seg), cw - 28, S(18.0), 1.6))
    sd_h = 0
    for s in steps:
        sd = s.one("sd")
        seg, _ = clean_segs(segs(sd)) if sd is not None else ([(" ", False, None, 1)], "")
        sd_h = max(sd_h, h_px(split_paras(seg), cw - 24, S(17.0), 1.5))
    sh_h = 40.0
    h = max(min_h, sh_h + body_h + 28 + sd_h + 18)
    if dry:
        return h
    for i, s in enumerate(steps):
        cx = x + i * (cw + gap)
        D.rect(sl, cx, y, cw, h, fill=WHITE, line=BORDER)
        sh = s.one("sh")
        seg, _ = clean_segs(segs(sh)) if sh is not None else ([(" ", False, None, 1)], "")
        D.rect(sl, cx, y, cw, sh_h, fill=NAVY)
        D.text_box(sl, cx + 12, y + 9, cw - 24, sh_h - 12, split_paras(seg), S(18.0), WHITE, lh=1.3)
        sb = s.one("sb")
        segb, _ = clean_segs(segs(sb)) if sb is not None else ([(" ", False, None, 1)], "")
        D.text_box(sl, cx + 14, y + sh_h + 14, cw - 28, body_h + 4, split_paras(segb), S(18.0), TX, lh=1.6)
        sd = s.one("sd")
        segd, _ = clean_segs(segs(sd)) if sd is not None else ([(" ", False, None, 1)], "")
        dy = y + h - sd_h - 18
        D.rect(sl, cx, dy, cw, sd_h + 18, fill=CREAM)
        D.text_box(sl, cx + 12, dy + 9, cw - 24, sd_h + 4, split_paras(segd), S(17.0), GOLD_TXT, lh=1.5)
    return h


def render_cards(D, sl, node, x, y, w, min_h=0, dry=False):
    cards = [c for c in node.children if c.tag != "#text" and c.has("card")]
    if not cards:
        cards = node.find_all(cls="card")
    n = max(1, len(cards))
    gap = 20.0
    cw = (w - gap * (n - 1)) / n
    info, hs = [], []
    for c in cards:
        segs_all = []
        ctag = c.one("ctag")
        if ctag is not None:
            s_, _ = clean_segs(segs(ctag))
            segs_all.append(("ctag", split_paras(s_), S(17.0), GOLD, 1.4, 12))
        h3 = c.one(tag="h3")
        if h3 is not None:
            s_, _ = clean_segs(segs(h3))
            segs_all.append(("h3", split_paras(s_), S(26.0), NAVY, 1.35, 12))
        for blk in c.children:
            if blk.tag == "p":
                s_, _ = clean_segs(segs(blk))
                segs_all.append(("p", split_paras(s_), S(19.5), TX, 1.7, 6))
            elif blk.tag == "ul":
                for li in blk.find_all(tag="li"):
                    s_, _ = clean_segs(segs(li))
                    segs_all.append(("li", split_paras(s_), S(19.5), TX, 1.6, 9))
        hh = 48.0
        for kind, paras, pt, col, lh, sa in segs_all:
            hh += h_px(paras, cw - 52, pt, lh) + sa * 0.6
        info.append((c, segs_all, hh))
        hs.append(hh)
    h = max(max(hs), min_h)
    if dry:
        return h
    for i, (c, segs_all, hh) in enumerate(info):
        cx = x + i * (cw + gap)
        plain = c.has("plain")
        D.rect(sl, cx, y, cw, h, fill=WHITE if plain else CREAM,
               line=BORDER if plain else None)
        D.rect(sl, cx, y, cw, 3, fill=NAVY if plain else GOLD)
        cy = y + 24
        for kind, paras, pt, col, lh, sa in segs_all:
            hh2 = h_px(paras, cw - 52, pt, lh)
            if kind == "li":
                D.rect(sl, cx + 26, cy + 10, 5, 5, fill=GOLD)
                D.text_box(sl, cx + 40, cy, cw - 66, hh2 + 4, paras, pt, col, lh=lh)
            else:
                D.text_box(sl, cx + 26, cy, cw - 52, hh2 + 4, paras, pt, col, lh=lh)
            cy += hh2 + sa * 0.6
    return h


def render_two(D, sl, node, x, y, w, min_h=0, dry=False):
    cols = node.direct("col")
    n = max(1, len(cols))
    gap = 34.0
    cw = (w - gap * (n - 1)) / n
    infos, hs = [], []
    for c in cols:
        items = []
        hd3 = c.one(tag="h3")
        hh = 0
        if hd3 is not None:
            s_, _ = clean_segs(segs(hd3))
            hh += h_px(split_paras(s_), cw - 10, 24.5, 1.4) + 24
            items.append(("h3", split_paras(s_), S(24.5), NAVY, 1.4, 24))
        ul = c.one(tag="ul")
        if ul is not None:
            for li in ul.find_all(tag="li"):
                s_, _ = clean_segs(segs(li))
                hh += h_px(split_paras(s_), cw - 34, 19.5, 1.66) + 11
                items.append(("li", split_paras(s_), S(19.5), TX, 1.66, 11))
        else:
            for p in c.direct(tag="p"):
                s_, _ = clean_segs(segs(p))
                hh += h_px(split_paras(s_), cw - 10, 19.5, 1.7) + 10
                items.append(("p", split_paras(s_), S(19.5), TX, 1.7, 10))
        infos.append(items)
        hs.append(hh)
    h = max(max(hs), min_h)
    if dry:
        return h
    for i, items in enumerate(infos):
        cx = x + i * (cw + gap)
        boxed = "background" in (cols[i].attrs.get("style") or "")
        if boxed:
            D.rect(sl, cx - 26, y, cw + 24, h, fill=CREAM)
        cy = y + (26 if boxed else 0)
        for kind, paras, pt, col, lh, sa in items:
            hh2 = h_px(paras, cw - (34 if kind == "li" else 10), pt, lh)
            if kind == "h3":
                D.text_box(sl, cx, cy, cw - 10, hh2 + 4, paras, pt, col, lh=lh, bold=True)
                D.rect(sl, cx, cy + hh2 + 10, cw - 10, 1, fill=BORDER)
            elif kind == "li":
                D.rect(sl, cx + 1, cy + 10, 5, 5, fill=GOLD)
                D.text_box(sl, cx + 15, cy, cw - 34, hh2 + 4, paras, pt, col, lh=lh)
            else:
                D.text_box(sl, cx, cy, cw - 10, hh2 + 4, paras, pt, col, lh=lh)
            cy += hh2 + sa
    return h


def _set_cell_border(cell, color=BORDER2, w=0.75, edges=("L", "R", "T", "B")):
    tcPr = cell._tc.get_or_add_tcPr()
    tagmap = {"L": "a:lnL", "R": "a:lnR", "T": "a:lnT", "B": "a:lnB"}
    for e in reversed(list(edges)):
        tag = qn(tagmap[e])
        for el in tcPr.findall(tag):
            tcPr.remove(el)
        ln = tcPr.makeelement(tag, {"w": str(int(Pt(w))), "cap": "flat", "cmpd": "sng", "algn": "ctr"})
        fill = ln.makeelement(qn("a:solidFill"), {})
        clr = ln.makeelement(qn("a:srgbClr"), {"val": "%02X%02X%02X" % (color[0], color[1], color[2])
                                               if isinstance(color, tuple) else str(color)})
        fill.append(clr)
        ln.append(fill)
        tcPr.insert(0, ln)


def render_table(D, sl, x, y, w, node, avail_h, font_scale=1.0, dry=False, target_h=None):
    rows = [c for c in node.children if c.tag != "#text" and c.has("tr")]
    if not rows:
        return 0
    # 列定义: 表头每个 .th/.td 的 flex 权重
    FIX = {"c1": 0.20, "c4": 0.24, "cA": 0.24, "cC": 0.30}
    head = rows[0]
    hcells = [c for c in head.children if c.tag != "#text"]
    weights, ncol = [], 0
    flexsum = 0.0
    for c in hcells:
        span = int(c.attrs.get("colspan", 1) or 1)
        if span > 1:
            weights.extend([1.0] * span)
            flexsum += span
        else:
            fixed = next((FIX[k] for k in FIX if k in c.cls), None)
            weights.append(fixed if fixed is not None else None)
            if fixed is None:
                flexsum += 1.0
        ncol += span
    # 用剩余的列宽
    fixedw = sum(wt for wt in weights if wt)
    gap_px = 0
    usable = w - gap_px
    rest = max(0.05, 1.0 - fixedw)
    cols_px = []
    for wt in weights:
        if wt:
            cols_px.append(usable * wt)
        else:
            cols_px.append(usable * rest / max(1.0, flexsum))
    base_pt = S(19.0) * font_scale
    head_pt = S(19.5) * font_scale
    pad_x, pad_y = 16.0, 11.0
    # 行高估算
    row_h, cells_txt = [], []
    for ri, r in enumerate(rows):
        is_head = r.has("head")
        cs = [c for c in r.children if c.tag != "#text"]
        pt = head_pt if is_head else base_pt
        mx = 0.0
        cinfo = []
        ci = 0
        for c in cs:
            span = int(c.attrs.get("colspan", 1) or 1)
            cwid = sum(cols_px[ci:ci + span])
            ci += span
            s_, _ = clean_segs(segs(c))
            paras = split_paras(s_)
            hh = h_px(paras, cwid - 2 * pad_x, pt, 1.6)
            mx = max(mx, hh)
            cinfo.append((c, paras, span, cwid))
        hrow = max(mx + 2 * pad_y, 46.0 if is_head else 40.0)
        row_h.append(hrow)
        cells_txt.append((r, cinfo, is_head))
    total = sum(row_h)
    tgt = target_h if target_h else avail_h
    if tgt and tgt > 0:
        k = tgt / max(1.0, total)
        if k < 0.999:
            # 浏览器里表格会被 flex 压扁，这里按同比例压行高（不裁字）
            k = max(0.78, k)
            row_h = [r * k for r in row_h]
        else:
            share = (tgt - total) / max(1, len(row_h) - 1)
            for i in range(1, len(row_h)):
                row_h[i] += share
        total = sum(row_h)
    if dry:
        return max(total, 100)
    # 建表
    shape = sl.shapes.add_table(len(rows), ncol, px(x), px(y), px(w), px(max(total, 100)))
    tbl = shape.table
    tblPr = tbl._tbl.tblPr
    tblPr.set("firstRow", "0")
    tblPr.set("bandRow", "0")
    for el in tblPr.findall(qn("a:tableStyleId")):
        tblPr.remove(el)
    sid = tblPr.makeelement(qn("a:tableStyleId"), {})
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # No Style, No Grid
    tblPr.append(sid)
    for j, wt in enumerate(cols_px):
        tbl.columns[j].width = px(wt)
    for i, hrow in enumerate(row_h):
        tbl.rows[i].height = px(hrow)
    for i, (r, cinfo, is_head) in enumerate(cells_txt):
        idx = 0
        for (c, paras, span, cwid) in cinfo:
            cell = tbl.cell(i, idx)
            if span > 1:
                try:
                    cell.merge(tbl.cell(i, min(ncol - 1, idx + span - 1)))
                except Exception:
                    pass
            cell.margin_left = px(pad_x)
            cell.margin_right = px(pad_x)
            cell.margin_top = px(4)
            cell.margin_bottom = px(4)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if is_head:
                cell.fill.fore_color.rgb = NAVY
            elif r.has("hi"):
                cell.fill.fore_color.rgb = CREAM
            else:
                cell.fill.fore_color.rgb = WHITE
            is_em = c.has("em")
            pt = (head_pt if is_head else base_pt) * (0.9 if c.has("muted") else 1.0)
            color = WHITE if is_head else (NAVY if is_em else RGBColor(0x3A, 0x3A, 0x3A))
            tf = cell.text_frame
            tf.word_wrap = True
            first = True
            for para in paras:
                p = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                p.line_spacing = Pt(pt * 1.6 * PX2PT)
                for t, b, cc, sf in para:
                    if not t:
                        continue
                    run = p.add_run()
                    run.text = t
                    D._font(run, pt * sf, b or is_em or is_head, cc if cc is not None else color)
            _set_cell_border(cell, color=(0xE6, 0xE1, 0xD9), w=0.75)
            idx += span
    return max(total, 100)


# ---------------------------------------------------------------- 页面渲染
def _kind(b):
    if b.has("tbl"):
        return "tbl"
    if b.has("cards") or b.has("grow"):
        return "cards"
    if b.has("two"):
        return "two"
    if b.has("note"):
        return "note"
    if b.has("quote"):
        return "quote"
    if b.has("steps"):
        return "steps"
    if b.has("numrow"):
        return "numrow"
    if b.has("databar"):
        return "databar"
    if b.has("bigvs"):
        return "bigvs"
    return "p"


def block_h(D, k, b, x0, w):
    """只测量不绘制"""
    if k == "tbl":
        return render_table(D, None, x0, 0, w, b, 0, dry=True)
    if k == "cards":
        return render_cards(D, fakeslide(D), b, x0, 0, w, dry=True)
    if k == "two":
        return render_two(D, fakeslide(D), b, x0, 0, w, dry=True)
    if k == "steps":
        return render_steps(D, fakeslide(D), b, x0, 0, w, dry=True)
    return _static_h(D, fakeslide(D), k, b, x0, w, dry=True)


class _FakeBody:
    def __init__(self, D):
        self.D = D

    def add_textbox(self, *a, **kw):
        raise RuntimeError("dry-run should not draw")


def fakeslide(D):
    return _FakeBody(D)


def content_slide(D, sl_node):
    global SC
    W = SLIDE_W_PX
    x0, w = PAD_L, W - PAD_L - PAD_R
    hd = sl_node.one("hd")
    y0 = PAD_T
    title_h = 0.0
    if hd is not None:
        h2 = hd.one(tag="h2")
        s_, _ = clean_segs(segs(h2)) if h2 is not None else ([(" ", False, None, 1)], "")
        title_h = h_px(split_paras(s_), w * 0.78, 44.0, 1.3) + 4
        y0 += title_h + 14 + 2 + 26
    body = sl_node.one("body")
    blocks = [c for c in body.children if c.tag != "#text"] if body is not None else []
    kinds = [_kind(b) for b in blocks]
    gap = BODY_GAP
    n_gap = max(0, len(blocks) - 1)
    avail_bottom = SLIDE_H_PX - PAD_B - 10
    avail = avail_bottom - y0

    def measure(scale):
        SC = scale
        return [block_h(D, k, b, x0, w) for k, b in zip(kinds, blocks)]

    sid = sl_node.attrs.get("id") or ""
    geo = GEOM.get(sid)
    scale = 1.0
    if geo and len(geo.get("h", [])) == len(blocks):
        # 用浏览器实测的分配高度做版式基准：PPT 与 PDF 视觉一致
        SC = 1.0
        nat = measure(1.0)
        hs = []
        for i, k in enumerate(kinds):
            t = float(geo["h"][i])
            if k in ("tbl", "cards", "two", "steps"):
                hs.append(max(t, 24.0))          # 弹性块按实测高度（表格内部再等比压行）
            else:
                hs.append(max(t, nat[i]) if nat[i] > t + 4 else t)
        gaps = [float(g) for g in geo.get("g", [])]
        if gaps and len(gaps) == n_gap:
            gap = sum(gaps) / n_gap
        # 仍然超预算就从弹性块里收
        over = (sum(hs) + gap * n_gap) - avail
        if over > 2:
            flex = [i for i, k in enumerate(kinds) if k in ("tbl", "cards", "two", "steps") and hs[i] > 50]
            fsum = sum(hs[i] for i in flex)
            if flex and fsum > 0:
                f = max(0.75, (fsum - over) / fsum)
                for i in flex:
                    hs[i] *= f
            if (sum(hs) + gap * n_gap) > avail + 2:
                scale = max(0.85, (avail - gap * n_gap) / max(1.0, sum(hs)))
                hs = measure(scale)
    else:
        hs = measure(1.0)
    for _ in range(5):
        need = sum(hs) + gap * n_gap
        if need <= avail:
            break
        scale = max(0.72, scale * (avail - gap * n_gap) / max(1.0, sum(hs)))
        hs = measure(scale)
    # 有富余时，把空间让给表格/卡片（表格可以撑开）
    extra = avail - (sum(hs) + gap * n_gap)
    if extra > 6:
        FLEX = {"tbl": 3.0, "cards": 1.0, "two": 1.2, "steps": 1.2}
        caps = [hs[i] * (1.9 if kinds[i] == "tbl" else 1.22) if kinds[i] in FLEX else hs[i]
                for i in range(len(hs))]
        for _ in range(6):
            room = [max(0.0, caps[i] - hs[i]) for i in range(len(hs))]
            tot = sum(room)
            if tot < 3 or extra < 3:
                break
            give = min(extra, tot)
            for i in range(len(hs)):
                if room[i] > 0:
                    hs[i] += give * room[i] / tot
            extra -= give
    # ---- 绘制
    SC = scale
    sl = D.slide()
    if hd is not None:
        h2 = hd.one(tag="h2")
        s_, _ = clean_segs(segs(h2))
        D.text_box(sl, x0, PAD_T, w * 0.8, title_h, split_paras(s_), 44.0, NAVY, lh=1.3, bold=True)
        note = hd.one("hdnote")
        if note is not None:
            s2_, _ = clean_segs(segs(note))
            D.text_box(sl, x0 + w * 0.62, PAD_T + title_h - 30, w * 0.38, 34, split_paras(s2_), 18.0,
                       TX_GREY, lh=1.3, align=PP_ALIGN.RIGHT)
        D.rect(sl, x0, PAD_T + title_h + 14, w, 2, fill=NAVY)
    cur = y0
    for i, (k, b) in enumerate(zip(kinds, blocks)):
        hh = hs[i]
        if k == "tbl":
            render_table(D, sl, x0, cur, w, b, hh, dry=False, target_h=hh)
        elif k == "cards":
            render_cards(D, sl, b, x0, cur, w, min_h=hh)
        elif k == "two":
            render_two(D, sl, b, x0, cur, w, min_h=hh)
        elif k == "steps":
            render_steps(D, sl, b, x0, cur, w, min_h=hh)
        else:
            _static_h(D, sl, k, b, x0, w, dry=False, y=cur)
        cur += hh + gap
    foot = sl_node.one("brandfoot")
    if foot is not None:
        s_, _ = clean_segs(segs(foot))
        D.text_box(sl, x0, SLIDE_H_PX - PAD_B + 6, w * 0.7, 30, split_paras(s_), 17.0, FOOT, lh=1.3)
    pn = sl_node.one("pn")
    if pn is not None:
        s_, _ = clean_segs(segs(pn))
        num = s_[0][0] if s_ else "?"
        D.text_box(sl, x0 + w * 0.7, SLIDE_H_PX - PAD_B + 6, w * 0.3, 30, split_paras(s_), 17.0, FOOT,
                   lh=1.3, align=PP_ALIGN.RIGHT)
        if scale < 0.999 or cur > avail_bottom + 6:
            D.warn.append("p%s scale=%.2f overflow=%.0fpx" % (num, scale, max(0.0, cur - gap - avail_bottom)))
    return sl


def _static_h(D, sl, k, b, x0, w, dry=False, y=0):
    if k == "p":
        cls = "lead" if b.has("lead") else ("muted" if b.has("muted") else "")
        pt, lh, pad = (24.5, 1.8, 10) if cls == "lead" else ((19.0, 1.7, 6) if cls == "muted" else (22.0, 1.8, 8))
        color = NAVY if cls == "lead" else (TX_MUTED if cls == "muted" else TX_DARK)
        s_, _ = clean_segs(segs(b))
        paras = split_paras(s_)
        h = h_px(paras, w, S(pt), lh) + S(pad)
        if dry:
            return h
        D.text_box(sl, x0, y, w, h, paras, S(pt), color, lh=lh)
        return h
    if k == "note":
        s_, _ = clean_segs(segs(b))
        paras = split_paras(s_)
        inner = w - 44
        th = h_px(paras, inner, S(19.0), 1.72)
        h = th + S(34)
        if dry:
            return h
        D.rect(sl, x0, y, w, h, fill=NOTE_BG, line=NOTE_LN, lw=0.75, dash=MSO_LINE_DASH_STYLE.DASH)
        D.text_box(sl, x0 + 20, y + 16, inner, th + 4, paras, S(19.0), TX_NOTE, lh=1.72)
        return h
    if k == "quote":
        s_, _ = clean_segs(segs(b))
        paras = split_paras(s_)
        inner = w - 56
        th = h_px(paras, inner, S(23.0), 1.8)
        h = th + S(40)
        if dry:
            return h
        D.rect(sl, x0, y, w, h, fill=CREAM)
        D.rect(sl, x0, y, 4, h, fill=GOLD)
        D.text_box(sl, x0 + 28, y + 20, inner, th + 4, paras, S(23.0), NAVY, lh=1.8)
        return h
    if k == "numrow":
        if dry:
            return _measure_numrow(D, b, w)
        return render_numrow(D, sl, b, x0, y, w)
    if k == "databar":
        if dry:
            return _measure_databar(D, b, w)
        return render_databar(D, sl, b, x0, y, w)
    if k == "bigvs":
        if dry:
            return _measure_bigvs(D, b, w)
        return render_bigvs(D, sl, b, x0, y, w)
    return 0


def _measure_numrow(D, node, w):
    cells = node.direct("numcell")
    n = max(1, len(cells))
    cw = (w - 22.0 * (n - 1)) / n
    hs = []
    for c in cells:
        nnum, nlab = c.one("n"), c.one("l")
        s1, _ = clean_segs(segs(nnum))
        s2, _ = clean_segs(segs(nlab))
        hs.append(h_px(split_paras(s1), cw - 24, S(62.5), 1.1) + h_px(split_paras(s2), cw - 24, S(19.0), 1.6) + 22)
    return max(hs)


def _measure_databar(D, node, w):
    cells = node.direct(tag="div")
    n = max(1, len(cells))
    cw = w / n
    hs = []
    for c in cells:
        v, k = c.one("v"), c.one("k")
        s1, _ = clean_segs(segs(v))
        s2, _ = clean_segs(segs(k))
        hs.append(h_px(split_paras(s1), cw - 44, S(41.5), 1.1) + h_px(split_paras(s2), cw - 44, S(17.5), 1.5))
    return max(hs) + 44


def _measure_bigvs(D, node, w):
    kids = [c for c in node.children if c.tag != "#text"]
    hs = []
    for c in kids:
        if c.has("vs1"):
            s1, _ = clean_segs(segs(c.one("n")))
            s2, _ = clean_segs(segs(c.one("l")))
            hs.append(h_px(split_paras(s1), (w - 56) * 0.4, S(70.0), 1.0) +
                      h_px(split_paras(s2), (w - 56) * 0.4, S(19.5), 1.5) + 12)
    return max(hs or [100]) + 44


def dark_slide(D, sl_node):
    sl = D.slide()
    W, H = SLIDE_W_PX, SLIDE_H_PX
    D.rect(sl, 0, 0, W, H, fill=NAVY)
    sec_num = sl_node.one("sec-num")
    x0 = PAD_L
    if sec_num is not None:  # 章节页
        s_, _ = clean_segs(segs(sec_num))
        D.text_box(sl, x0, 150, 600, 170, split_paras(s_), 156.0, RGBColor(0x6E, 0x7E, 0x96), lh=1.0, bold=True)
        st = sl_node.one("sec-title")
        s_, _ = clean_segs(segs(st))
        D.text_box(sl, x0, 340, 1000, 100, split_paras(s_), 67.5, WHITE, lh=1.2, bold=True)
        sln = sl_node.one("sec-line")
        s_, _ = clean_segs(segs(sln))
        paras = split_paras(s_)
        D.text_box(sl, x0, 460, 1000, h_px(paras, 1000, 26.0, 1.7) + 6, paras, 26.0,
                   RGBColor(0xD5, 0xDD, 0xE6), lh=1.7)
        return sl
    # 封面 / 尾页
    kicker = sl_node.one("kicker")
    ct = sl_node.one("cover-title")
    rule = sl_node.one("cover-rule")
    cs = sl_node.one("cover-sub")
    tags = sl_node.one("cover-tags")
    # 计算堆叠总高
    items = []
    if kicker is not None:
        s_, _ = clean_segs(segs(kicker))
        items.append(("k", split_paras(s_), 19.5, GOLD_L, 1.4, 0))
    if ct is not None:
        st = ct.attrs.get("style") or ""
        m = re.search(r"font-size:\s*([\d.]+)px", st)
        pt = float(m.group(1)) if m else 78.0
        s_, _ = clean_segs(segs(ct))
        items.append(("t", split_paras(s_), pt, WHITE, 1.28, 0))
    items.append(("rule", None, 0, None, 0, 0))
    if cs is not None:
        st = cs.attrs.get("style") or ""
        m = re.search(r"font-size:\s*([\d.]+)px", st)
        pt = float(m.group(1)) if m else 28.5
        s_, _ = clean_segs(segs(cs))
        items.append(("s", split_paras(s_), pt, RGBColor(0xDC, 0xE2, 0xEA), 1.75, 0))
    if tags is not None:
        spans = tags.direct(tag="span")
        items.append(("tags", [split_paras(clean_segs(segs(sp))[0])[0] for sp in spans], 21.0,
                      RGBColor(0xF0, 0xF3, 0xF7), 1.4, 0))
    heights = []
    for kind, paras, pt, col, lh, _ in items:
        if kind == "rule":
            heights.append(54)
        elif kind == "tags":
            row = 0
            wsum = 0
            rows = 1
            for p in paras:
                tw = eff_len("".join(x[0] for x in p)) * 21.0 + 60
                if wsum + tw > W - 2 * PAD_L:
                    rows += 1
                    wsum = 0
                wsum += tw
            heights.append(rows * 62 + 30)
        else:
            heights.append(h_px(paras, W - 2 * PAD_L - 60, pt, lh) + 20)
    total = sum(heights)
    y = max(PAD_T + 20, (H - total) / 2 - 30)
    for (kind, paras, pt, col, lh, _), hh in zip(items, heights):
        if kind == "rule":
            D.rect(sl, x0, y + 26, 112, 4, fill=GOLD_L)
            y += hh
        elif kind == "tags":
            cx = x0
            for p in paras:
                tw = eff_len("".join(x[0] for x in p)) * 21.0 + 44
                if cx + tw > W - PAD_R:
                    cx = x0
                    y += 62
                D.rect(sl, cx, y, tw, 52, fill=None, line=RGBColor(0x8E, 0x9C, 0xB0), lw=0.75)
                D.text_box(sl, cx + 20, y + 12, tw - 40, 32, [p], 21.0, RGBColor(0xF0, 0xF3, 0xF7),
                           lh=1.4, anchor=MSO_ANCHOR.MIDDLE)
                cx += tw + 16
            y += hh
        else:
            D.text_box(sl, x0, y + 8, W - 2 * PAD_L - 60, hh, paras, pt, col, lh=lh,
                       bold=(kind == "t"))
            y += hh
    foot = sl_node.one("cover-foot")
    if foot is not None:
        s_, _ = clean_segs(segs(foot))
        paras = split_paras(s_)
        D.text_box(sl, x0, H - PAD_B - 6, W - 2 * PAD_L, 34, paras, 19.5,
                   RGBColor(0xB9, 0xC3, 0xD1), lh=1.5)
    return sl


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("pptx")
    ap.add_argument("--font", default="微软雅黑")
    ap.add_argument("--json", default=None)
    ap.add_argument("--geom", default=None, help="浏览器实测几何 json（deck 版式对齐用）")
    a = ap.parse_args()
    if a.geom:
        GEOM.update(json.load(open(a.geom, encoding="utf-8")))
    p = Parser()
    p.feed(open(a.html, encoding="utf-8").read())
    deck = [n for n in p.root.find_all(tag="div") if n.has("slide")]
    D = Deck(a.font)
    report = []
    for i, s in enumerate(deck, 1):
        if s.has("dark"):
            dark_slide(D, s)
            report.append({"page": i, "type": "dark"})
        else:
            content_slide(D, s)
            report.append({"page": i, "type": "content", "warn": D.warn[-2:] if D.warn else []})
    D.prs.save(a.pptx)
    print("slides=%d -> %s" % (len(deck), a.pptx))
    if D.warn:
        print("WARN:", "; ".join(D.warn))
    if a.json:
        json.dump(report, open(a.json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()