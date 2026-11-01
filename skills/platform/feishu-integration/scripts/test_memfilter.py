#!/usr/bin/env python3
# PATH NOTE: 这是某台机器上的实测脚本，下面两个绝对路径按自己的 Hermes 安装位置改。
"""Verify the Feishu send-layer filter for memory / self-improvement notices.

Checks 4 things, offline (no network, no real message sent):
  1. the helper functions survived (i.e. the patch is still in adapter.py)
  2. the gate is actually called inside send()
  3. the classifier's verdicts on the real notice shapes + control cases
  4. what the config switch currently reads

Usage:  python3 test_memfilter.py [path/to/adapter.py]
Exit:   0 all pass | 1 a case failed | 2 patch missing
"""
import importlib.util
import os
import re
import sys

ADAPTER = sys.argv[1] if len(sys.argv) > 1 else (
    "/usr/local/lib/hermes-agent/plugins/platforms/feishu/adapter.py"
)
SITE = "/usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages"
if os.path.isdir(SITE) and SITE not in sys.path:
    sys.path.insert(0, SITE)

src = open(ADAPTER, encoding="utf-8").read()
for sym in ("_is_memory_notice", "_MEM_NOTICE_PREFIX_RE",
            "_feishu_memory_notices_suppressed"):
    if sym not in src:
        print(f"MISSING {sym} -- patch lost (hermes update overwrote adapter.py?)")
        raise SystemExit(2)

# dataclass-style decorators need the module registered before exec_module
spec = importlib.util.spec_from_file_location("feishu_adapter_under_test", ADAPTER)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    fails += 0 if ok else 1
    print(f"{'PASS' if ok else 'FAIL'}  {name}  got={got} want={want}")


# 1. gate wired into send()
calls = len(re.findall(r"_is_memory_notice\(", src))
check("gate called from send()", calls >= 2, True)   # 1 = def, >=2 = def + call

# 2. classifier verdicts
blocked = [
    "💾 Memory updated",
    "💾 Self-improvement review — 3 notes",
    "🧠 Holographic — recalled 1 memory",
    "💾 记忆已更新",
    "🧠 记忆召回 3 条",
]
allowed = [
    "P13 待认领：在讨论意见里写想牵头还是参与",
    "报错：feishu send failed code 10014",
    "holographic 记忆库我查过了，共 15 条",          # control: prose mentioning it
    "💾 " + "x" * 600,                              # control: long block (>400 chars)
    "✅ 已生成 3 份成品",
    "",
]
for t in blocked:
    check(f"block {t[:34]!r}", mod._is_memory_notice(t), True)
for t in allowed:
    check(f"allow {t[:34]!r}", mod._is_memory_notice(t), False)

# 3. config switch read-through (informational)
try:
    print("suppressed_now =", mod._feishu_memory_notices_suppressed())
except Exception as exc:  # noqa: BLE001
    fails += 1
    print("FAIL  config switch read:", exc)

print("\nRESULT:", "ALL PASS" if fails == 0 else f"{fails} FAILED")
raise SystemExit(0 if fails == 0 else 1)
