# 多维表格字段写入与回读校验

写记录前先 `GET /open-apis/bitable/v1/apps/{app}/tables/{tbl}/fields?page_size=100`，拿到每个字段的 `type` 与 `property`。下表是实测过的写值形状。

## 写入矩阵

| 字段 | type | 写入值 | 回读值 | 坑 |
|---|---|---|---|---|
| 文本 | 1 | `"字"` | `[{"text":"字","type":"text"}]` | — |
| 数字 | 2 | `123` | `123` | 别传字符串 |
| 单选 | 3 | `"已认领"`（选项名） | `"已认领"` | 先读 `property.options[].name`；发明不存在的选项会报错或自动建新选项 |
| 多选 | 4 | `["A","B"]` | `["A","B"]` | 同上 |
| 日期 | 5 | `1700000000000`（毫秒） | 同 | 秒级时间戳会变成 1970 |
| 复选框 | 7 | `true` / `false` | 同 | — |
| 人员 | 11 | `[{"id":"ou_xxx"}]` | `[{id, name, en_name, email}]` | 只给 `name` → `1254066 UserFieldConvFail`；显示的 name 是通讯录昵称，改不了 |
| 超链接 | 15 | `{"link":"https://...","text":"显示字"}` | 同结构 | — |
| 附件 | 17 | `[{"file_token":"..."}]` | 带 url 的对象 | 上传要 `drive:file` 权限 |
| 关联 | 18 | `[{"record_ids":[...]}]` | 数组 | 跨表才能用 |

## 批量写

```python
POST /open-apis/bitable/v1/apps/{app}/tables/{tbl}/records/batch_update
{"records":[{"record_id":"rec...","fields":{"负责人":[{"id":"ou_..."}],"认领状态":"已认领"}}]}
```

一次最多 500 条；单条失败会整批返回 `code != 0`，别只看 HTTP 200。

## 回读校验（关键）

**不要用「取 text」的通用工具校人员/单选字段** —— 它们没有 `text` 键，会被读成空串，看上去像写失败了（本 skill 踩过：10 条明明写进去，回读全空，险些二次重写）。

```python
def val(f, name):
    v = f.get(name)
    if isinstance(v, list):
        # 人员 / 附件 / 多选 / 文本分段
        return [x.get('name') or x.get('text') or x.get('file_token') if isinstance(x, dict) else x for x in v]
    return v
```

最稳的做法：校验时把目标记录的 `fields` 原样 `json.dumps` 打一遍，肉眼确认，再统计全表分布（如 `Counter(状态)`）。

## 人员字段的显示名

人员字段只存账号 id，单元格文字由通讯录决定。客户/同事希望显示「Ben」「张三（外聘）」这类自定义标签时：

1. 首选问一句：改账号昵称，还是加一列文本？
2. 别擅自加列 —— 表是多人共用的，多一列负责人会让人不知道该看哪个。
3. 交付时把「已写入的是账号 用户141145，不是 Ben」说清楚，别让用户打开表才发现。
