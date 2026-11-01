# lark-cli 域 scope 实测与验证命令（2026-08-28 定稿，app <YOUR_APP_ID>）

背景：Hermes 的飞书 bot app 只申请了部分 API scope。本表为逐域实测结果，用 **bot 身份**（`lark-cli` 默认 `--as bot`）验证。判断法：用假 token/URL 触发一次读请求，看错误类型（见 SKILL.md「Verifying Which API Scopes…」）。

## ✅ 已通（bot 身份端到端实测可用）
| 域 | 验证命令 | 返回 |
|---|---|---|
| base 多维表格 | `lark-cli base +base-get --base-token bascnNONEXIST123` | `NOTEXIST`(资源不存在) → 权限通 |
| sheets 表格 | `lark-cli sheets +workbook-create --title x --dry-run` | 过 scope（仅报缺 title） |
| docs Docx 读 | `lark-cli docs +fetch --doc https://open.feishu.cn/docx/doccnNONEXIST` | `Invalid document_id`(api) → 权限通 |
| im 列群 | `lark-cli im +chat-list` | 成功返回群列表（实测列到「播客选题小组」等 5 群） |
| **im 读群内消息** | `lark-cli im +chat-messages-list --chat-id <CHAT_ID> --limit 3` | **`ok:true` 读出消息，含 sender 中文名(<你的名字>)/时间/类型** — 用户已补 `im:message:read` scope |

## 🚫 用户明确不用（别再补权限 / 别再报为待办）
| 域 | 缺的 scope |
|---|---|
| im 跨群搜索 | `search:message` |
| drive 搜索 | `search:docs:read` |
| calendar 日历 | `calendar:calendar` `calendar:calendar:readonly` `calendar:calendar.event:read` |
| 审批 / 会议 / 邮件 | 用户说不需要 |

## ⚠️ 设计约束（非 bug）
- mail：bot 身份无法解析 `--mailbox me`，需显式邮箱地址。
- user 身份未登录（`auth status` → user=missing）。userScopes 里有一批 base/sheets 权限，但那是**用户授权 scope**，需 `lark-cli auth login` + `--as user` 才能用；**bot 身份用的是 app 自身申请的 tenant scope**。所以**别用 `lark-cli auth scopes` 判断 bot 能力**——它显示的是 userScopes；要看 bot 真实权限，直接触发命令读报错最可靠。

## 待办提示（当要开新能力时）
- 用户在飞书控制台 `https://open.feishu.cn/app/<YOUR_APP_ID>` → 权限管理，搜索上表 scope 名勾选 → **创建版本并发布** → 重新启用应用 → 重新测。
- 发布后 app_secret 可能轮换，需同步 `hermes config set feishu.app_secret`。
- 本 app 当前可用的核心面就是：文档读写 + 多维表格 + 表格 + 列群 + 读群消息；im 发消息等写操作未单独实跑，用到时先 `--dry-run` 探授权。
