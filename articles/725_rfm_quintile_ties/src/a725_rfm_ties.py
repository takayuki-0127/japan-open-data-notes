"""725 購入回数で顧客を5等分すると、同じ回数の人が別の段に分かれるのはどれだけか

架空の会員5,000人の1年間の購入回数（1回だけの人が多い、幾何分布に近い形）と最終購入日。
購入回数で5段（1が上位）に分ける3通り：
  NTILE(5)：人数で5等分。同じ回数の人は、並べるときの2つ目の順（顧客番号）で分かれる
  NTILE(5)（2つ目の順を最終購入日に変える）
  順位で段を決める：RANK（同じ回数は同じ順位）×5÷人数 で段にする。同じ回数の人は必ず同じ段
同じ回数なのに別の段に入った人、段ごとの人数、2つ目の順を変えたときに段が変わった人を数える。
DuckDB の SQL と Python の結果が一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の会員5,000人の購入回数（作成者が乱数で作成、seed 725）"
rng = np.random.default_rng(725)
DATA.mkdir(exist_ok=True)
N = 5000
freq = np.minimum(rng.geometric(0.42, N), 30)
last = pd.Timestamp("2025-12-31") - pd.to_timedelta(rng.integers(0, 365, N), unit="D")
C = pd.DataFrame({"customer_id": [f"C{i+1:05d}" for i in range(N)], "freq": freq, "last_date": last.date})
C.to_csv(DATA / "customers.csv", index=False)


def ntile(order_df, k=5):
    n = len(order_df); base, extra = divmod(n, k)
    sizes = [base + (1 if i < extra else 0) for i in range(k)]
    return np.repeat(np.arange(1, k + 1), sizes)


o1 = C.sort_values(["freq", "customer_id"], ascending=[False, True]); C.loc[o1.index, "ntile_id"] = ntile(o1)
o2 = C.assign(ld=pd.to_datetime(C.last_date)).sort_values(["freq", "ld", "customer_id"], ascending=[False, False, True]); C.loc[o2.index, "ntile_recent"] = ntile(o2)
rk = C.freq.rank(ascending=False, method="min")
C["rank_tier"] = (np.floor((rk - 1) * 5.0 / N) + 1).astype(int)
for c in ["ntile_id", "ntile_recent"]: C[c] = C[c].astype(int)

con = duckdb.connect(); con.execute("SET threads=1")
c0 = C[["customer_id", "freq", "last_date"]].assign(last_date=pd.to_datetime(C.last_date))
con.register("c0", c0); con.execute("CREATE TABLE customers AS SELECT * FROM c0")
dq = con.execute((SQL / "02_rfm_tiers_duckdb.sql").read_text(encoding="utf-8")).df().set_index("customer_id")
Ci = C.set_index("customer_id")
for c in ["ntile_id", "ntile_recent", "rank_tier"]: assert (dq[c].astype(int) == Ci.loc[dq.index, c]).all(), c

split = C.groupby("freq").ntile_id.nunique(); split_vals = split[split > 1].index.tolist()
in_split = C.freq.isin(split_vals)
# 同じ回数なのに、その回数の多数派の段と違う段に入った人
maj = C.groupby("freq").ntile_id.agg(lambda s: s.value_counts().idxmax())
off_major = int((C.ntile_id != C.freq.map(maj)).sum())
changed = int((C.ntile_id != C.ntile_recent).sum())
sizes = pd.DataFrame({m: C[m].value_counts().sort_index() for m in ["ntile_id", "ntile_recent", "rank_tier"]}).fillna(0).astype(int)
sizes.to_csv(RES / "tier_sizes.csv")
cross = pd.crosstab(C.freq.clip(upper=8), C.ntile_id); cross.to_csv(RES / "freq_by_ntile.csv")
C.to_csv(RES / "customers_tiers.csv", index=False)
fv = C.freq.value_counts().sort_index()

out = {"customers": N, "freq_share_pct": {str(k): round(float(v / N * 100), 1) for k, v in fv.head(6).items()},
       "freq_mean": round(float(freq.mean()), 2),
       "split_freq_values": [int(v) for v in split_vals], "customers_in_split_values": int(in_split.sum()),
       "customers_in_split_values_pct": round(float(in_split.mean() * 100), 1),
       "off_majority_tier": off_major, "off_majority_tier_pct": round(off_major / N * 100, 1),
       "changed_by_tiebreak": changed, "changed_by_tiebreak_pct": round(changed / N * 100, 1),
       "ntile_tiers_of_freq1": sorted(C[C.freq == 1].ntile_id.unique().tolist()),
       "tier_sizes": {m: sizes[m].to_dict() for m in sizes.columns}, "rank_tier_used": sorted(C.rank_tier.unique().tolist()),
       "sql_matches_python": True}
out["tier_sizes"] = {m: {str(k): int(v) for k, v in d.items()} for m, d in out["tier_sizes"].items()}
json.dump(out, open(RES / "a725_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：購入回数ごとの人数を NTILE の段で色分け
cols = {1: "#1f4e8c", 2: BLUE, 3: LIGHT, 4: "#f3b38f", 5: ORANGE}
fig, ax = plt.subplots(figsize=(9, 3.9)); bottom = np.zeros(len(cross))
for t in cross.columns:
    ax.bar([str(v) if v < 8 else "8+" for v in cross.index], cross[t].values, bottom=bottom, color=cols[t], label=f"{t}段")
    bottom += cross[t].values
ax.set_xlabel("購入回数"); ax.set_ylabel("人数"); ax.legend(frameon=False, ncol=5, fontsize=9, title="NTILE(5) の段", title_fontsize=9)
ax.set_title(f"NTILE で5等分すると、同じ回数の人が別の段に分かれる（{len(split_vals)}つの回数で{in_split.sum():,}人）")
save(fig, "a725_split.png", SRC)

# 図2：段ごとの人数
fig, ax = plt.subplots(figsize=(8, 3.6)); x = np.arange(1, 6); wd = 0.38
a = sizes.ntile_id.reindex(x, fill_value=0); b = sizes.rank_tier.reindex(x, fill_value=0)
ax.bar(x - wd / 2, a, wd, color=BLUE, label="NTILE(5)"); ax.bar(x + wd / 2, b, wd, color=ORANGE, label="同じ回数は同じ段（順位で段を決める）")
for i in range(5):
    ax.text(x[i] - wd / 2, a.iloc[i] + 40, f"{a.iloc[i]:,}", ha="center", fontsize=8.5); ax.text(x[i] + wd / 2, b.iloc[i] + 40, f"{b.iloc[i]:,}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([f"{t}段" for t in x]); ax.set_ylabel("人数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("同じ回数を同じ段にすると、人数は偏り、4段・5段は空になる")
save(fig, "a725_sizes.png", SRC)

# 図3：2つ目の順を変えたときに段が変わった人
chg = C[C.ntile_id != C.ntile_recent].freq.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar([str(v) for v in chg.index], chg.values, color=ORANGE)
for i, v in enumerate(chg.values): ax.text(i, v + 15, f"{v:,}人", ha="center", fontsize=9)
ax.set_xlabel("購入回数"); ax.set_ylabel("段が変わった人数")
ax.set_title(f"並べる2つ目の順（顧客番号→最終購入日）を変えるだけで {changed:,}人（{changed / N * 100:.1f}%）の段が変わる", fontsize=11.5)
save(fig, "a725_tiebreak.png", SRC)
print(json.dumps(out, ensure_ascii=False))
