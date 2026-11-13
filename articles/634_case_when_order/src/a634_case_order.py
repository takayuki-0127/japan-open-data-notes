"""634 CASE WHEN の条件の並べ方で、何件が別の区分に入るのか

架空の顧客 2万人（直近1年の購入金額・回数、最後の購入からの日数、初めての購入からの日数）を、4つの条件で区分する。
  VIP：金額 10万円以上、常連：6回以上、新規：初めての購入から90日以内、休眠：最後の購入から180日超
CASE WHEN は上から順に見て、最初に当てはまった区分になる。条件が重なる顧客は、並べ方で区分が変わる。
4つの条件の並べ方 24通りすべてで区分ごとの人数を出し、重なりの数と、よく使う2つの並べ方の間で区分が変わる人数を数える。
SQL（DuckDB、1スレッド）で2つの並べ方と重なりを出し、Python と一致を確かめる。数字は置いた顧客の分布で決まる。
"""
import json
import itertools
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の顧客（作成者が乱数で作成、seed 634）"
rng = np.random.default_rng(634)
N = 20_000
tenure = rng.integers(1, 2000, N)                       # 初めての購入からの日数
rate = rng.gamma(0.8, 0.012, N)                         # 1日あたりの購入回数
active = np.minimum(tenure, 365)
orders = rng.poisson(rate * active) + (tenure <= 365)   # 直近1年の回数（新しい人は最初の1回を必ず含む）
dsl = np.where(orders > 0, np.minimum(rng.exponential(1 / np.maximum(rate, 1e-4)), tenure), np.minimum(tenure, 365 + rng.integers(1, 700, N)))
dsl = np.minimum(dsl, tenure).astype(int)
spend = (orders * rng.gamma(3, 4000, N)).round(-1).astype(int)
C = pd.DataFrame({"customer_id": np.arange(1, N + 1), "spend": spend, "orders": orders, "days_since_last": dsl, "days_since_first": tenure})
RULES = {"VIP": C.spend >= 100000, "常連": C.orders >= 6, "新規": C.days_since_first <= 90, "休眠": C.days_since_last > 180}
M = pd.DataFrame(RULES)
k = M.sum(1)


def assign(order):
    seg = pd.Series("その他", index=C.index)
    done = pd.Series(False, index=C.index)
    for r in order:
        hit = M[r] & ~done
        seg[hit] = r; done |= hit
    return seg


perm_rows = []
for order in itertools.permutations(RULES):
    s = assign(order).value_counts()
    perm_rows.append({"order": "→".join(order), **{r: int(s.get(r, 0)) for r in list(RULES) + ["その他"]}})
P = pd.DataFrame(perm_rows); P.to_csv(RES / "by_order_24.csv", index=False)
A = ["VIP", "常連", "新規", "休眠"]; B = ["休眠", "新規", "常連", "VIP"]
sa, sb = assign(A), assign(B)
moved = int((sa != sb).sum())
cross = pd.crosstab(sa, sb); cross.to_csv(RES / "crosstab_A_vs_B.csv")
pair = pd.DataFrame([[int((M[a] & M[b]).sum()) for b in RULES] for a in RULES], index=list(RULES), columns=list(RULES))
pair.to_csv(RES / "pair_overlap.csv")

# SQL
con = duckdb.connect(); con.execute("SET threads=1"); con.register("cust", C)
qs = [q.strip() for q in (SQL / "02_case_order_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
qa, qb, qk = [con.execute(q[q.index("SELECT"):]).df() for q in qs]
assert dict(zip(qa.seg, qa.n)) == sa.value_counts().to_dict()
assert dict(zip(qb.seg, qb.n)) == sb.value_counts().to_dict()
assert dict(zip(qk.k, qk.n)) == k.value_counts().to_dict()
rng_seg = {r: [int(P[r].min()), int(P[r].max())] for r in RULES}
out = {"customers": N, "rule_hits": {r: int(M[r].sum()) for r in RULES}, "n_rules_hit": {int(i): int(v) for i, v in k.value_counts().sort_index().items()},
       "multi_hit": int((k >= 2).sum()), "range_over_24_orders": rng_seg, "order_A": A, "order_B": B,
       "count_A": sa.value_counts().to_dict(), "count_B": sb.value_counts().to_dict(), "moved_A_vs_B": moved,
       "pair_overlap": pair.to_dict()}
json.dump(out, open(RES / "a634_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"segment": list(RULES), "hits": [int(M[r].sum()) for r in RULES], "min_24": [rng_seg[r][0] for r in RULES], "max_24": [rng_seg[r][1] for r in RULES],
              "order_A": [int((sa == r).sum()) for r in RULES], "order_B": [int((sb == r).sum()) for r in RULES]}).to_csv(RES / "summary.csv", index=False)

# 図1：24通りでの人数の幅
fig, ax = plt.subplots(figsize=(8.5, 4))
rs = list(RULES)
for i, r in enumerate(rs):
    lo, hi = rng_seg[r]
    ax.plot([lo, hi], [i, i], color=GRAY, lw=6, solid_capstyle="butt")
    ax.scatter([int((sa == r).sum())], [i], color=BLUE, zorder=3, s=40, label="並べ方A（VIP→常連→新規→休眠）" if i == 0 else None)
    ax.scatter([int((sb == r).sum())], [i], color=ORANGE, zorder=3, s=40, marker="s", label="並べ方B（休眠→新規→常連→VIP）" if i == 0 else None)
    ax.text(hi, i + 0.22, f"{lo:,}〜{hi:,}人", ha="right", fontsize=8.5)
ax.set_yticks(range(4)); ax.set_yticklabels(rs); ax.set_xlabel("区分の人数（灰の帯は24通りの並べ方での幅）")
ax.legend(frameon=False, fontsize=9, loc="lower right"); ax.set_title("同じ4つの条件でも、並べ方で区分の人数が変わる")
save(fig, "a634_range.png", SRC)

# 図2：重なり
fig, ax = plt.subplots(figsize=(6.5, 4.6))
im = ax.imshow(pair.to_numpy(), cmap="Blues")
for i in range(4):
    for j in range(4):
        v = pair.iloc[i, j]; ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=10, color="white" if v > pair.to_numpy().max() * 0.6 else INK)
ax.set_xticks(range(4)); ax.set_xticklabels(rs); ax.set_yticks(range(4)); ax.set_yticklabels(rs)
ax.set_title("2つの条件に同時に当てはまる人数（対角は1つの条件の人数）", fontsize=11)
save(fig, "a634_overlap.png", SRC)

# 図3：A→B の移り先
fig, ax = plt.subplots(figsize=(8.5, 4))
segs = rs + ["その他"]
bottom = np.zeros(len(segs)); cols = {"VIP": BLUE, "常連": GREEN, "新規": ORANGE, "休眠": GRAY, "その他": LIGHT}
for tb in segs:
    v = np.array([cross.loc[a, tb] if (a in cross.index and tb in cross.columns) else 0 for a in segs])
    ax.bar(segs, v, bottom=bottom, color=cols[tb], label=f"B では {tb}")
    bottom += v
ax.set_xlabel("並べ方A での区分"); ax.set_ylabel("人数"); ax.legend(frameon=False, fontsize=8.5, ncol=3)
ax.set_title(f"並べ方A の区分が、B ではどこに入るか（{moved:,}人が変わる）")
save(fig, "a634_moves.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int)[:3000])
