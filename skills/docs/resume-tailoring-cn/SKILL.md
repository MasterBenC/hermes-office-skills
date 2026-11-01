---
name: resume-tailoring-cn
description: Use when tuning a 中文简历 to 招聘岗位，或要从招聘岗位表里选岗。多方向定制＋国企社招岗位筛选。
author: MasterBenC
license: MIT
platforms: [linux, macos, windows]
---

# 中文简历多方向定制

One person, N job directions, one shared fact base. Never write four separate documents by hand —
content drifts and every edit has to be repeated four times.
This skill also governs the step **before** writing: reading the 招聘岗位任职明细表 and deciding which
single 岗位 to apply for (see 岗位筛选与单岗决策 below).

## Architecture (proven)

**引擎和模板已经在 `scripts/` 里，不要重写。**

- `scripts/resume_gen.py` —— 版式引擎：A4、NAVY #1F3A5F、EA=微软雅黑、日期右对齐、
  `add_section(compact=)`、固定行距 `lh`（`w:lineRule=exact`）、`widow_control=False`。
- `scripts/content_template.py` —— 事实底座模板：FACTS 层（事实只写一次）+ SPECS 层（每个方向一个 dict），
  带注释，复制就能开工。

```bash
cp scripts/content_template.py content.py     # 与 resume_gen.py 放同一目录
# 填 FACTS 与 SPECS
python3 content.py           # 出全部方向
python3 content.py 方向A      # 只重建一个方向
```

依赖 `python-docx`；系统 python 没装就自己建 venv，别在别人的解释器上乱装。

Each direction dict: `tagline / summary / skills_core / jobs / education / certs` plus optional
`compact=True`, `projects`, `projects_title`, `projects_first`. Populate the fact base once and the
directions only re-frame it — same facts, different positioning line and bullet ordering.

新增方向：复制一个现有 dict 当起点，改完追加进 `SPECS`，然后**只重建这一个方向**——
`build(content.<方向>, path)`，没必要跑全量（全量一次要转 4–6 份 PDF）。

## Build + verify loop

```bash
cd resume_build && python3 content.py \
  && cd out && soffice --headless --convert-to pdf --outdir . *.docx \
  && for f in *.pdf; do echo "$f : $(pdfinfo "$f" | awk '/^Pages/{print $2}')页"; done \
  && for n in AI 不良资产 投融资 财富管理; do pdftoppm -r 100 -png "<你的名字>_简历_$n.pdf" "chk_$n"; done
```

Then measure bottom margin in code instead of eyeballing (usable height ≈ 284 mm):

```python
from PIL import Image; import numpy as np, glob
for f in sorted(glob.glob("chk_*.png")):
    a = np.array(Image.open(f).convert("L")); rows = np.where((a < 200).sum(axis=1) > 2)[0]
    print(f, "余量", round(284 - rows.max()/100*25.4, 1), "mm")
```

Add content only into measured slack. If a version flips to 2 pages: set `compact=True` on that
first (tightens section spacing), and only then start cutting text.

### 关键坑：本机看着一页，到用户 Word 里变两页（固定行距是唯一正解）

LibreOffice 把 微软雅黑 替换成 WenQuanYi Zen Hei，后者的行高度只有约 1.14em，而真正的
微软雅黑是 1.32–1.36em。同一份 docx 用「倍数行距」时，本机量出来 260mm、到 Word 里渲染成
~299mm，直接翻页——"本机一页"是假的。

修法（已内建在 resume_gen.py）：`lh=<pt>` 时段落改用**固定行距**`w:lineRule="exact"`，
行高不再由字体度量决定，Word 与 LibreOffice 的行位置逐毫米一致（实测差 0.0–0.3mm），
换字体（微软雅黑/Noto/WenQuanYi）出的高度也相同。再关掉孤行控制
（`pf.widow_control = False`），否则最后一段会被整段挤到第 2 页，还看不出原因。

配套旋钮：`lh` 固定行距（10.5pt 正文用 12.6pt 稳）、`sp` 段间距系数、`lf` 字号系数、
`margins` 四边 mm。字体度量一致的版面下，一页/两页可以一次网格扫描（lh × sp）定下来。

### 一页版：先扫参数，再核缓冲

**保持 `lh=12.6` 不动，优先收 `sp`**——行距是版面观感成本，段间距不是。扫一轮定下来：

```python
import os, sys, subprocess
sys.path.insert(0, "resume_build")   # 与 content.py 同目录
os.environ["RESUME_EA"] = "Noto Sans CJK SC"   # 必须在 import resume_gen 之前
import content
from resume_gen import build
S = "~/.hermes/cache/scratch/scan"
for sp in [0.75, 0.70, 0.65, 0.60]:
    for lh in [12.6, 12.4]:
        d = dict(content.<方向>); d["sp"], d["lh"] = sp, lh
        p = f"{S}/t_{sp}_{lh}.docx"; build(d, p)
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", S, p],
                       capture_output=True)
        info = subprocess.run(["pdfinfo", p.replace("docx", "pdf")],
                              capture_output=True, text=True).stdout
        print(sp, lh, [l for l in info.splitlines() if l.startswith("Pages")])
```

