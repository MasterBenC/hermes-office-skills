---
name: chinese-gongwen-docx
description: Use when writing Chinese 公文 docx. GB/T 9704 layout.
author: MasterBenC
license: MIT
platforms: [linux, macos, windows]
---

# 中文公文体 docx 生成

用 python-docx 直接写 OOXML 生成符合 GB/T 9704-2012 的公文（汇报/报告/请示/函），不要用内置 Title/Heading 样式（它们带主题字体，且非公文字号）。完整构建脚本见 `scripts/build_gongwen.py`。

## 版式参数（照抄）

| 元素 | 字体(东亚) | 字号 | half-points |
|---|---|---|---|
| 大标题 | 方正小标宋简体 | 二号 22pt | 44 |
| 正文 | 仿宋_GB2312 | 三号 16pt | 32 |
| 一级标题(一、) | 黑体 | 三号 16pt | 32 |
| 批注/说明 | 楷体_GB2312 | 四号 14pt | 28 |
| 表格内正文 | 仿宋_GB2312 | 五号 10.5pt | 21 |

- 西文一律 `w:ascii="Times New Roman"`，同时设 `w:rFonts w:eastAsia`，缺一不可。
- 正文段落：`<w:spacing w:line="560" w:lineRule="exact"/>`（固定值28磅）+ `<w:ind w:firstLineChars="200" w:firstLine="640"/>`（首行缩进2字符；用 firstLineChars，只写 firstLine 会在字体/字号变化时错位）。
- 页边距：上3.7 下3.5 左2.8 右2.6 cm。
- 标题不加首行缩进；**标题必须手动断行**（`run.add_break(WD_BREAK.LINE)`），二号字一行只放 ≈20 字，靠自动换行会把词切断。回行按梯形/菱形，每行词意完整。
- 署名右对齐 `w:rightChars="200"`；成文日期独立一段、右对齐 `w:rightChars="400"`（机关名右空2字、日期右空4字，日期视觉上在机关名下达居中）。
- 页码：宋体四号，数字两侧一字线 `— 1 —`。需在 `word/settings.xml` 加 `<w:evenAndOddHeaders/>`，`section.footer`=单页右空一字、`section.even_page_footer`=双页左空一字；页码用 `<w:fldSimple w:instr=" PAGE "/>`。
- 主送机关（"省某某厅某某处："）顶格，不缩进。

## 必做的校验流程

1. 本地 soffice 需要 **libreoffice-writer**。很多机器只装了 core/draw/impress，此时任何 docx 都报 `source file could not be loaded`——先 `dpkg -l | grep libreoffice` 确认并 `apt-get install -y libreoffice-writer`。
2. `soffice -env:UserInstallation=file:///tmp/lopX --headless --norestore --convert-to pdf --outdir <dir> <file>`（每次换 profile 目录，避免锁冲突）。
3. `pdfinfo` 看页数；`pdftoppm -r 100 -png` 转图后用 vision_analyze 检查断行、缩进、页码左右位置、表格是否溢页。
4. Linux 没有仿宋/黑体/小标宋，渲染会用 Noto 代替——字形不同但 CJK 全角宽度一致，所以**断行和页数判断仍然有效**，交付给用户时字体在 Word 里正常。非 Windows 环境的替代字体提：华文中宋（代小标宋）、宋体。

## 版面容量（决定要不要删字）

三号仿宋 + 28磅固定行距 + 标准页边距：**每页 ≈ 22 行 × 27 字 ≈ 600 字**。标题（2行大字，按字号折算约1.9行）、每个独立段落的末行残字、落款前间距都要折算。短文稿常溢出到第2页只带3行；要么压到 600 字内，要么接受2页，但**绝不能出现「末页只有落款」**（孤页会被退件）。段数越多越费行——把并列的「一是/二是」合成一段可省 1–2 行。

## 行文要点（内容层面比版式更容易翻车）

- 文种：「汇报」「申请」都不是公文文种。对上级用**报告/请示**；对不相隶属单位用**函**（商请协助→「关于商请协助开展……的函」）。
- 人名、部门、日期必须具体。「有关领导」「近日」会被退件，也让对方无法转办。
- 向上要资源时，**必须给出我方候选方向+理由请对方圈定**，不能写「恳请结合掌握的资源予以指导」把选择推回去。
- 请求批准的事项**分条列项**（一是/二是/三是各占一行），便于圈批；末尾必须留**我方联系人+电话**，否则受理部门无法回话。
- 主动写风险隔离句（如「本次属于工作交流，尚未形成具体试点、合作或费用安排」）能显著降低对方政治顾虑。
- 加一句「如可行可形成可复制的模式、向其他细分行业推广」——机关领导愿推一件事，往往因为它能成为其工作成果。
- 附件（需求表/议程初稿）挂上，批复率明显提高。
- 落款必须是主体全称，不能写「项目团队」（无名无章无法归档办理）。
- 涉军、军民融合类表述在正式行文中先加边界句：「仅面向民用及可公开的产业配套领域，不涉及涉密和出口管制事项」。
