# 批量读取一个多维表格（分享链接 → 结构化数据）

用于：用户扔来一个 Bitable 分享链接，要求把里面几十~上千条记录整理成能用的素材（评审、盘点、清单、写作材料）。
方向与 SKILL.md 的「创建 Bitable」相反：这里读的是别人（甚至别的租户）已有的表。

## 0. 命名陷阱

CLI 的 base 域用 `--base-token`，**没有** `--app-token`（写错只会得到一句 `unknown flag`，白跑一轮）。

## 1. 取 base_token 与表名

分享链接形如 `https://<tenant>.feishu.cn/base/<base_token>?from=from_copylink`，`?` 前那一段就是 base_token。
租户域名与本 app 的租户可以不同，**不影响**——权限看 app scope + 文档分享设置。

```bash
lark-cli base +base-get --base-token <base_token>   # 返回表名、时区、revision，不需要额外 scope
```

## 2. 列结构与记录（老版 v1 端点，`bitable:app` 即可）

新 shortcut（`+table-list` 等）依赖 `base:table:read`，没申请会报 99991672；
**同一份数据走 legacy `bitable/v1` 就能读**。遇到 scope 报错先换端点，别下结论说没权限。

```bash
APP=<base_token>; TID=<table_id>
lark-cli api GET /open-apis/bitable/v1/apps/$APP/tables --params '{"page_size":100}'
lark-cli api GET /open-apis/bitable/v1/apps/$APP/tables/$TID/fields --params '{"page_size":100}'
lark-cli api GET /open-apis/bitable/v1/apps/$APP/tables/$TID/records --params '{"page_size":500}'
```

分页：`page_size` 上限 500，循环到 `has_more == false`，`page_token` 取自上一次响应。

```python
pt, recs = None, []
while True:
    p = {"page_size": 500}
    if pt: p["page_token"] = pt
    out = subprocess.run(["lark-cli","api","GET",f"/open-apis/bitable/v1/apps/{APP}/tables/{TID}/records",
                          "--params", json.dumps(p)], capture_output=True, text=True).stdout
    d = json.loads(out)["data"]
    recs += d["items"]
    if not d.get("has_more"): break
    pt = d.get("page_token")
```

**在 execute_code 里做聚合，不要把上千行原始 JSON 打进上下文**——只把统计量、缺失情况、少量样本打出来。

## 3. 字段值形态（按 type 分支，别当纯字符串处理）

| type | 值 |
|---|---|
| 1 文本 | 字符串 |
| 2 数字 / 5 日期 | 数字 / 毫秒时间戳 |
| 15 URL | `{"link": ..., "text": ...}`；**用户经常把整段标题或说明粘进来**，解析成 URL 前先看 `text` |
| 17 附件 | 数组：`file_token` / `name` / `size` / `type` / `url`（`url` 是 API 下载端点，需要一个 media-token 头或 drive scope） |
| 18 单向关联 / 21 双向 | 关联记录数组 |

统一用 `(f.get(K) or "")` / `(f.get(K) or {}).get("link","")` 取，别 `f[K]`。

## 4. 附件读不了时不要停在那里

`drive:file:readonly` 未开通 → 附件下载一律 99991672。这时候：

1. 先把**不需要附件**的那部分全做完（其它字段、外链、统计）。
2. 把「必须读附件才能拿到内容的条目」单独列成一张短名单（通常远远少于总数）。
3. 只针对这张短名单去要授权（开放平台勾选 `drive:file:readonly` 并发布版本，用户点一次）。

不要把「整表读附件」当默认路径——那是大量下载 + 解析，成本远高于真实需要。

## 5. 先做体检再写正文

这类表几乎都有脏数据，而且**体检结果往往就是用户最想先知道的东西**：

- 按业务键（仓库 URL / 手机号 / 编号）归一化后计数 → 「N 条记录只对应 M 个唯一对象」= 重复提交。
- 编号/命名格式分布（正则取前缀）→ 规范混乱程度。
- 每个关键字段的缺失数 → 哪些条目拿不到内容、需要别的来源。
- 外链可达性（`curl -o /dev/null -w '%{http_code}'` 并发测）→ 区分 200 / 403 私有 / 404 填错。

先报这些结论，再给完整数据文件；用户对「表本身有问题」的接受度远高于对「长表」的接受度。

## 6. 交付形态

- 明细给 **xlsx**（openpyxl 在 hermes venv 里有），一行一条，带重复标记列。
- 给用户看的速览用 PNG 表格，但**一张长图没人看**：tbl2img 渲 100 行 ≈ 2200×8000px。按 30~35 行切片多张。
- 交付前过滤平台模板文字：`No description available`、`以下是 Gitee 平台说明，您可以替换此简介`、裸 HTML（`<!DOCTYPE`）——这些不是内容。

外链那一侧怎么批量抓简介/README：见 `batch-repo-recon` skill。
