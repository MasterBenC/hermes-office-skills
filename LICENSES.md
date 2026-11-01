# 来源与许可

本仓库分两类内容，许可各自独立。**转载/二改前请看这一页。**

## 一、自建 skill（MIT）

在真实中文办公交付中写出来的，作者 MasterBenC，许可 MIT —— 可商用、可改、可再分发，
保留本声明即可。

| 分类 | Skill |
|---|---|
| docs | `chinese-docx-typesetting` · `chinese-gongwen-docx` · `resume-tailoring-cn` · `html-to-image-rendering` |
| office | `deck-html-to-pptx` |
| platform | `feishu-integration` · `lark-cli-feishu` · `agently-mail` |
| media | `image-processing` |

其中 `html-to-image-rendering/scripts/tbl2img.py`、`deck-html-to-pptx/scripts/deck_html_to_pptx.py` 同属 MIT。

## 二、第三方 skill（原许可保留）

这些来自 Hermes Agent 生态与社区，**版权归原作者**，本仓库只做原样收集，未改许可。

| 分类 | Skill | 作者 | 许可 |
|---|---|---|---|
| office | `microsoft-office` | Nous Research | MIT |
| office | `ocr-and-documents` | Hermes Agent | MIT |
| office | `excalidraw` | Hermes Agent | MIT |
| office | `meeting-action-items` | Ben Barclay (benbarclay), Hermes Agent | MIT |
| office | `nano-pdf` | community | MIT |
| platform | `linear` | Hermes Agent | MIT |
| platform | `box` | Chris Kim (iskysun96), Hermes Agent | MIT |

MIT 全文见各 skill 目录下的 `LICENSE` 文件（如 `skills/office/microsoft-office/LICENSE`）。

## 三、使用注意

1. **不要把生产凭据写进 skill。** 仓库里的飞书 App ID、群 ID、公众号凭据等一律是占位符
   （`<YOUR_APP_ID>` / `<CHAT_ID>` / `<OPEN_ID>`），装好后按自己环境的真值替换，
   并且**替换在自己的私有副本里**，别回传到公开仓库。
2. **飞书 `app_secret` 会在重新发布后轮换。** 遇到 `10014 app unauthorized` 先换 secret，别急着查权限。
3. 第三方 skill 若上游已更新，以官方 Hermes 仓库版本为准；本包里的版本是收集时的快照。

---

整理：MasterBenC（公众号：拆解师Ben）
