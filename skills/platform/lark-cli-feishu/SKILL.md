---
name: lark-cli-feishu
description: Use lark-cli to operate Feishu. Routes 28 lark-* skills.
version: 1.0.0
metadata:
  hermes:
    tags: [feishu, lark, cli, lark-cli, bot]
author: MasterBenC
license: MIT
platforms: [linux, macos, windows]
---

# lark-cli 飞书官方 CLI 操作入口

本机已安装 **lark-cli v1.0.91**（飞书/Lark 官方 CLI，Go 二进制），并已绑定到 Hermes（`lark-cli config bind --source hermes`），复用 Hermes 飞书应用 `<YOUR_APP_ID>`。

这是 **REST API 直连（feishu-integration skill）之外的第二条飞书通道**，能力更广、命令更成熟。涉及飞书操作用户想走 CLI 时用它。

## 先决：身份与安全（强制执行）

1. **当前身份 = bot（默认 `--as bot`，defaultAs = bot）**。bot 只能访问应用自己申请了 scope 的资源；`--as user` 才代表用户本人（需 user 已登录取证，当前用户身份 missing 未登录）。
2. **高风险写入必须用户确认**：命令 `--help` 标注 `high-risk-write` 的，遇到退出码 10（high-risk gate），停下→向用户展示 action/risk/关键参数→取得显式同意后，把 `hint` 指出的确认 flag 追加到原 argv 末尾重试。绝不静默加确认 flag 绕过。
3. **禁止输出密钥**：appSecret、accessToken 等不落终端明文。
4. **文件路径只接受相对路径**：`--file`/`--output`/`@file` 用 cwd 下相对路径；大 JSON 优先 stdin 传入。
5. **JSON 成功判断用 `ok == true` 或退出码 0**，不要用 `code == 0`（成功信封无顶层 code；code 只出现在错误信封 error 内）。
6. 命令输出 `verification_url`/`console_url`/授权 URL 时，必须用 `lark-cli auth qrcode` 生成二维码一并展示（PNG 优先），URL 原样转发不改写。

## 核心工作流：按需读取能力 skill，再执行

lark-cli 的 28 个能力定义**内嵌在 binary 里**，用 `lark-cli skills read <name>` 读取，**不要一次性全读**。流程：

1. 判断场景 → 选对应能力 skill 名（见下表）
2. 读该 skill：`lark-cli skills read lark-xxx`（首次进入该域时读一次；含子文件按 skill 内引用指引再读）
3. 看命令用法：`lark-cli <domain> --help` 或 `lark-cli <domain> +shortcut --help`（优先用 `+shortcut` 高级任务命令）
4. 执行。优先 `+shortcut`，其次 typed 命令，兜底 `lark-cli api METHOD /open-apis/...`

## 能力路由表（skill 名 → 场景）

| 场景 | skill | domain |
|---|---|---|
| 共享底座：认证/身份/安全/scope/退出码10/输出契约 | `lark-shared` | —（每次先想到它） |
| 发消息/回消息/群管理/搜索/上传下载图 | `lark-im` | im |
| 文档 Docx/Wiki 读取/创建/编辑 | `lark-doc` | docs, mindnotes |
| 云盘文件/上传下载/权限/评论 | `lark-drive` | drive |
| Drive 本地 Markdown 文件 | `lark-markdown` | markdown |
| 多维表格 base（表/字段/记录/视图/仪表盘/表单） | `lark-base` | base |
| 电子表格 sheets | `lark-sheets` | sheets |
| 幻灯片 PPT | `lark-slides` | slides |
| 日历/日程/空闲查询 | `lark-calendar` | calendar |
| 邮件 | `lark-mail` | mail |
| 任务 | `lark-task` | task |
| 通讯录/搜人 | `lark-contact` | contact |
| 知识库 wiki | `lark-wiki` | wiki |
| 审批 | `lark-approval` | approval |
| 会议/纪要/转写 | `lark-meeting` / `lark-minutes` / `lark-vc` | meeting, minutes, vc |
| 白板 | `lark-whiteboard` | whiteboard |
| 考勤 | `lark-attendance` | attendance |
| OKR | `lark-okr` | okr |
| 妙搭应用开发/部署 | `lark-apps` | apps |
| 实时事件订阅 WebSocket | `lark-event` | event |
| 探索底层 API | `lark-openapi-explorer` | api |

## 当前能力边界（截至 2026-08）

绑定的是 Hermes 现有 bot app，**只有部分域申请了 API scope**：

