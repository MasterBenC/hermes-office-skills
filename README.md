# Hermes 办公技能包 · Office Skills for AI Agents

一套**真跑过活的**中文办公技能（Skill），给 AI Agent 用。
不是提示词合集：每个 skill 都带可执行脚本、实测过的坑、和"什么时候别用"的判断。

- 共 **16 个 skill**，覆盖：中文 Word / 公文 / 简历、Excel·PPT·PDF、扫描件 OCR、HTML→PNG、HTML→可编辑 PPTX、
  会议纪要转行动项、飞书（Lark）接入、邮件、Linear、Box、图片处理。
- 来源：日常真实交付中长出来的，不是演示稿。
- 许可：自建部分 MIT；第三方（Nous Research 等）保留原许可，见 [LICENSES.md](LICENSES.md)。

---

## 一句话安装（把下面这段丢给你的 Agent）

```text
请阅读 https://raw.githubusercontent.com/MasterBenC/hermes-office-skills/main/AGENT_INSTALL.md
按里面的步骤把办公技能装进我的 skills 目录，装完列一份清单给我。
```

Agent 会自己下载、复制到正确的目录、验证并回报。不想让 Agent 自己判断，就直接看
[AGENT_INSTALL.md](AGENT_INSTALL.md) 里的一行命令。

---

## 装完你会多出这些能力

### 文档（docs/）

| Skill | 解决什么 |
|---|---|
| `chinese-docx-typesetting` | 中文 Word 的**分页工程**：一页塞不塞得下、打开会不会乱、改一句能不能一键重出。一份内容源出 N 个版本（简历/方案多方向）。 |
| `chinese-gongwen-docx` | 中文**公文**排版，按 GB/T 9704 的版式（页边距、字号、行距、成文日期位置）。 |
| `resume-tailoring-cn` | 中文简历按岗位定制：**带版式引擎**（`resume_gen.py`，固定行距保证"本机一页=Word 一页"）+ 事实底座模板 + 多方向 spec + 国企社招选岗 + 官方报名表填写。 |
| `html-to-image-rendering` | HTML/CSS 设计稿 → PNG。含表格转小字号 PNG（`tbl2img.py`）、长图切片、中文字体处理。 |

### 办公工具（office/）

| Skill | 解决什么 |
|---|---|
| `microsoft-office` | 离线读写 Word/PPT/Excel（python-docx / python-pptx / openpyxl），**不需要装 Office**。含模板套用、批注、修订、xlsx 重算。 |
| `deck-html-to-pptx` | HTML 汇报稿 → **可编辑**的 16:9 `.pptx`（文字可选中、表格可改，不是截图）。 |
| `ocr-and-documents` | PDF / 扫描件取文本：先诊断有没有文本层，再选 pymupdf 或 marker-pdf。 |
| `nano-pdf` | 在已有 PDF 上按自然语言指令改文字。 |
| `meeting-action-items` | 会议记录/转写 → 带出处的决议、责任人、待办工单。 |
| `excalidraw` | 生成手绘风架构图/流程图/时序图的 Excalidraw JSON。 |

### 平台接入（platform/）

| Skill | 解决什么 |
|---|---|
| `feishu-integration` | 飞书 Bitable / Docx / IM 的 REST 直连、鉴权、字段写入、10014 报错排障、扫码看图 H5。 |
| `lark-cli-feishu` | 用官方 `lark-cli` 操作飞书，路由到 28 个子技能；权限 scope 实测矩阵。 |
| `agently-mail` | 通过命令行收发邮件：发送、回复、转发、搜索、读信、下载附件。 |
| `linear` | Linear 的 issue / project / team 管理（GraphQL + curl）。 |
| `box` | Box 云盘的文件、分享、搜索、元数据。 |

### 图片（media/）

| Skill | 解决什么 |
|---|---|
| `image-processing` | 去背景、社媒尺寸裁切、压缩、格式转换。 |

---

## 这些 skill 共同遵守的几条规矩

1. **先诊断再动手**：PDF 先查文本层，Word 先查能不能一页塞下，图表先查字体有没有。别上来就装包。
2. **一页装不下是硬约束**：中文文档的美观度在"溢出"面前一文不值。所有排版 skill 都以分页实测为准。
3. **交付物要可改**：能给可编辑 `.pptx` 不给截图 PPT，能给 `.docx` 不给 PDF。客户要改字的时候见真章。
4. **坑写在 skill 里**：snap 版 chromium 的私有 `/tmp`、`app_secret` 会在重新发布后轮换、微软雅黑缺失会静默换字体……这些都是踩过才写的。

---

## 目录结构

```
skills/
├── docs/       中文文档生成与排版
├── office/     Office 文件、PDF、OCR、图表、HTML→PPTX
├── platform/   飞书 / 邮件 / Linear / Box
└── media/      图片处理
```

每个 skill 是一个目录：`SKILL.md`（判断与流程）+ `scripts/`（可跑）+ `references/`（深水区细节）+ `templates/`（可套用）。

## 适配哪些 Agent

- **Hermes Agent**：装进 `~/.hermes/skills/`，自动出现在技能索引里。
- **Claude Code**：装进 `~/.claude/skills/`（同一套 SKILL.md 约定）。
- **其他 Agent（Cursor / Codex / 自研）**：这套文件本质是 Markdown + Python 脚本，直接当知识库放着，
  让 Agent 按需读对应 `SKILL.md` 即可 —— 没有魔法，只有写清楚的判断和能跑的脚本。

## 许可

自建 skill：MIT，随便用、随便改。
第三方 skill 归原作者（Nous Research / Hermes Agent / 各作者），原许可保留，逐条见 [LICENSES.md](LICENSES.md)。

## 谁整理的

**MasterBenC（公众号：拆解师Ben）**。这套 skill 不是照着教程抄的，是在日常办公和内容交付里被真实需求反复打出来的那一版——留着的是跑通过的，删掉的是好看的。
