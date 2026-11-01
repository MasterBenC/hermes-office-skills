# 给 Agent 的安装说明（照做即可）

你（Agent）现在要把这个仓库里的办公技能装到本机，然后向用户回报清单。
**不要问用户选哪个 skill**，全部装。装之前不要改仓库里的任何内容。

仓库：`MasterBenC/hermes-office-skills`
包内容：`skills/{docs,office,platform,media}/<skill-name>/SKILL.md` 等，共 16 个 skill。

---

## 第 0 步：确定目标目录

按你运行的环境选一个，**不要自己发明路径**：

| 你的运行环境 | 目标目录 |
|---|---|
| Hermes Agent | `~/.hermes/skills/` |
| Claude Code | `~/.claude/skills/` |
| 其他支持 SKILL.md 约定的 agent | 该项目约定的 skills 目录 |
| 不支持 skills 的 agent（Cursor / Codex / 自研） | `~/agent-skills/hermes-office-skills/`，当只读知识库挂着 |

判断方法：看 `~/.hermes/` 或 `~/.claude/` 是否存在；都存在就优先 `~/.hermes/`，并在回报里说明。

## 第 1 步：下载

```bash
TMP=$(mktemp -d)
curl -fL --retry 3 -o "$TMP/pkg.tar.gz" \
  https://codeload.github.com/MasterBenC/hermes-office-skills/tar.gz/refs/heads/main
tar xzf "$TMP/pkg.tar.gz" -C "$TMP"
SRC="$TMP/hermes-office-skills-main/skills"
ls "$SRC"        # 应看到 docs office platform media
```

GitHub 慢或连不上时的镜像（任选其一，把上面 URL 的 host 换掉）：

```bash
# 镜像 A
https://gh-proxy.com/https://github.com/MasterBenC/hermes-office-skills/archive/refs/heads/main.tar.gz
# 镜像 B
https://ghfast.top/https://github.com/MasterBenC/hermes-office-skills/archive/refs/heads/main.tar.gz
```

三个都失败就先 `git clone git@github.com:MasterBenC/hermes-office-skills.git`（SSH 443），再复制 `skills/`。
全失败就停手，告诉用户"下载不通"，并把报错原文贴出来 —— 不要凭记忆编造文件。

## 第 2 步：复制进 skills 目录

```bash
DEST=~/.hermes/skills          # ← 用第 0 步定下的目录
mkdir -p "$DEST"
for cat in docs office platform media; do
  mkdir -p "$DEST/$cat"
  for d in "$SRC/$cat"/*/; do
    name=$(basename "$d")
    if [ -e "$DEST/$cat/$name" ]; then
      echo "SKIP (已存在): $cat/$name"
    else
      cp -r "$d" "$DEST/$cat/$name"
      echo "OK: $cat/$name"
    fi
  done
done
```

**默认不覆盖**已有同名 skill。如果用户明确说"覆盖/更新"，才加 `rm -rf "$DEST/$cat/$name"` 再复制。
如果用户的目录是扁平结构（没有分类子目录，例如 `~/.claude/skills/<name>/`），把每个 skill 直接放到 `"$DEST/$name/"`，不要保留 `docs/office/...` 这一层。

## 第 3 步：装依赖（只在缺的时候装）

脚本用到这些 Python 包，**按需**安装，别一股脑升级：

```bash
python3 - <<'PY'
import importlib
need = {"docx":"python-docx","pptx":"python-pptx","openpyxl":"openpyxl",
        "fitz":"pymupdf","PIL":"pillow"}
missing=[p for m,p in need.items() if not importlib.util.find_spec(m)]
print("MISSING:", " ".join(missing) if missing else "none")
PY
```

有缺的再 `pip install <包名>`。系统 Python 有 PEP 668 限制时用 `python3 -m venv` 或 `pipx`，
**不要** `--break-system-packages` 把用户系统搞脏。

## 第 4 步：验证（必须做，不许跳过）

```bash
DEST=~/.hermes/skills
find "$DEST" -maxdepth 3 -name SKILL.md -newermt '-10 minutes' | wc -l   # 应为 16 个
head -3 "$DEST/docs/chinese-docx-typesetting/SKILL.md"                   # 能读出 name/description
python3 "$DEST/office/deck-html-to-pptx/scripts/deck_html_to_pptx.py" --help 2>&1 | head -3
```

16 个对不上、`--help` 报 ImportError 都要在回报里如实说，不要粉饰。

## 第 5 步：回报给用户

只回报这四项，别写安装日志流水账：

1. 装到哪个目录、成功几个 / 跳过几个（列被跳过的名字）
2. 缺哪些依赖、装了没有
3. 抽验结果（`--help` 通不通）
4. 一句话：这些 skill 覆盖"中文 Word/公文/简历 · Office·PDF·OCR · HTML→PPTX·PNG · 会议纪要 · 飞书/邮件/Linear/Box · 图片处理"

---

## 之后怎么用

不需要记命令。需要用的时候说人话即可，Agent 会自己匹配到 skill：

- 「把这份 Markdown 排成能直接发出去的中文 Word，一页装得下」
- 「把这些会议记录整理成决议 + 责任人 + 待办」
- 「这份 HTML 汇报稿转成客户能自己改字的 PPT」
- 「扫描件 PDF 里的表格提出来，做成 Excel」
- 「飞书多维表格里加一批记录，字段按这个 JSON 填」
- 「这张图去掉背景，出 3:4 和 1:1 两个版本」

skill 的价值在判断，不在命令：什么时候别用 OCR、什么时候该出可编辑文件而不是截图、
什么情况下"一页装不下"只能改内容 —— 这些都写在各自的 `SKILL.md` 里，用之前先读。
