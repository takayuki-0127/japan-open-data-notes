"""02_整形：ブラウザで集めた JSON（f73_watcher.json.gz）から
- コメント1件1行の表（data/_comments.parquet、全文を含むので GitHub には置かない）
- DI の表（data/raw/di_watcher.csv：原数値と季節調整値、現状・先行き）
を作る。同じ月が2回入っている場合（ページの重複）は、後に読んだ方を捨てる。
"""
import gzip, json
import pandas as pd
from common import WATCHER_JSON, COMMENTS, RAW, DATA, MARK

d = json.load(gzip.open(WATCHER_JSON, "rt", encoding="utf-8"))
cols = ["ym", "kind", "region", "field", "mark", "industry", "reason", "text"]
c = pd.DataFrame(d["rows"], columns=cols)
# 先行き（saki）は「判断の理由」の欄に文章が入り、追加説明の欄は空。現状（gen）は理由の欄が「来客数の動き」などの分類
c.loc[c.kind == "saki", "text"] = c.loc[c.kind == "saki", "reason"]
c.loc[c.kind == "saki", "reason"] = ""
c["field3"] = c.field.str.extract(r"^(家計動向|企業動向|雇用)")[0]
c["score_mark"] = c.mark.map(MARK)
# 調査月ごとに、同じ (kind, 地域) の並びが2回出てくる重複を除く
before = len(c)
c = c.drop_duplicates(subset=cols).reset_index(drop=True)
c["text"] = c.text.str.replace(r"^[・\s]+", "", regex=True).str.replace(r"\s+", "", regex=True)
c = c[c.text.str.len() > 0].reset_index(drop=True)
c["id"] = range(len(c))
c.to_parquet(COMMENTS)

di = d["di"]
def frame(rows, name, cols):
    f = pd.DataFrame(rows, columns=["ym"] + cols)
    return f.set_index("ym").add_prefix(name + "_")
raw_cols = ["n", "v5", "v4", "v3", "v2", "v1", "di"]
out = (frame(di["raw_gen"], "raw_gen", raw_cols)
       .join(frame(di["raw_saki"], "raw_saki", raw_cols), how="outer")
       .join(frame(di["sa_gen"], "sa_gen", ["di", "kakei", "kigyo", "koyo"]), how="outer")
       .join(frame(di["sa_saki"], "sa_saki", ["di", "kakei", "kigyo", "koyo"]), how="outer"))
out.index.name = "ym"
out.to_csv(RAW / "di_watcher.csv")

# 月ごとのコメント数（GitHub に置く）
cnt = c.groupby(["ym", "kind"]).size().unstack()
cnt.to_csv(DATA / "comments_per_month.csv")
print("rows", before, "->", len(c), "months", c.ym.nunique(), c.ym.min(), c.ym.max())
print(c.groupby("kind").size())
print(c.mark.value_counts())
print(c.text.str.len().describe())
print(c.field3.value_counts(dropna=False))
