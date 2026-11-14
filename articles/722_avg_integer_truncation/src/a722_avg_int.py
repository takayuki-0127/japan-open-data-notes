"""722 整数の列を SQL Server の AVG で平均すると、小数の切り捨てで店ごとの平均はどれだけずれるのか

架空の30店のレシート（各店 200〜400枚、計約9,000枚）。列は 1枚あたりの点数（整数、1〜12点）と会員フラグ（0/1）。
店ごとの「1枚あたりの点数」と「会員の割合」を、
  小数のまま平均（DuckDB の AVG、Python の平均）
  整数のまま平均（SQL Server の AVG(int) は結果も int で小数を切り捨てる、とされる。Python で再現）
で出し、ずれ・同じ値になった店・順位の入れ替わりを数える。
SQL Server の挙動はここでは試していない（未検証）。DuckDB の SQL では整数の割り算（//）で切り捨てを再現し、Python と一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の30店のレシート（作成者が乱数で作成、seed 722）"
rng = np.random.default_rng(722)
DATA.mkdir(exist_ok=True)
NS = 30
lam = rng.uniform(1.6, 3.8, NS)              # 店ごとの点数の平均（1を引く前）
mem = rng.uniform(0.25, 0.65, NS)            # 店ごとの会員の割合
rows = []
for s in range(NS):
    n = int(rng.integers(200, 401))
    items = np.clip(1 + rng.poisson(lam[s], n), 1, 12)
    flag = (rng.uniform(size=n) < mem[s]).astype(int)
    for k in range(n): rows.append((f"S{s+1:02d}", f"S{s+1:02d}-{k+1:04d}", int(items[k]), int(flag[k])))
Rc = pd.DataFrame(rows, columns=["store_id", "receipt_id", "items", "member_flag"])
Rc.to_csv(DATA / "receipts.csv", index=False)

g = Rc.groupby("store_id")
S = pd.DataFrame({"receipts": g.size(), "avg_items": g["items"].mean(), "member_rate": g.member_flag.mean()})
S["avg_items_truncated"] = (g["items"].sum() // g.size()).astype(int)       # 正の数なので切り捨て＝0への丸め
S["member_rate_truncated"] = (g.member_flag.sum() // g.size()).astype(int)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("r0", Rc); con.execute("CREATE TABLE receipts AS SELECT * FROM r0")
dq = con.execute((SQL / "02_avg_duckdb.sql").read_text(encoding="utf-8")).df().set_index("store_id")
for c in ["avg_items", "member_rate"]: assert np.allclose(dq[c], S.loc[dq.index, c]), c
for c in ["avg_items_truncated", "member_rate_truncated", "receipts"]: assert (dq[c].astype(int) == S.loc[dq.index, c]).all(), c

S["diff_items"] = S.avg_items - S.avg_items_truncated
S["rank_exact"] = S.avg_items.rank(ascending=False, method="min").astype(int)
S["rank_trunc"] = S.avg_items_truncated.rank(ascending=False, method="min").astype(int)
S.round(4).to_csv(RES / "by_store.csv")
tot_exact = Rc["items"].mean()
vc = S.avg_items_truncated.value_counts().sort_index()
# 切り捨てた平均×枚数で「点数の合計」を戻したとき
back = (S.avg_items_truncated * S.receipts).sum(); true_sum = Rc["items"].sum()

out = {"stores": NS, "receipts": len(Rc), "avg_items_overall": round(float(tot_exact), 3),
       "avg_items_range": [round(float(S.avg_items.min()), 2), round(float(S.avg_items.max()), 2)],
       "diff_items_mean": round(float(S.diff_items.mean()), 3), "diff_items_max": round(float(S.diff_items.max()), 3),
       "diff_items_mean_pct": round(float((S.diff_items / S.avg_items).mean() * 100), 1),
       "diff_items_max_pct": round(float((S.diff_items / S.avg_items).max() * 100), 1),
       "distinct_values_exact": int(S.avg_items.round(6).nunique()), "distinct_values_truncated": int(S.avg_items_truncated.nunique()),
       "truncated_value_counts": {str(k): int(v) for k, v in vc.items()},
       "spearman_exact_vs_trunc": round(float(stats.spearmanr(S.avg_items, S.avg_items_truncated).statistic), 3),
       "max_gap_same_truncated": round(float(S.groupby("avg_items_truncated").avg_items.agg(lambda v: v.max() - v.min()).max()), 3),
       "sum_back_from_truncated": int(back), "sum_true": int(true_sum), "sum_back_short_pct": round(float((1 - back / true_sum) * 100), 1),
       "member_rate_range": [round(float(S.member_rate.min()), 3), round(float(S.member_rate.max()), 3)],
       "member_rate_truncated_values": sorted(S.member_rate_truncated.unique().tolist()), "sql_matches_python": True}
json.dump(out, open(RES / "a722_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：店ごとの平均（小数）と切り捨て
o = S.sort_values("avg_items"); x = np.arange(NS)
fig, ax = plt.subplots(figsize=(10, 3.8))
ax.scatter(x, o.avg_items, color=BLUE, s=22, label="小数のまま（DuckDB の AVG）", zorder=3)
ax.scatter(x, o.avg_items_truncated, color=ORANGE, s=22, marker="s", label="整数の AVG（切り捨ての再現）", zorder=3)
for i in range(NS): ax.plot([i, i], [o.avg_items_truncated.iloc[i], o.avg_items.iloc[i]], color=GRAY, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(o.index, rotation=90, fontsize=7.5); ax.set_ylabel("1枚あたりの点数")
ax.legend(frameon=False, fontsize=9); ax.set_title(f"切り捨てで平均{out['diff_items_mean']:.2f}点、最大{out['diff_items_max']:.2f}点低く出る（店は小数の平均の順）")
save(fig, "a722_by_store.png", SRC)

# 図2：同じ値にまとまる
fig, ax = plt.subplots(figsize=(8, 3.6))
for v in vc.index:
    sub = S[S.avg_items_truncated == v]
    ax.scatter(sub.avg_items, np.full(len(sub), v) + rng.uniform(-0.12, 0.12, len(sub)), color=BLUE, s=20)
    ax.text(sub.avg_items.max() + 0.05, v, f"{len(sub)}店", va="center", fontsize=9)
ax.set_xlabel("小数のままの平均（点）"); ax.set_ylabel("整数の AVG の結果"); ax.set_yticks(vc.index)
ax.set_title(f"30店の平均は、切り捨てると{len(vc)}つの値にまとまる")
save(fig, "a722_groups.png", SRC)

# 図3：0/1 の列の平均
fig, ax = plt.subplots(figsize=(8, 3.6)); o2 = S.sort_values("member_rate")
ax.bar(np.arange(NS), o2.member_rate * 100, color=BLUE, label="小数のまま")
ax.scatter(np.arange(NS), o2.member_rate_truncated * 100, color=ORANGE, marker="s", s=18, zorder=3, label="整数の AVG（再現）")
ax.set_xticks(np.arange(NS)); ax.set_xticklabels(o2.index, rotation=90, fontsize=7.5); ax.set_ylabel("会員の割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("0/1 の列を整数のまま平均すると、どの店も0%になる")
save(fig, "a722_member_rate.png", SRC)
print(json.dumps(out, ensure_ascii=False))