取**能出一页的最松那组**（先保住 12.6）。不要靠压 `lh` 凑页数。

**缓冲才算通过**：内容底距纸底 − 页边距 ≥ **5 mm**（约 1 行）。刚好装下（余量 1–2 mm）不算——
用户在 Word 里改一个词、改个日期就会翻到第 2 页。缓冲不够就删整行内容，不要压行距；删的次序：
只在该方向出现的 `certs` 行 → 与岗位无关的短经历只留公司名+时间 → 合并两条同类 bullet（合并后
通常省 1 行，因为换行比原来两条各自折行更省）。

参考体量（已验证一页、余量 12.7 mm）：`compact=True, projects_first=True, lh=12.6, sp=0.75,
margins=(14,14,17,17)` — 可装下 tagline + 6 行 summary + 5 条 skills_core + 2 个代表项目 +
4 段工作经历（含 1 段单条）+ 3 条教育 + 2 行资质。需再塞内容时先在这个基线上下扫 sp，不要动 lh。

### 出 PDF 的字体

PDF 交付物要嵌自己有的字体：`RESUME_EA="Noto Sans CJK SC"` 重建后再转 PDF（默认
WenQuanYi 字形偏旧，别拿它出正式 PDF）；送用户的 .docx 仍用 `微软雅黑`（他 Word 里才是对的）。
固定行距下两者页高相同，所以 PDF 与 Word 的版面一致。

## Environment

- Interpreter: 用**装了 python-docx + openpyxl 的那个**解释器（自己建 venv 最省事）。读招聘
  《岗位任职明细表》.xlsx 需要 openpyxl；Hermes 的 execute_code 沙箱不一定有，别硬走。
- `soffice`, `pdfinfo`, `pdftoppm` available; Noto CJK substitutes for 微软雅黑 — fine for previewing,
  but tell the user to re-export PDF from Word before sending it out.
- `vision_analyze` on the chk_*.png catches what pixel math can't: 方框乱码, bullets or dates wrapped
  onto the wrong line, 代表项目 blocks with empty bullet lists rendering as blank rows.

## Domain lessons

- Get the **official term** before writing industry vocabulary into the resume. Example: 信托业务三分类
  (银保监规〔2023〕1 号) names it **风险处置服务信托** under 资产服务信托, not "不良资产服务信托" — the
  colloquial name belongs in parentheses, the official one leads.
- 专业领域 lines with real 文号 (财税〔2009〕59 号, 财政部 税务总局公告 2023 年第 35 号 …) read as
  first-hand; a bare "熟悉税务筹划" reads as filler.
- **Only write what the user confirms.** Ask before adding any 文号/工具/业务线; when the user says "没做过
  以物抵债", it must disappear from every version, not just the summary.
- **以任职要求文本为准，不从公司名／行业标签推断考核项**：名字带"绿色"字样的平台，岗位要求里写的可能只是五条
  产业赛道、没有绿色专项；反过来名字中性的岗也可能暗考专才经验。逐条读要求，别读名字。
- 用户说"我这块经验比较少吧"时，先把岗位要求原文拆开逐条对照：每条到底考什么、他命中几条、缺的那条是不是
  真的在考核项里。弱项只能换成可辩护的措辞（"对 X 产业链保持研究跟踪"），并且**当场标明这是推断，给
  「删掉／补一条实据」二选一**——不要悄悄写进去，也不要用一句"不用担心"打发。
- Quantify with what the user gives (金额量级, 进入轮次, 角色). Never invent project names, counterparties,
  or scale — leave the space empty and ask instead.
- Watch for timeline contradictions in the source resume (overlapping education dates, a departure month
  that coincides with a company-wide event) and surface them as questions; recruiters will.
- Ask role, not labels: 收购方 vs 出让方, 受让方 vs 撮合方, 投资决策 vs 份额获取 — one word changes what the
  bullet may claim, and in finance it also changes the compliance story.
- 空泛的合作方表述（"熟悉各大 VC/PE"、"与众多机构保持良好关系"）在国资/机构面试里是负分，落成可被追问的
  实体形态："与多地政府产业引导基金及头部 VC/PE 建立直接合作渠道（GP 层面），主导份额争取与后续轮次资本对接"。
  机构名不可代编——让用户给分级口径（可公开披露／只说类别／说数量不说名字），给不了就先泛写并列入待补清单。
