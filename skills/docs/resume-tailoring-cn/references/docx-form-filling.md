# 用 python-docx 填官方中文表格（报名表/登记表）

原则：**读原表 → 定位格 → 写字**。一格都不新增、不重排，只往里填字。
解释器：任意装了 `python-docx` 的 `python3`（没有就 `python3 -m venv .venv`）。

## 1. 先把表格结构打出来

```python
from docx import Document
d = Document("附件1_报名表.docx"); t = d.tables[0]

def uniq(row):                      # 关键：合并单元格会让 row.cells 重复
    seen, out = set(), []
    for c in row.cells:
        if id(c._tc) in seen: continue
        seen.add(id(c._tc)); out.append(c)
    return out

for i, row in enumerate(t.rows):
    print(i, [c.text.strip()[:14] for c in uniq(row)])
```

`row.cells` 对横向合并的格子会**重复返回同一个 `_tc`**，直接按 `cells[k]` 取会越取越偏。
一律先 `uniq()`；之后"第几个格子"才和表头列顺序对得上。

## 2. 按标签定位，不要写死行号

填表几乎必然要插行（经历段数不够用），**插一行后面所有索引齐平移**。所以定位一律走标签：

```python
def find_row(t, *labels):           # 同时含这些文字的行的行号
def after_label(row, label):        # 该行里 label 右边那一格
```

需要两个同名表头时（"家庭主要成员"和"其他近亲属"都有一排 `姓名/与本人关系/…`）取后者用 `[-1]`，
不要用 `[0]`。

## 3. 插行 = deepcopy 一行再 addnext

```python
from copy import deepcopy

def insert_after(t, idx, n=1):
    anchor = t.rows[idx]._tr
    for _ in range(n):
        new = deepcopy(anchor); anchor.addnext(new); anchor = new
```

deepcopy 出来带着上边框/底纹/行高，比 `table.add_row()` 可靠（后者丢格式、落到表尾）。
复制完把内容清空：每个 `w:tc` 只留第一个 `w:p`，并删掉该段里除 `w:pPr` 以外的子节点。

## 4. 写字：一个格子一个 run，显式设中文字体

```python
from docx.shared import Pt
from docx.oxml.ns import qn

r = p.add_run(text)
r.font.name = "仿宋"                                    # 西文名
r._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "仿宋")   # 中文名：不设就回退宋体
r.font.size = Pt(9)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER                  # 短字段居中，长叙事段用 JUSTIFY
```

先删段落里已有的 run（`r._element.getparent().remove(r._element)`）再写，否则旧字残留、
两段文字叠在一个格子里看不出来。

## 5. 页数回退：空单元格的默认字号在撑行高

插完行常常从 2 页涨到 3 页，第 3 页只有签字行——**不是内容多了，是空单元格**。
原表里空格子还挂着 Calibri 13pt 的空 run，每行按 13pt 算高度；填了字的格子反而是 9pt。

```python
# ① 所有 run 字号压到 ≤10pt；② 纯空段落塞一个 9pt 空 run
for row in t.rows:
    for c in row.cells:
        for p in c.paragraphs:
            if not p.runs:
                r = p.add_run(""); r.font.size = Pt(9)
                r._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "仿宋")
            for r in p.runs:
                if r.font.size and r.font.size > Pt(10): r.font.size = Pt(10)
# ③ 行高改成 atLeast 0，交给内容决定
from docx.oxml import OxmlElement
trPr = row._tr.get_or_add_trPr()
trH = OxmlElement("w:trHeight"); trH.set(qn("w:val"), "0"); trH.set(qn("w:hRule"), "atLeast"); trPr.append(trH)
```

做完这一轮掉一页是常态。还要省行就删"奖励情况""处分情况"这类表单里给多行、实际只填"无"的**空白备用行**
（给 2 行改 1 行、给 3 行改 1 行，不影响填报）。

## 6. 验收：文本层 + 像素层两遍

```bash
soffice --headless --convert-to pdf --outdir . 表.docx
pdfinfo 表.pdf | grep Pages                       # 页数回归
pdftotext -f 1 -l 1 -layout 表.pdf - | sed -n '1,8p'   # 字填对没、表头行有没有被折行
pdftoppm -r 100 -png 表.pdf pg                    # 再上 vision_analyze 看布局
```

- `pdftotext -layout` 能抓到 vision 经常漏读的字（"投资管理部"这种被挤在长串中间的词）。
- 表头那行"应聘公司、部门、岗位：… 填表时间：…"最容易折行把"日"甩到第二行——缩到 10pt、
  间隔空格减到 3–4 个；核验方法是 `pdftotext` 看它是否只剩一行。
- vision 报"某栏目缺失"时先用 `pdftotext` 全文搜一遍，跨页的栏目它常常看不到。
- 每次改完都重转 PDF：docx 本身看不出翻页。

## 7. 性别/年龄字段的写法

- 简历与登记表里年龄写出生年月（如 `YYYY.MM`），不写具体岁数。
- 出生日期、身份证号、民族、政治面貌、婚姻状况、籍贯这几项只有用户能提供，缺一律 `〔待填〕`＋黄色高亮。
