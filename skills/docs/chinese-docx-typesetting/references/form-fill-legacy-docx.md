# 旧版 .doc 表格填写（应聘登记表／报名表／登记表）

## 0. 为什么不能直接改

`.doc` 是 OLE 二进制，python-docx 打不开。先转换：

```bash
soffice --headless --convert-to docx --outdir . "表.doc"
```

转换保留合并格、边框、页眉页脚；只要不增删列，版式不会走样，回写 `.doc` 也稳。

## 1. 定位：按底层 `<w:tc>`，不按 `row.cells`

`row.cells` 把合并单元格重复吐出来（纵合并的右侧「照片」列会在每一行重现），索引和真实 `<w:tc>` 序列不同步。

```python
from docx.oxml.ns import qn

def tcs(row):                       # 真实子元素序列
    return row._tr.findall(qn('w:tc'))

def tcell(table, ri, ci):
    return tcs(table.rows[ri])[ci]
```

填之前先 dump 一次带 gridSpan／vMerge 的结构，认清每个 tc 是「标签」还是「值」，以及右侧是不是照片框（vMerge=restart/continue）：

```python
for ri, row in enumerate(t.rows):
    out = []
    for tc in tcs(row):
        tcPr = tc.find(qn('w:tcPr')); span = vm = None
        if tcPr is not None:
            gs = tcPr.find(qn('w:gridSpan'))
            span = gs.get(qn('w:val')) if gs is not None else None
            v = tcPr.find(qn('w:vMerge'))
            vm = (v.get(qn('w:val')) or 'cont') if v is not None else None
        txt = "".join(n.text or "" for n in tc.iter(qn('w:t')))
        out.append(f"[span={span},vm={vm}]{txt[:40]!r}")
    print(ri, " | ".join(out))
```

同一个 `ri` 下的 tc 序号才是写值用的坐标（标签格与值格相邻，写错就是覆盖标签）。

## 2. 写值：保留原 run 的 rPr

表内文字多为 宋体 SimSun + `w:szCs=21`（五号）。新插的 run 不带 rPr 会掉回主题字体，在 Word 里和邻格不一致。

```python
import copy
from docx.oxml import OxmlElement

def set_para_text(p, text):
    runs = p.findall(qn('w:r'))
    rPr = next((r.find(qn('w:rPr')) for r in runs if r.find(qn('w:rPr')) is not None), None)
    for r in runs:
        p.remove(r)
    for hl in p.findall(qn('w:hyperlink')):
        p.remove(hl)
    if text:
        r = OxmlElement('w:r')
        if rPr is not None:
            r.append(copy.deepcopy(rPr))
        t = OxmlElement('w:t')
        t.set(qn('xml:space'), 'preserve')
        t.text = text
        r.append(t)
        p.append(r)
```

**一个格子常常有多个 `<w:p>`**：标签一行、选项一行，声明区甚至有 5～6 段。只改 `ps[0]` 会静默无效（选项行的勾选根本没动），dump 才发现。要么遍历全部段落，要么明确知道改第几段。吃了这条亏的症状：`●` 一个都没打上，表却「保存成功」了。

## 3. 勾选：○/〇 → ●

同一张表里可能混用 `○`(U+25CB) 和 `〇`(U+3007)，空格数还不一样。用正则，不要字面 replace：

```python
import re
txt = re.sub(r"〇\s*无", "●无", txt, count=1)   # 只勾第一个「无」，别把前面的「有」也一并勾上
```

一行里同时有「有」和「无」时（「有无犯罪记录？〇有 … 〇无」），用 `rfind` 定位末尾那个再改，或让正则只匹配目标词。

## 4. 加行

工作经历／教育经历行数不够时，复制最后一行（连同边框与列宽）插到它后面，再往新行的 tc 里写值：

```python
new_tr = copy.deepcopy(t.rows[21]._tr)
t.rows[21]._tr.addnext(new_tr)
```

不要让内容「压成一行」去迁就行数——HR 一眼看出格式被改过。

## 5. 自检与交付

1. dump 整表文本逐格核：标签还在吗、值落对位置吗、勾选生效吗。
2. `soffice --convert-to pdf` → `pdftoppm -r 110 -png` → 看图核对边框／合并格／换行／空白页。
3. 回写：`soffice --headless --convert-to doc:"MS Word 97" 填好的.docx`，`.doc` + `.docx` 一起交（`.doc` 是 HR 手里那份的格式）。