- **合规上别把自己写大**：申报类岗位会写明"无监管处罚、失信被执行、行业禁入"，国企背调查得细。资管、
  受托背景要措辞干净——写"份额争取/投资决策/撮合"这类角色词，别写"主导 N 个股权项目"；受托资产用"资产隔离、
  有序传承"收口，不要往控股上靠。

## 岗位筛选与单岗决策（国企／事业单位社招）

招聘方给的《岗位任职明细表》xlsx 是筛选依据，按硬门槛逐条点验，**不要按岗位名称猜匹配度**。
选岗权重：**不可控的资格闸（需求专业／证书／案例数）> 名额数量 > 赛道命中**。
资格闸不过就是零分，名额少只是概率低；两者冲突时买确定性，不要买名额——尤其当用户不肯去问 HR、
结果由形式审查单方面决定的时候。

- **名额**：招 5 人的岗与招 1 人的岗是两个难度。只招 1 人的**专才岗**（投后赋能、风控、法务合规）通常已有
  对口人选、社招走流程，别因为"描述看着像我"就主攻；招 1 人的**通用投资岗**只是录取率低，不是内定信号，可以投。
- **硬门槛逐条点验**：「至少成功主导 1 支新基金的发起设立」「主导落地 ≥5 个完整退出案例」「牵头 ≥1 个项目
  现场审计」「法律职业资格 A 证」这类是资格闸，不满足就是零，别用"经历相关"去顶。境外学历 ≠ 中国法考（法考是独立的资格闸）。
- **需求专业是最容易翻车的闸**：明细表写的「经管类、理工类、医学类」等门类是形式审查项，实务中通常按
  **最高学历专业**认定，不是"哪个学历能套上就算哪个"。硕士学位专业不在列时，先问 HR 能否按本科专业认定，
  再决定投哪个岗；自己认定"本科算数"就报，简历再好也是零。
- **两个学位分属两个门类时，找"双命中"岗**：本科与硕士分属两个门类时（如本科经管类＋硕士法学类）→ 优先投需求专业写成
  「经管类、理工类、法学类」的岗，两种审定口径都过，完全不依赖 HR 通融。用户不去问 HR 时，这是唯一安全的
  选法；只单边命中的岗要先解决口径问题再投。
- **按交集出简历**：挑要求高度重合的两个岗，用一份"交集版"覆盖——赛道只写两岗共同列出的方向，删掉只在
  一边出现的。HR 口径变了直接换岗投，一个字不用改。
- **只能投一个岗位时**：给**一个**明确推荐 + **一个**切换条件（"若 HR 回 X 则改投 Y"），并说明为什么。
  他要的是在截止日前下决心，列三个候选让他挑等于没帮。用户明确不去问 HR 时，切换条件失效——只给
  **单一答案 + 这笔选择的代价**（名额从 5 降到 1 之类），不要摆备选让他二次决策。
- 明细表里通常**没有报名截止时间和报名方式**。别只提醒他自己去核——用 `web_search` 搜「<单位> <年份> 社会招聘
  公告」，中公／粉笔／公务员招考站常整篇转载，能直接拿到：报名起止（精确到点）、报名邮箱、**是否限报一个岗位**、
  材料清单、是否需现场确认。截止前一天还在选岗的会话里，这个必须先查——否则简历做完才发现已经过期。
- 材料清单里的硬项提前点出来：留学背景的岗位审核几乎都要**教育部留学服务中心《境外学历学位认证书》**，
  申办要若干工作日，赶不上截止就是零。认证书不在手时，先把这个说在前面，再谈简历。
- **查招聘方体量再给建议**：搜集团／母公司的**债券跟踪评级报告**（上交所债券公告、评级机构 PDF），里面按子公司
  拆出管理基金数、实缴规模、营收与利润总额。体量小（几支基金、实缴几亿、年利润百万级）意味着岗位偏一线执行、
  薪酬低于市场化机构——这是他该知道但该由他自己定的信息，如实说一句，不劝退也不美化。

## 官方报名表 / 应聘登记表（附件1）填写

简历定稿后紧接着的一步。表是招聘方的，只能填不能改版式；填写手法与代码配方见
`references/docx-form-filling.md`（合并单元格去重、按标签定位行、插行、字号压制回页数）。

- **用官方原表填，不重做表格**。合并单元格、字号、页边距、页脚页码都是审核项的外观；重画一张
  "看起来一样"的表，打印或转 PDF 就错位。公告里常有直链（`curl -sL -o 附件1_报名表.docx "https://…/xxx.docx"`），
  下完 `md5sum` 跟用户附件比一次，确认同一份再动手。
- **跨表字段必须逐字一致**：参加工作时间 = 最早一段工作经历的起始月（不是"第一段专业对口的工作"）；
  公司全称、职务写法、学历起止月都照简历/上一份登记表抄。工龄和经历自相矛盾是国企背调最先抓的点。
