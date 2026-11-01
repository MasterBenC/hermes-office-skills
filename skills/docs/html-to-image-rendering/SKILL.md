---
name: html-to-image-rendering
description: Use when an HTML/CSS design must become a PNG.
author: MasterBenC
license: MIT
platforms: [linux, macos, windows]
---

# HTML → Image Rendering

Use for any design that must ship as a flat image: info cards, covers, table images rendered from
data, slide exports, preview thumbnails. Write it as HTML/CSS and render it locally. HTML gives
exact control over type size, spacing, alignment and color; Pillow hand-drawing is slower, and image
generation models invent content (extra subtitles, watermarks, wrong characters).

## Procedure

1. **Write the HTML first, standalone.** One file, inline CSS, fixed width. Do not rely on any
   ambient theme — the render has none. Set the ground color explicitly on the page/body.
2. **Render with the weasyprint chain** (no browser, no CDP, no headless Chrome):

   ```bash
   python3 scripts/html_card_to_png.py          # 用装了 Pillow 的解释器
   ```

   The script renders HTML → PDF (`@page` pins the size) → `pdftoppm` at 2x → PIL crops the
   trailing background. Copy `scripts/html_card_to_png.py` next to the HTML and edit the constants
   at the top (source, output, width/height, ground color, dpi, tail whitespace).

   **设计用了 grid 或别的现代 CSS？改用 headless chromium**（这个引擎的 grid 支持极薄，多栏会压成竖排）：

   ```bash
   S=~/snap/chromium/common          # 必须在 snap 看得见的路径里
   cp page.html $S/page.html
   /usr/bin/chromium-browser --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
     --force-device-scale-factor=2 --window-size=1500,1900 \
     --screenshot=$S/shot.png file://$S/page.html
   ```

   `headless=new` 只截视口：窗口高度给足，再用 PIL 把尾部背景裁掉（同一套裁剪）。页面靠 JS 生成 DOM 时也走这条。
3. **Run the visual self-check before delivering.** See the gate below.
4. **Deliver the PNG.** On a chat surface emit a `MEDIA:/abs/path.png` line so it renders inline;
   for a publishing pipeline, hand the path to whatever uploads it to the asset library.
5. **Slice anything tall before delivering it.** A whole-page preview (article, report, long doc)
   renders as one 10k–15k px image that is unreadable in a chat pane — split it into ~4000px
   segments (`scripts/slice_tall_png.py`) and send them in order. A single card is fine as-is;
   the rule kicks in past roughly three screens of height.

## The delivery gate (do not skip)

You cannot see the image you just rendered, and "the render exited 0" says nothing about whether it
looks right. Before handing it over, call `vision_analyze` on the PNG and ask concrete layout
questions, not "does this look good":

- Are the columns actually side by side, or has the flow collapsed to stacked?
- Does each list number/bullet sit on the same line as its text?
- Are CJK characters real glyphs, or tofu boxes / fallback serif?
- Is anything clipped at an edge, or overlapped by an absolutely-positioned element?
- Is the bottom crop tight, over-long, or cutting a line in half?
- If it reads as airy, gappy, or "machine-made": **count the repeated blocks first.** A per-block
  top margin that is right for five sections becomes N visible gaps when the document has thirteen;
  the fix is that per-block margin, not the body paragraph spacing. Squeezing paragraph margins
  below ~10px only crowds the text and leaves every gap in place.

A collapsed layout or a clipped line is a defect, not a cosmetic detail.

## Pitfalls

- **weasyprint does not shrink to content height.** The `@page` size is fixed, so give the page more
  height than you need and crop the trailing background rows with PIL afterwards (the script does
  this). Without the crop you ship a card with a large empty bottom band.
- **Run it with the venv interpreter that has weasyprint** (the path above); it is not in the system
  `python3`. A missing `pdftoppm` is a poppler install, not a code bug.
