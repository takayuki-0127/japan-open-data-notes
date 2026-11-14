"""782 表の1列だけを並べ替えると、何行の値が別の行とつながってしまうのか

架空の顧客表2,000人（顧客番号・会員ランク・前年の購入額・今年の購入額）。会員ランクは前年の購入額で決まり、今年の購入額は前年と相関する。
Excel で「今年の購入額」の列だけを選んで降順に並べ替えた（ほかの列は動かない）場合を Python で再現する（Excel では未検証）。
元の表の並びが「顧客番号の順」と「前年の購入額の順」の2通りで、別の顧客の値が入った行の数・ランク別の平均・前年との相関がどう変わるかを見る。
顧客番号での照合は DuckDB（1スレッド）で行い、Python と一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の顧客表（作成者が乱数で作成、seed 782）"
rng = np.random.default_rng(782)
N = 2000
prev = np.round(rng.lognormal(10, .7, N), -2).astype(int)
now = np.round(prev * np.exp(rng.normal(0, .35, N)), -2).astype(int)
rank = np.where(prev >= np.quantile(prev, .9), "ゴールド", np.where(prev >= np.quantile(prev, .6), "シルバー", "一般"))
O = pd.DataFrame({"customer_id": np.arange(1, N + 1), "rank": rank, "prev_amount": prev, "amount": now})
DATA.mkdir(exist_ok=True); O.to_csv(DATA / "customers.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("original", O)
q = "\n".join(l for l in (SQL / "02_check_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
RANKS = ["ゴールド", "シルバー", "一般"]


def one_col_sort(df):     # 「amount」の列だけを降順に並べ替える（ほかの列はそのまま）
    s = df.copy(); s["amount"] = np.sort(df.amount.to_numpy())[::-1]; return s


res = {}; tables = {}
for name, base in [("by_id", O), ("by_prev", O.sort_values("prev_amount", ascending=False, kind="stable").reset_index(drop=True))]:
    S = one_col_sort(base); tables[name] = S
    con.register("sorted_table", S); Q = con.execute(q).df().iloc[0]
    m = S.merge(O[["customer_id", "amount"]], on="customer_id", suffixes=("", "_true"))
    moved = int((m.amount != m.amount_true).sum())
    assert moved == int(Q.n_moved) and int(Q.total_gap) == 0 and int(Q.abs_gap) == int((m.amount - m.amount_true).abs().sum())
    res[name] = dict(moved=moved, moved_share=moved / N, mean_abs_gap=float((m.amount - m.amount_true).abs().mean()),
                     corr_prev=float(np.corrcoef(S.prev_amount, S.amount)[0, 1]), total_gap=int(Q.total_gap),
                     by_rank={r: float(S[S["rank"] == r].amount.mean()) for r in RANKS})
true_rank = {r: float(O[O["rank"] == r].amount.mean()) for r in RANKS}
R = pd.DataFrame([{"table": k, **{f"mean_{r}": v["by_rank"][r] for r in RANKS}, "moved": v["moved"], "corr_prev": v["corr_prev"]} for k, v in res.items()]
                 + [{"table": "true", **{f"mean_{r}": true_rank[r] for r in RANKS}, "moved": 0, "corr_prev": float(np.corrcoef(O.prev_amount, O.amount)[0, 1])}])
R.to_csv(RES / "summary.csv", index=False)
out = {"customers": N, "true_corr_prev": float(np.corrcoef(O.prev_amount, O.amount)[0, 1]), "true_by_rank": true_rank,
       **{f"{k}_{kk}": vv for k, v in res.items() for kk, vv in v.items() if kk != "by_rank"},
       "by_id_by_rank": res["by_id"]["by_rank"], "by_prev_by_rank": res["by_prev"]["by_rank"], "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a782_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ランク別の平均
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(3); w = .27
for j, (vals, l, c) in enumerate([(true_rank, "正しい", BLUE), (res["by_id"]["by_rank"], "1列だけ並べ替え（元は顧客番号の順）", ORANGE), (res["by_prev"]["by_rank"], "1列だけ並べ替え（元は前年の順）", GREEN)]):
    v = [vals[r] / 1e4 for r in RANKS]; b = ax.bar(x + (j - 1) * w, v, w, color=c, label=l)
    for bb, vv in zip(b, v): ax.text(bb.get_x() + w / 2, vv + .3, f"{vv:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(RANKS); ax.set_ylabel("今年の購入額の平均（万円）"); ax.legend(frameon=False)
ax.set_title("元が顧客番号の順だと、ランクの差がほぼ消える")
save(fig, "a782_by_rank.png", SRC)
# 図2：前年と今年の散布図
fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharex=True, sharey=True)
for ax, (df, t) in zip(axs, [(O, "正しい"), (tables["by_id"], "元は顧客番号の順"), (tables["by_prev"], "元は前年の順")]):
    ax.scatter(df.prev_amount / 1e4, df.amount / 1e4, s=3, color=GRAY)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_title(f"{t}（相関 {np.corrcoef(df.prev_amount, df.amount)[0, 1]:.2f}）", fontsize=10)
    ax.set_xlabel("前年の購入額（万円）")
axs[0].set_ylabel("今年の購入額（万円）")
fig.suptitle("元の並びが前年の順だと、ずれた表のほうが相関が強く見える", y=1.03)
save(fig, "a782_scatter.png", SRC, y=-0.05)
# 図3：ずれた行と合計
fig, ax = plt.subplots(figsize=(9, 4.6))
lab = ["元は顧客番号の順", "元は前年の順"]
v = [res["by_id"]["moved_share"] * 100, res["by_prev"]["moved_share"] * 100]
b = ax.bar(lab, v, color=[ORANGE, GREEN])
for bb, vv, k in zip(b, v, ["by_id", "by_prev"]):
    ax.text(bb.get_x() + bb.get_width() / 2, vv + 1.5, f"{vv:.0f}%（1行あたり平均{res[k]['mean_abs_gap'] / 1e4:.1f}万円ずれ）", ha="center", fontsize=9)
ax.set_ylabel("別の顧客の値が入った行（%）"); ax.set_ylim(0, 110)
ax.set_title("合計は変わらない（差0円）ので、合計で確かめても気づけない")
save(fig, "a782_moved.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
