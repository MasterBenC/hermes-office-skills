---
name: deck-html-to-pptx
description: "Use when an HTML deck (1440x810) must become an editable .pptx."
version: 1.0.0
author: Hermes Agent (MasterBenC)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pptx, powerpoint, deck, html, slides, editable, 汇报, 幻灯片]
    category: office
    related_skills: [microsoft-office, html-to-image-rendering]
---

# HTML 汇报稿 → 可编辑 PPTX

把「AI 生成的自制 HTML 横版汇报稿」（1440×810 px，`@page size` 固定版式）转成**文字可选中、表格可编辑**的 16:9 `.pptx`。
不是把页面截图塞进幻灯片 —— 截图 PPT 到了客户手里没法改，这是这个脚本存在的唯一理由。

## 什么时候用

- 已经有一份排好版的 HTML deck（例如 AI 直接产出的汇报稿），但交付对象要 `.pptx`。
- 客户/领导必须能在 PowerPoint 里改字、改数字、改表格。
- 需要保留 HTML 那份设计（深色封面、卡片、数据条、步骤条），又要原生 PPT 元素。

不要用：本来就是图片型设计稿（那种只能出图，见 `html-to-image-rendering`）。

## 跑法

```bash
pip install python-pptx            # 唯一硬依赖
python3 scripts/deck_html_to_pptx.py deck.html out.pptx
python3 scripts/deck_html_to_pptx.py deck.html out.pptx --font "微软雅黑" --json report.json
```

- `--font`：目标机器上要有的字体，默认 `微软雅黑`（Windows 交付用它；macOS 换 `PingFang SC`）。
- `--json`：输出逐页几何/字号报告，用来核对有没有元素溢出。
- `--geom`：喂浏览器实测几何 json，版式对不齐时用。

字号换算固定为 **HTML px × 2/3 = pt**（1440 px 宽 → 13.333 in = 960 pt）。所以 HTML 里按 px 想的版式，进 PPT 后字号是同一套比例，不用二次调。

## 支持的 class（写 HTML 时照着用）

| 组 | class |
|---|---|
| 封面/章节/尾页 | `dark` `kicker` `cover-title` `cover-sub` `cover-rule` `cover-tags` `cover-foot` `sec-num` `sec-title` `sec-line` |
| 正文骨架 | `hd` `h2` `hdnote` `body` `brandfoot` `pn` `lead` `muted` `note` `quote` |
| 布局块 | `cards` `card` `ctag` `two` `col` `steps` `step` `sh` `sb` `sd` |
| 表格 | `tbl` `tr` `tr.head` `tr.hi` `th` `td` `td.em` `c1`–`c4` `cA` `cB` `cC` |
| 数据可视化 | `numrow` `numcell` `n` `l` `databar` `v` `k` `bigvs` `vs1` `vsdiv` |

`databar`（`v` 值 / `k` 上限）在 PPT 里被还原成真实矩形条，不是图片。

## 坑

- **字体缺失不会报错，只会静默换字体**：交付前在目标机器上确认 `--font` 指定的字体存在，否则整份 PPT 的换行位置会变。
- **一页塞不下时脚本不会自动缩字**：要么改 HTML，要么手动调整；先跑 `--json` 看溢出。
- **中英混排的数字/单位容易断行**：在 HTML 里用 `white-space:nowrap` 包住关键数字，转出来的 PPT 也保持整块。
- PPT 的表格是 `graphicFrame`，行高由内容决定 —— 合并单元格别指望和 HTML 完全一致，先做一页样板确认再批量。
