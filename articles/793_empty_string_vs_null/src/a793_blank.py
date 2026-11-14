"""793 空の文字と NULL を区別せずに数えると、未入力の件数はどれだけずれるのか

架空の顧客5,000人の「建物名」（書かない人も多い）。入ってきた経路で、未入力の形が違う。
  web（5割）：未入力は NULL　　import（3割）：未入力は空の文字 ''　　counter（2割）：未入力は半角か全角の空白
未入力の件数を「IS NULL」「NULL か ''」「空白を除いてから」で数え、COUNT(列) の入力率も出す。
さらに、同じ表を CSV に書き出して pandas の既定で読み直すと、どう数えられるかも見る。
DuckDB（1スレッド）と Python の一致を確かめる。
"""
import json, io
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の顧客表（作成者が乱数で作成、seed 793）"
rng = np.random.default_rng(793)
N = 5000
src = rng.choice(["web", "import", "counter"], N, p=[.5, .3, .2])
has = rng.random(N) < .55
names = np.array(["ハイツ", "コーポ", "マンション", "レジデンス", "荘"])
bld = []
for s, h in zip(src, has):
    if h:
        bld.append(f"{rng.choice(['さくら', 'みどり', 'あおば', 'ひかり'])}{rng.choice(names)}{rng.integers(1, 30)}")
    elif s == "web":
        bld.append(None)
    elif s == "import":
        bld.append("")
    else:
        bld.append(rng.choice([" ", "　", "  "]))
C = pd.DataFrame({"customer_id": np.arange(1, N + 1), "source": src, "building": pd.array(bld, dtype=object)})

con = duckdb.connect(); con.execute("SET threads=1"); con.register("customers", C)
q = "\n".join(l for l in (SQL / "02_blank_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
b = C.building
isnull = b.isna(); empty = isnull | (b == ""); trim = isnull | (b.fillna("").str.strip(" 　") == "")
P = pd.DataFrame({"source": src, "isnull": isnull, "empty": empty, "trim": trim, "cnt": b.notna()}).groupby("source").sum().reindex(Q.source)
assert (P["isnull"].values == Q.blank_isnull.values).all() and (P["empty"].values == Q.blank_empty.values).all()
assert (P["trim"].values == Q.blank_trim.values).all() and (P.cnt.values == Q.count_col.values).all()
assert int(trim.sum()) == int((~has).sum())
Q.to_csv(RES / "by_source.csv", index=False)

# CSV に書き出して pandas の既定で読み直す（'' は NaN になる、空白だけの値は残る）
DATA.mkdir(exist_ok=True); C.to_csv(DATA / "customers.csv", index=False)
R2 = pd.read_csv(DATA / "customers.csv")
csv_isnull = int(R2.building.isna().sum()); csv_space = int((R2.building.fillna("x").str.strip(" 　") == "").sum())

true_blank = int((~has).sum())
tot = Q[["n", "blank_isnull", "blank_empty", "blank_trim", "count_col"]].sum()
out = {"rows": N, "true_blank": true_blank, "true_blank_share": true_blank / N,
       "blank_isnull": int(tot.blank_isnull), "blank_empty": int(tot.blank_empty), "blank_trim": int(tot.blank_trim),
       "share_isnull": float(tot.blank_isnull / N), "share_empty": float(tot.blank_empty / N), "share_trim": float(tot.blank_trim / N),
       "fill_rate_count_col": float(tot.count_col / N), "true_fill_rate": float(has.mean()),
       "by_source": Q.set_index("source").to_dict(orient="index"),
       "csv_pandas_isnull": csv_isnull, "csv_pandas_space_only": csv_space,
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a793_main.json", "w"), ensure_ascii=False, indent=1, default=int)

# 図1：未入力の件数（3通り）
fig, ax = plt.subplots(figsize=(8.5, 4.4))
lab = ["IS NULL だけ", "NULL か ''", "空白を除いてから\n（本当の未入力）"]
vals = [tot.blank_isnull, tot.blank_empty, tot.blank_trim]
ax.bar(range(3), vals, color=[ORANGE, GRAY, BLUE])
for i, v in enumerate(vals): ax.text(i, v + 30, f"{int(v):,}件（{v/N:.0%}）", ha="center", fontsize=11)
ax.set_xticks(range(3)); ax.set_xticklabels(lab); ax.set_ylabel("「建物名」が未入力の件数"); ax.set_ylim(0, max(vals) * 1.15)
ax.set_title(f"IS NULL だけで数えると、未入力 {true_blank:,}件のうち {true_blank-int(tot.blank_isnull):,}件を見落とす")
save(fig, "a793_counts.png", SRC)

# 図2：経路ごとの未入力の形
fig, ax = plt.subplots(figsize=(8.5, 4.4)); x = np.arange(len(Q)); w = .25
for j, (c, col, l) in enumerate([("blank_isnull", ORANGE, "IS NULL"), ("blank_empty", GRAY, "NULL か ''"), ("blank_trim", BLUE, "空白も除く")]):
    ax.bar(x + (j - 1) * w, Q[c], w, color=col, label=l)
ax.set_xticks(x); ax.set_xticklabels({"counter": "窓口", "import": "取り込み", "web": "ウェブ"}.get(s, s) for s in Q.source)
ax.set_ylabel("未入力と数えた件数"); ax.legend(frameon=False)
ax.set_title("入ってきた経路で、未入力の形（NULL・''・空白）が違う")
save(fig, "a793_by_source.png", SRC)

# 図3：入力率（COUNT(列)）と、CSV を pandas で読み直したとき
fig, ax = plt.subplots(figsize=(8.5, 4.4))
lab = ["COUNT(列)÷件数\n（DB のまま）", "pandas で読み直し\n（notna の割合）", "本当の入力率"]
vals = [tot.count_col / N, (N - csv_isnull) / N, has.mean()]
ax.bar(range(3), np.array(vals) * 100, color=[ORANGE, GRAY, BLUE])
for i, v in enumerate(vals): ax.text(i, v * 100 + 1, f"{v:.0%}", ha="center", fontsize=11)
ax.set_xticks(range(3)); ax.set_xticklabels(lab); ax.set_ylabel("「建物名」の入力率（%）"); ax.set_ylim(0, 100)
ax.set_title("同じ表でも、DB と CSV 経由の pandas で入力率が変わる（'' は pandas では欠けた値になる）")
save(fig, "a793_fill_rate.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "by_source"}, ensure_ascii=False, indent=1, default=int)); print(Q)
