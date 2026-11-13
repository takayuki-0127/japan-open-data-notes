"""691 同じ顧客の重複行から「最初」と「最新」のどちらを残すかで、属性の集計はどれだけ変わるのか

架空の顧客表（2万人）。会員ランクの変更や引っ越しのたびに、上書きせず行を足す作りになっている（更新日時つき）。
重複を除く方法を4通り比べる：
  raw   重複を除かずに数える
  first 顧客ごとに最初の行を残す
  last  顧客ごとに最新の行を残す（いまの属性）
  asof  2024-12-31 までの行の中で最新を残す（その日時点の属性）
いまの属性を知りたいなら last が正しく、2024年末時点なら asof が正しい。それぞれの取り違えでどれだけ違うかを数える。
DuckDB の SQL でも同じ集計をして一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の顧客表（作成者が乱数で作成、seed 691）"
rng = np.random.default_rng(691)
DATA.mkdir(exist_ok=True)
N = 20000
RANKS = ["一般", "シルバー", "ゴールド", "プラチナ"]
REGIONS = ["北部", "東部", "中央", "西部", "南部"]

rows, rid = [], 0
start = pd.Timestamp("2021-01-01"); end = pd.Timestamp("2026-10-31")
for c in range(1, N + 1):
    t = start + pd.Timedelta(days=int(rng.integers(0, (end - start).days - 30)))
    rank = int(rng.choice(4, p=[0.7, 0.2, 0.08, 0.02])); reg = int(rng.choice(5, p=[0.15, 0.25, 0.3, 0.2, 0.1]))
    rid += 1; rows.append((rid, c, t, REGIONS[reg], RANKS[rank]))
    while True:
        t = t + pd.Timedelta(days=int(rng.exponential(420)) + 30)
        if t > end:
            break
        if rng.uniform() < 0.75:                     # ランクの変更（上がることが多い）
            rank = int(np.clip(rank + rng.choice([1, -1], p=[0.8, 0.2]), 0, 3))
        else:                                         # 引っ越し（中央へ移る人がやや多い）
            reg = int(rng.choice(5, p=[0.1, 0.25, 0.4, 0.15, 0.1]))
        rid += 1; rows.append((rid, c, t, REGIONS[reg], RANKS[rank]))
raw = pd.DataFrame(rows, columns=["row_id", "customer_id", "updated_at", "region", "member_rank"])
raw.to_csv(DATA / "customers_raw.csv", index=False, date_format="%Y-%m-%d")

ASOF = pd.Timestamp("2024-12-31")
s = raw.sort_values(["customer_id", "updated_at", "row_id"])
V = {"raw": raw, "first": s.groupby("customer_id").head(1), "last": s.groupby("customer_id").tail(1),
     "asof": s[s.updated_at <= ASOF].groupby("customer_id").tail(1)}
rank_tab = pd.DataFrame({k: v["member_rank"].value_counts().reindex(RANKS, fill_value=0) for k, v in V.items()})
reg_tab = pd.DataFrame({k: v["region"].value_counts().reindex(REGIONS, fill_value=0) for k, v in V.items()})
rank_tab.to_csv(RES / "by_rank.csv", index_label="member_rank"); reg_tab.to_csv(RES / "by_region.csv", index_label="region")

# DuckDB で同じ集計
con = duckdb.connect(); con.execute("SET threads=1")
con.register("raw_df", raw.assign(updated_at=raw.updated_at.dt.date))
con.execute("CREATE TABLE customers_raw AS SELECT * FROM raw_df")
q = (SQL / "02_dedup_duckdb.sql").read_text(encoding="utf-8")
dq = con.execute(q).df()
for m in ["raw", "first", "last", "asof"]:
    d = dq[dq.method == m].set_index("member_rank")["customers"].reindex(RANKS, fill_value=0)
    assert (d.values == rank_tab[m].values).all(), m

dup = raw.customer_id.value_counts()
last_ = V["last"].set_index("customer_id"); first_ = V["first"].set_index("customer_id")
asof_ = V["asof"].set_index("customer_id"); last_in_asof = last_.loc[asof_.index]
out = {"customers": N, "rows": len(raw), "customers_with_dup": int((dup > 1).sum()),
       "dup_share_pct": round(float((dup > 1).mean() * 100), 1),
       "by_rank": rank_tab.to_dict(), "by_region": reg_tab.to_dict(),
       "first_vs_last_rank_diff_customers": int((first_["member_rank"] != last_["member_rank"]).sum()),
       "first_vs_last_region_diff_customers": int((first_["region"] != last_["region"]).sum()),
       "asof_customers": len(asof_),
       "last_vs_asof_rank_diff_customers": int((asof_["member_rank"] != last_in_asof["member_rank"]).sum()),
       "gold_plus_share_pct": {k: round(float(v["member_rank"].isin(["ゴールド", "プラチナ"]).mean() * 100), 1) for k, v in V.items()},
       "asof_gold_plus_pct_correct": round(float(asof_["member_rank"].isin(["ゴールド", "プラチナ"]).mean() * 100), 1),
       "asof_gold_plus_pct_using_last": round(float(last_in_asof["member_rank"].isin(["ゴールド", "プラチナ"]).mean() * 100), 1),
       "sql_matches_python": True}
json.dump(out, open(RES / "a691_main.json", "w"), ensure_ascii=False, indent=1)

meth = {"raw": "重複を除かない", "first": "最初の行を残す", "last": "最新の行を残す（いま）", "asof": "2024年末時点の最新"}
col = {"raw": GRAY, "first": ORANGE, "last": BLUE, "asof": GREEN}
# 図1：ランク別の人数
fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(4); w = 0.2
for k, m in enumerate(["raw", "first", "last", "asof"]):
    ax.bar(x + (k - 1.5) * w, rank_tab[m], w, color=col[m], label=meth[m])
    for i, v in enumerate(rank_tab[m]):
        ax.text(i + (k - 1.5) * w, v, f"{v:,}", ha="center", va="bottom", fontsize=7, rotation=90)
ax.set_xticks(x); ax.set_xticklabels(RANKS); ax.set_ylabel("人数（行数）"); ax.legend(frameon=False, fontsize=8.5)
ax.set_title("会員ランク別の人数：残す行で上位ランクの人数が何倍も変わる")
save(fig, "a691_by_rank.png", SRC)

# 図2：上位ランクの割合
fig, ax = plt.subplots(figsize=(8, 3.6))
ms = ["raw", "first", "last", "asof"]; v = [out["gold_plus_share_pct"][m] for m in ms]
ax.barh(range(4), v, color=[col[m] for m in ms])
for i, vv in enumerate(v):
    ax.text(vv, i, f" {vv:.1f}%", va="center", fontsize=9)
ax.set_yticks(range(4)); ax.set_yticklabels([meth[m] for m in ms]); ax.invert_yaxis()
ax.set_xlabel("ゴールド以上の割合（%）"); ax.set_title("「いま」の割合を、最初の行で数えると大きく低く出る")
save(fig, "a691_gold_share.png", SRC)

# 図3：地域別（最初 vs 最新）
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(5); w = 0.38
ax.bar(x - w / 2, reg_tab["first"], w, color=ORANGE, label=meth["first"]); ax.bar(x + w / 2, reg_tab["last"], w, color=BLUE, label=meth["last"])
for i in range(5):
    d = reg_tab["last"].iloc[i] - reg_tab["first"].iloc[i]
    ax.text(i, max(reg_tab["first"].iloc[i], reg_tab["last"].iloc[i]), f"{d:+,}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(REGIONS); ax.set_ylabel("人数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("地域別の人数：引っ越しの分だけ、中央が増え他が減る")
save(fig, "a691_by_region.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
