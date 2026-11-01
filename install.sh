#!/usr/bin/env bash
# Hermes 办公技能包 · 一键安装（也可直接照抄进你自己的 agent 脚本）
# 用法:
#   bash install.sh                 # 自动判断 ~/.hermes/skills 或 ~/.claude/skills
#   bash install.sh /path/to/skills # 指定目标目录
#   bash install.sh /path/to/skills --force   # 覆盖同名 skill
set -euo pipefail

REPO_OWNER="MasterBenC"
REPO_NAME="hermes-office-skills"
BRANCH="main"

DEST="${1:-}"
FORCE="${2:-}"
if [ -z "$DEST" ]; then
  if [ -d "$HOME/.hermes" ]; then DEST="$HOME/.hermes/skills"
  elif [ -d "$HOME/.claude" ]; then DEST="$HOME/.claude/skills"
  else DEST="$HOME/agent-skills/hermes-office-skills"; fi
fi
mkdir -p "$DEST"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() {
  local url="$1"
  echo "→ 下载: $url"
  curl -fL --retry 3 --connect-timeout 15 -o "$TMP/pkg.tar.gz" "$url"
}

echo "目标目录: $DEST"
if ! fetch "https://codeload.github.com/$REPO_OWNER/$REPO_NAME/tar.gz/refs/heads/$BRANCH" 2>/dev/null \
 && ! fetch "https://gh-proxy.com/https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/$BRANCH.tar.gz" 2>/dev/null \
 && ! fetch "https://ghfast.top/https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/heads/$BRANCH.tar.gz" 2>/dev/null; then
  echo "!! 三个源都失败。试 SSH: git clone git@github.com:$REPO_OWNER/$REPO_NAME.git" >&2
  exit 1
fi

tar xzf "$TMP/pkg.tar.gz" -C "$TMP"
SRC="$TMP/$REPO_NAME-$BRANCH/skills"
[ -d "$SRC" ] || { echo "!! 包里没有 skills/ 目录" >&2; exit 1; }

ok=0; skip=0
for cat in "$SRC"/*/; do
  c=$(basename "$cat")
  for d in "$cat"*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    if [ -e "$DEST/$c/$name" ]; then
      if [ "$FORCE" = "--force" ]; then rm -rf "$DEST/$c/$name"; else echo "skip $c/$name"; skip=$((skip+1)); continue; fi
    fi
    mkdir -p "$DEST/$c"
    cp -r "$d" "$DEST/$c/$name"
    echo "ok   $c/$name"; ok=$((ok+1))
  done
done

echo
echo "完成：新增 $ok 个，跳过 $skip 个 → $DEST"
echo "提示：脚本依赖 python-docx / python-pptx / openpyxl / pymupdf / pillow，缺什么装什么。"