- **Crop by scanning upward for the first non-background row, sampling across the width** — a solid
  dark card has no distinguishing pixel in a center-only scan, which can crop into the content.
- **`-r 192` is roughly 2x.** For a reader that displays 750px wide, render 750px at 2x and ship the
  1500px file; 1x looks soft on retina screens.
- **Flex works; grid support is thinner.** Multi-column rows and `display:flex` "number + text on one
  line" align correctly in this engine. Do not reach for grid or exotic layout when flex says it.
- **Call weasyprint in-process instead of shelling out to a `weasyprint` binary.** The venv's console
  script is not reliably on `PATH`, so `subprocess.run(["weasyprint", ...])` dies while
  `import weasyprint; weasyprint.HTML(filename=in_path).write_pdf(out_path)` works in the very same
  interpreter. Go straight to the API inside the venv python.
- **For a variable-height document, pin the `@page` width and give it generous height, then crop the
  trailing background with PIL** — the engine does not shrink a page to its content either.
- **When a vision check is available, use it before shipping.** The render exiting 0 says nothing
  about rhythm, alignment, or CJK glyphs; run the gate questions above and treat a real defect
  (collapsed column, tofu boxes, clipped line) as blocking, not cosmetic.
- **snap 版 chromium 有私有 `/tmp` 和自己的 HOME。** 输入 `file:///tmp/x.html` 会静默渲染成 ERR_FILE_NOT_FOUND（照样「写出」一张 PNG），`--screenshot=/tmp/shot.png` 也落进沙箱、在真实文件系统上找不到：**输入和输出都放 snap 可见路径**（`~/snap/chromium/common/`）。判断渲染是否真发生看文件体积——空白页几十 KB，真页面几百 KB。
- **表格 PNG（`scripts/tbl2img.py`）要一个常驻的带 PIL 的解释器，且路径必须是稳定路径。** 两个坑叠在一起：系统 `python3` 没有 PIL；而 Hermes 自己托管的 venv 目录**带每次会话都变的 hash**（`~/.hermes/installs/<hash>/environments/<hash>/venv/bin/python3`），写死在命令里迟早 `exit 127`。正确做法是建一次常驻 venv 并一直复用它——先 `ls -d ~/.hermes/tools/*venv` 看有没有现成的（本机是 `~/.hermes/tools/imgvenv`，已有 pillow），没有就建：`~/.hermes/bin/uv venv ~/.hermes/tools/imgvenv && UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple ~/.hermes/bin/uv pip install --python ~/.hermes/tools/imgvenv/bin/python pillow`。之后固定：`~/.hermes/tools/imgvenv/bin/python ~/.hermes/scripts/tbl2img.py data.json out.png --fs 15 --title "…"`。装包挂国内直连 PyPI 会卡死几分钟，走清华源 6 秒；venv 放 `~/.hermes/tools/` 而不是 scratch，scratch 会被 24h 清理。
- **截图前确认这次渲染真读到了文件**，别把上一轮的成功输出当本次证据：路径一换（尤其 `/tmp`）就可能是另一张图。

## Card design conventions

- **Name the card for the author's role in making it.** A card that distills a source document is
  the author's own reading note — call it a reading note, not a "summary" or "abstract", which reads
  as second-hand material. The card is physical evidence of the act of reading.
- **Borrow the source's visual language.** If the material came from a page or report, reuse that
  palette (ground, accent, tag colors) so the card reads as a product of the same research.
- **Carry its own compliance line** when the subject touches regulated financial products or foreign
  venues: one short line saying it is a personal note and not investment advice.
- **One idea per visual block.** Numbered blocks with a one-line heading and two or three lines of
  body text beat a dense paragraph; this is a card, not a document.

## Support files

- `scripts/html_card_to_png.py` — the render chain, parameterized at the top of the file.
- `scripts/slice_tall_png.py` — trims the trailing band and cuts a tall render into ~4000px
  segments for a chat surface.