- **不知道的字段绝不编**：写 `〔待填〕` 并 `run.font.highlight_color = WD_COLOR_INDEX.YELLOW`，交付时把这几项
  一次性列成清单（一行一项，方便他照填）。用户一次给齐后再统一替换、清掉高亮；分批追问会被嫌烦。
- 用户说"部门别写"就留空白格——合并单元格里的空值是合法的。别用公司名或条线去猜部门，背调第一句就问这个。
- **学历时间重叠不许改时间，改培养方式列**：2+2/转学/双学位写 `2+2（国内段）` / `2+2（美国段）`，其后的
  硕士写 `全日制`。同时在聊天里提醒他：审核细问时拿哪一句话解释。
- **简历里别写死"当前值"**：`男 · NN 岁` 过个生日就错，写 `男 · YYYY.MM`。年龄、司龄、"至今 N 年" 都会在
  投递窗口内失效，出生年月不会。
- 身份证号照抄，但过一遍校验位（权重 7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2 → mod 11 → `10X98765432`），
  对得上就顺口告诉他一句；对不上绝不自行改数字，只提醒他核。
- **家庭成员、签字、日期留空给他手写**。这三样代填等于伪造；把"需要你手写"单独点出来，别混在待补清单里。
- 交付三件套：可编辑 docx（打印手签用）＋ PDF 预览（手机上看）＋ 按命名规则打好的 zip
  （`<公司><部门><岗位><姓名>.zip`，内部文件 `00`–`07` 编号，缺号即待补）。邮件主题、收件邮箱、截止时间
  一行一条列清楚，不要写成段落。

## Delivery

Copy final artifacts to a flat folder and ship both .pdf and .docx via `MEDIA:`.
Ship the editable content source alongside (`_简历内容源文件.py`) so the next iteration is a one-line edit.

**两张交付物的留白纪律不同**：简历**不许**留占位符——待补项写在聊天回复里。报名表**可以**留
`〔待填〕`＋黄色高亮，因为它是给用户继续填的半成品，高亮本身就是"这里要你填"的提示；但交出去时
必须同时给出这份高亮的清单，并说清哪些是要他手写的（签字/日期/家庭成员）。

## 面试前：从简历到 90 秒自我介绍

用户丢来一份自己的简历说"下午有面试"，要的不是改写，是**能开口说的话**。次序：先查对方，再压内核，
最后写口语稿。

- **先查对方在公开场合怎么讲自己**（`web_search` 搜"<公司> <条线> 战略 2026"、"<公司> <业务品牌>"）。
  拿到三样就够用：这条线归谁管（条线负责人姓名与头衔）、对外的品牌打法（如"企业家办公室""人-家-企-社"）、
  历史上落地过什么同类业务。"为什么来"一段要挂在**对方自己的话**上，比夸公司有效十倍，且他知道你真做了功课。
- 简历→内核压成**四句**：一线体量（金额、创收、职务）、结构难度（别人做不了的复杂结构）、专业底色
  （证书／学历／原生专业能力）、现在的位置。四句之外都是追问素材。
- 自我介绍 **90 秒、250–300 字**，第一人称，句子 12–18 字。结构固定：一句定位 → 三层经历（底色／一线／跨境）
  → 一句收口主张。别写成简历朗读稿。
- **数字只说三个**（规模、创收、累计），其余留给追问——全报出来像堆砌。
- 禁空词："精通 X""深度参与""赋能"一律换成具体动作（"某某客户的美国税与 CRS 申报我一起处理过"）。
- 面试前必须准备的三个追问：为什么离开上一家（不吐槽老东家，讲两种工具解决两类问题）、
  为什么来这座城市／这家公司、薪资期望（**不报区间**："更看重平台和空间，具体可以谈"）。
- 结尾留一个**业务向反问**（条线与分公司怎么分工、总部给什么协同资源），比问晋升通道更像已经入职的人。
- 同一份简历面不同条线时，只换最后一段"为什么来"和一句技术侧补充，别重写全稿。

### 顺手要指出的简历硬伤（面谈前必修）

- **当前薪资／年薪区间不写进简历**：与国资、券商总部职级体系直接冲突，常在筛选阶段被判"来了留不住"。
- **别贴公众号／媒体原文长链**：显得像剪报，且链接会失效；改用一句行业地位（规模、排名、市占）。
- **第三人称推荐语搬运痕迹**（"其在某某公司……"）是硬伤，自己简历必须换成第一人称或无主语。
- 几百字内容排成 4 页＝材料汇编。投递件压到 2 页：公司体量压成一句，渠道罗列合成一行。
- 学历时间重叠写在**培养方式列**（2+2 国内段／美国段），不要靠备注解释。
- 案例栏不能空：一手主导的知名项目（客户／交易名可披露的）比任何形容词都值钱，缺了就追问要。