- ✅ **可用（bot 身份已授权，端到端实测通过）**：`base`（多维表格，含表/字段/记录/视图/仪表盘/表单）、`sheets`（电子表格）、`docs` 只读（`docx v1 .../raw_content` 能取全文纯文本，见下方「读飞书文档正文」）。实测 `base +base-get` 返回资源不存在而非权限报错，说明 base 权限打通。
- ⚠️ **未申请（调会报 `app_scope_not_applied` / missing_scopes）**：calendar、drive 搜索(search:docs:read)、mail、im(需确认) 等。
- 要解锁：用户在飞书开放平台控制台给 app `<YOUR_APP_ID>` 勾选对应 API 权限并重新发布。报错里的 `missing_scopes` 和 `console_url` 指向申请入口。

**兜底**：涉及飞书但 lark-cli 因 scope 不足失败时，退回 feishu-integration skill 的 REST API 直连方式（尤其多维表格）。

## 读飞书文档正文（wiki 链接 → 全文）

会话里的 `feishu_doc` 工具只在飞书评论上下文中可用，别的场合调用会直接报 `Feishu client not available (not in a Feishu comment context)` — 从聊天/定时任务里读文档，走这条命令链：

```bash
# 1) wiki 链接（.../wiki/<wiki_token>）→ 先拿 obj_token（真正的 docx token）
lark-cli api GET /open-apis/wiki/v2/spaces/get_node \
  --params '{"token":"<wiki_token>","obj_type":"wiki"}'
#    用返回的 node.obj_token / node.obj_type；链接里直接给的就是 docx token 则可跳过

# 2) 取全文纯文本
lark-cli api GET /open-apis/docx/v1/documents/<docx_token>/raw_content
#    → data.content 即整篇纯文本
```

坑：

- `raw_content` **只有正文纯文本**：标题、表格、列表都退化成一行行文字，没有层级。要抽待办就按关键词/编号正则抽，别指望结构。
- 长文别直接读进上下文：先落盘（输出重定向到文件），用 python 抽出 `data.content` 存成 `.txt` 再 `read_file` —— 顺便得到一份可反复比对的快照。
- `--params` 要一次传对 JSON（引号/逗号）；结构复杂时优先走 stdin。
- 文档 token 与 wiki token **不是一回事**：`raw_content` 只认 docx token，拿 wiki token 去调只会得到非预期结果。

## 读群成员 / 群消息 / 视图记录（bot 身份实测可用）

盘点「群里发的表、谁该认领」这类活，这三条命令就够，不用等通讯录权限：

```bash
# 群成员（拿 open_id + 显示名；返回 member_total 可核对人数）
lark-cli api GET /open-apis/im/v1/chats/<chat_id>/members \
  --params '{"member_id_type":"open_id","page_size":100}'
# 群消息倒序（参与讨论的 bot 和人的 open_id 都在 sender 里）
lark-cli api GET /open-apis/im/v1/messages \
  --params '{"container_id_type":"chat","container_id":"<chat_id>","page_size":50,"sort_type":"ByCreateTimeDesc"}'
# 多维表格按视图取记录（视图自带筛选/排序，别自己按字段名猜）
lark-cli api GET /open-apis/bitable/v1/apps/<app>/tables/<tbl>/records \
  --params '{"view_id":"<view_id>","page_size":500}'
```

- **人名映射走群成员接口，不要靠 `/open-apis/contact/v3/users/{open_id}`**（bot 身份报 `no user authority`）或 `search/v1/user`（报 `token_invalid`）：没授通讯录 scope 时这两条路都是死的，而群成员列表里就有 `name`。
- 消息里的 `sender.sender_type` 用来分人分机器人：先列出「谁能代表谁」（同一个 open_id 既是某人的账号又挂着自建机器人时极易认错），再去解读消息内容。**不要把表里的人员字段当成正在跟你说话的人。**
- 一次拉 50 条够看上下文；要全量就翻 `page_token`，别把整群历史全 dump 进上下文。

## 定时/脚本场景不要用它

`/usr/local/bin/lark-cli` 是指向 `/usr/local/lib/node_modules/@larksuite/cli/scripts/run.js` 的 node wrapper（真身同目录 `bin/lark-cli`），身份配置在 `~/.lark-cli/<workspace>/config.json`。也就是说它要 node 在 PATH 上 + 交互登录态的环境变量；**cron 那种最小环境里它会输出 `ok:false`/非 JSON**，脚本容易静默吞掉。

所以：定时任务（同步、巡检、报表）用 `feishu-integration` 的 REST 直连写法（stdlib urllib，解 `${FEISHU_APP_SECRET}` 占位符），并先过 `env -i /usr/bin/python3 脚本.py` 这一关再挂 crontab。手动/交互操作继续用 lark-cli。

## 验证命令速查

```bash
lark-cli auth status            # 看 identity/bot/user 状态
lark-cli auth scopes            # 看已申请 scope
lark-cli skills list            # 列出全部能力 skill
lark-cli skills read lark-base  # 读某能力 skill
lark-cli base --help            # 看 domain 命令
```
