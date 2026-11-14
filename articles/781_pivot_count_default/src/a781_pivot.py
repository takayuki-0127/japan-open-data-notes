"""781 数の列に文字が1つまざると、Excel のピボットの集計はどう変わり、合計はどれだけ消えるのか

架空の売上表（10店×300行）。金額の列は、ほとんどが数だが、一部が「12,000」のような文字（別のシステムから貼り付けたもの）や「-」（売上なし）になっている。
Excel のピボットは、値の列に文字や空白が1つでもあると、既定の集計が「合計」ではなく「個数」になると言われている。
この動きと、「合計」に切り替えたときに文字の行が足されない動き（SUM は文字を無視する）を Python で再現する（Excel では未検証）。
店ごとに、ピボットに出る値・文字を無視した合計・数に直した合計を比べる。数に直す SQL は DuckDB（1スレッド）で動かし、Python と一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の売上表（作成者が乱数で作成、seed 781）"
rng = np.random.default_rng(781)
STORES = [f"店{c}" for c in "ABCDEFGHIJ"]
TEXT_RATE = dict(zip(STORES, [0, 0, 0, .01, .02, .05, .1, .2, .3, 0]))   # 文字になった金額の割合（店ごと）
rows = []
for s in STORES:
    v = (np.round(rng.lognormal(9, .6, 300), -1)).astype(int)
    txt = rng.random(300) < TEXT_RATE[s]
    dash = rng.random(300) < .01
    cell = [("-" if d else (f"{x:,}" if t else str(x))) for x, t, d in zip(v, txt, dash)]
    rows.append(pd.DataFrame({"store": s, "amount": cell, "true_amount": np.where(dash, 0, v)}))
D = pd.concat(rows, ignore_index=True)
DATA.mkdir(exist_ok=True); D[["store", "amount"]].to_csv(DATA / "sales.csv", index=False)


def as_number(x):        # Excel のセルで「数」として入っている値（文字は None）
    try: return int(x)
    except ValueError: return None


num = D.amount.map(as_number)
any_text = num.isna().any()
default_agg = "個数" if any_text else "合計"
P = D.assign(num=num).groupby("store", sort=False).agg(rows=("amount", "size"), count_shown=("amount", "size"),
                                                         sum_ignore_text=("num", lambda s: int(s.dropna().sum())),
                                                         true_sum=("true_amount", "sum"),
                                                         n_text=("num", lambda s: int(s.isna().sum()))).reset_index()
con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", D[["store", "amount"]])
q = "\n".join(l for l in (SQL / "02_clean_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df().set_index("store").reindex(P.store)
assert (Q.sum_cleaned.to_numpy() == P.true_sum.to_numpy()).all() and (Q.sum_numbers_only.to_numpy() == P.sum_ignore_text.to_numpy()).all()
P["missing_share"] = 1 - P.sum_ignore_text / P.true_sum
P.to_csv(RES / "by_store.csv", index=False)
out = {"rows": len(D), "text_cells": int(num.isna().sum()), "text_cells_share": float(num.isna().mean()),
       "default_aggregation": default_agg,
       "total_true": int(P.true_sum.sum()), "total_ignore_text": int(P.sum_ignore_text.sum()),
       "total_missing_share": float(1 - P.sum_ignore_text.sum() / P.true_sum.sum()),
       "missing_share_by_store": {s: round(float(m), 4) for s, m in zip(P.store, P.missing_share)},
       "max_missing_store": str(P.store[P.missing_share.idxmax()]), "max_missing_share": float(P.missing_share.max()),
       "rank_true": list(P.sort_values("true_sum", ascending=False).store), "rank_ignore_text": list(P.sort_values("sum_ignore_text", ascending=False).store),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a781_main.json", "w"), ensure_ascii=False, indent=1)

x = np.arange(len(P))
# 図1：ピボットに出る「個数」
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(x, P.count_shown, color=GRAY)
for xx, v in zip(x, P.count_shown): ax.text(xx, v + 5, f"{v}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(P.store); ax.set_ylabel("ピボットに出る値")
ax.set_title(f"文字が{out['text_cells']}セルまざると、既定の集計が「{default_agg}」になり、どの店も300と出る")
save(fig, "a781_count.png", SRC)
# 図2：文字を無視した合計
fig, ax = plt.subplots(figsize=(9, 4.6)); w = .38
ax.bar(x - w / 2, P.true_sum / 1e4, w, color=BLUE, label="数に直した合計（正しい）")
ax.bar(x + w / 2, P.sum_ignore_text / 1e4, w, color=ORANGE, label="「合計」に切り替えた値（文字は足されない）")
ax.set_xticks(x); ax.set_xticklabels(P.store); ax.set_ylabel("売上（万円）"); ax.legend(frameon=False, loc="lower left")
ax.set_title("「合計」に切り替えても、文字の行の金額は消えたまま")
save(fig, "a781_sum.png", SRC)
# 図3：消えた割合
fig, ax = plt.subplots(figsize=(9, 4.6))
b = ax.bar(x, P.missing_share * 100, color=ORANGE)
for bb, v, r in zip(b, P.missing_share * 100, P.store): ax.text(bb.get_x() + bb.get_width() / 2, v + .4, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(P.store); ax.set_ylabel("消えた売上の割合（%）")
ax.set_title("文字の多い店ほど売上が小さく見え、店の順位も入れ替わる")
save(fig, "a781_missing.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
