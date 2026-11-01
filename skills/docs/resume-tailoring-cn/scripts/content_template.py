#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简历事实底座模板 —— 复制这个文件，把你的真实事实填进去，删掉示例。

规矩（违反必翻车）：
  1. 事实（机构全称、时间、数字、职级）只在 FACTS 区写一次，方向 spec 不许重打。
  2. 方向 spec 只允许改：tagline / summary / skills_core / jobs 里 bullet 的措辞与顺序 /
     projects / education / certs 的取舍 / compact 与排版参数。
  3. 没确认的事实一律空着并列入待补清单，绝不编。

跑法：
  python3 content.py          # 出全部方向（每个方向一个 docx）
  python3 content.py 方向名    # 只出一个方向
"""
import os
import sys

from resume_gen import build          # 同目录的版式引擎

OUT = os.environ.get("RESUME_OUT", "out")


# ============================================================ FACTS（改这里）
NAME = "你的名字"
CONTACT = "男 · YYYY.MM · 1XX0000XXXX · you@example.com"

EDU = [
    dict(school="某某大学", degree="硕士 · 某某专业", period="2015.09 – 2018.06"),
    dict(school="某某大学", degree="学士 · 某某专业", period="2011.09 – 2015.06"),
]

# 倒序。key 唯一，方向 spec 里按 key 挑选用哪些段、哪些 bullet
JOBS = {
    "job_a": dict(
        org="某某公司（全称）",
        title="某某职务",
        period="2021.03 – 至今",
        bullets=[
            "**动词开头的第一条**：做了什么 + 对象 + 结果数字。",
            "第二条：结构与难度，别人做不了的那部分。",
        ],
    ),
    "job_b": dict(
        org="某某公司（全称）",
        title="某某职务",
        period="2018.07 – 2021.02",
        bullets=["一段一段倒序，每段 1–2 条 bullet 就够。"],
    ),
}


# ============================================================ 方向 spec（改这里）
SPECS = {
    # 方向名（也是输出文件名的一部分）
    "方向A": dict(
        # 定位句：<角色名>｜<方法A> × <方法B> × <方法C>，角色名用对方岗位的语言
        tagline="某某方向｜方法A × 方法B × 方法C",
        # 个人概述 3–4 行；**加粗**的部分会被渲染成强调色
        summary="X 年某某行业经验，**两个最硬的数字**，擅长某某方法论。"
                "服务对象与场景一句话说清。",
        # 核心能力 4–6 条，格式「能力名：具体手段」，要能被 ATS 抓
        skills_core=[
            "**能力名一**：具体手段，不要形容词。",
            "**能力名二**：具体手段。",
        ],
        jobs=["job_a", "job_b"],
        education=EDU,
        certs=[("某某资格", "某某证书（年份）"), ("语言", "英语 · 某某水平")],
        # 可选：代表项目（技术/AI 方向建议放在工作经历之前）
        # projects=[
        #     dict(name="项目名", role="你的角色", period="2025",
        #          bullets=["可公开披露的产出与结果。"]),
        # ],
        # projects_title="代表项目",
        # projects_first=True,
        # ---- 一页装不下时的旋钮（先收 sp，不要压 lh）----
        # compact=True,
        # lh=12.6,      # 固定行距（pt），10.5pt 正文用 12.6 稳
        # sp=0.75,      # 段间距系数
        # margins=(14, 14, 17, 17),
    ),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, spec in SPECS.items():
        if only and only != name:
            continue
        data = dict(spec)
        # 事实底座在这一刻注入，方向 spec 里不重复写
        data.setdefault("name", NAME)
        data.setdefault("contact", CONTACT)
        if "jobs" in data and data["jobs"] and isinstance(data["jobs"][0], str):
            data["jobs"] = [dict(JOBS[k]) for k in data["jobs"]]
        path = os.path.join(OUT, f"{NAME}_简历_{name}.docx")
        build(data, path)
        print("written:", path)


if __name__ == "__main__":
    main()
