"""713 率が5%から6%になったのを「1ポイント増」と「20%増」のどちらで書くかで、店の並びはどれだけ変わるのか

架空の30店の申込み率（申込み÷来店）2期分。前の期の率は1〜20%でばらばら、来店数もばらばら。
変化を ポイントの差／%の変化／申込み件数の差 の3つで並べ、順位の入れ替わりと上位5店の重なりを数える。
DuckDB（1スレッド）と pandas で一致を確かめる。seed 713。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店の申込み率（作成者が乱数で作成、seed 713）"
rng = np.random.default_rng(713)
NS = 30
rate1 = np.exp(rng.uniform(np.log(1), np.log(20), NS)) / 100
visits1 = np.round(np.exp(rng.normal(np.log(4000), 0.6, NS))).astype(int)
visits2 = np.round(visits1 * rng.lognormal(0, 0.08, NS)).astype(int)
true_pt = rng.normal(0.4, 0.8, NS) / 100  # ポイントの変化
rate2 = np.clip(rate1 + true_pt, 0.002, None)
apps1 = rng.binomial(visits1, rate1); apps2 = rng.binomial(visits2, rate2)
S = pd.DataFrame({"store_id": [f"S{i + 1:02d}" for i in range(NS)], "visits1": visits1, "apps1": apps1, "visits2": visits2, "apps2": apps2})
S.to_csv(DATA / "stores.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("stores", S)
Q = con.execute((SQL / "02_rank_duckdb.sql").read_text(encoding="utf-8")).df().set_index("store_id")
P = S.set_index("store_id").copy()
P["rate1"] = P.apps1 * 100 / P.visits1; P["rate2"] = P.apps2 * 100 / P.visits2
P["diff_pt"] = P.rate2 - P.rate1; P["change_pct"] = (P.rate2 / P.rate1 - 1) * 100; P["diff_apps"] = P.apps2 - P.apps1
for c, k in [("diff_pt", "rank_pt"), ("change_pct", "rank_pct"), ("diff_apps", "rank_apps")]:
    P[k] = P[c].rank(ascending=False, method="min").astype(int)
    assert (P[k] == Q[k]).all()
assert np.allclose(P.diff_pt, Q.diff_pt) and np.allclose(P.change_pct, Q.change_pct)
P.round(3).to_csv(RES / "stores_ranked.csv")
top = lambda k: set(P.nsmallest(5, k).index)
low = P.rate1 < P.rate1.median()
out = {"stores": NS, "rate1_range_pct": [round(float(P.rate1.min()), 2), round(float(P.rate1.max()), 2)],
       "spearman": {"pt_vs_pct": round(float(stats.spearmanr(P.rank_pt, P.rank_pct).correlation), 3),
                    "pt_vs_apps": round(float(stats.spearmanr(P.rank_pt, P.rank_apps).correlation), 3),
                    "pct_vs_apps": round(float(stats.spearmanr(P.rank_pct, P.rank_apps).correlation), 3)},
       "top5_overlap": {"pt_and_pct": len(top("rank_pt") & top("rank_pct")), "pt_and_apps": len(top("rank_pt") & top("rank_apps")), "pct_and_apps": len(top("rank_pct") & top("rank_apps"))},
       "top5_pct_low_base_count": int(low[list(top("rank_pct"))].sum()),
       "top5_pt_low_base_count": int(low[list(top("rank_pt"))].sum()),
       "max_rank_jump_pt_vs_pct": int((P.rank_pt - P.rank_pct).abs().max()),
       "top_pct_store": {"store": P.change_pct.idxmax(), **{k: round(float(P.loc[P.change_pct.idxmax(), k]), 2) for k in ["rate1", "rate2", "diff_pt", "change_pct", "diff_apps", "rank_pt"]}},
       "top_pt_store": {"store": P.diff_pt.idxmax(), **{k: round(float(P.loc[P.diff_pt.idxmax(), k]), 2) for k in ["rate1", "rate2", "diff_pt", "change_pct", "diff_apps", "rank_pct"]}},
       "example_5_to_6": {"diff_pt": 1.0, "change_pct": 20.0}}
json.dump(out, open(RES / "a713_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：前の期の率と、%の変化・ポイントの差
fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.8))
axs[0].scatter(P.rate1, P.diff_pt, color=BLUE, s=25); axs[0].axhline(0, color=GRAY, lw=0.6)
axs[0].set_xscale("log"); axs[0].set_xlabel("前の期の申込み率（%、対数の目盛り）"); axs[0].set_ylabel("ポイントの差"); axs[0].set_title("ポイントの差", fontsize=11)
axs[1].scatter(P.rate1, P.change_pct, color=ORANGE, s=25); axs[1].axhline(0, color=GRAY, lw=0.6)
axs[1].set_xscale("log"); axs[1].set_xlabel("前の期の申込み率（%、対数の目盛り）"); axs[1].set_ylabel("%の変化"); axs[1].set_title("%の変化", fontsize=11)
fig.suptitle("%の変化は、前の率が低い店ほど大きく振れる", fontsize=13)
save(fig, "a713_base.png", SRC)
# 図2：順位の入れ替わり
fig, ax = plt.subplots(figsize=(6.5, 5.5))
for sid, r in P.iterrows():
    col = ORANGE if abs(r.rank_pt - r.rank_pct) >= 8 else LIGHT
    ax.plot([0, 1], [r.rank_pt, r.rank_pct], color=col, lw=1.5 if col == ORANGE else 1)
ax.set_xticks([0, 1]); ax.set_xticklabels(["ポイントの差の順位", "%の変化の順位"]); ax.invert_yaxis(); ax.set_ylabel("順位")
ax.set_title(f"30店の順位の入れ替わり（8位以上動いた店をオレンジ）、順位の相関{out['spearman']['pt_vs_pct']:.2f}", fontsize=11)
save(fig, "a713_ranks.png", SRC)
# 図3：上位5店
fig, ax = plt.subplots(figsize=(8, 3.6))
lab = ["ポイントの差", "%の変化", "件数の差"]
for i, k in enumerate(["rank_pt", "rank_pct", "rank_apps"]):
    t5 = P.nsmallest(5, k)
    ax.scatter([i] * 5, t5.rate1, s=60, color=[BLUE, ORANGE, GREEN][i])
    for sid, r in t5.iterrows():
        ax.annotate(sid, (i, r.rate1), xytext=(6, 0), textcoords="offset points", fontsize=8, va="center")
ax.axhline(P.rate1.median(), color=GRAY, lw=0.8, ls="--"); ax.text(2.4, P.rate1.median(), "前の率の中央値", fontsize=8, color=GRAY, va="bottom", ha="right")
ax.set_xticks(range(3)); ax.set_xticklabels(lab); ax.set_yscale("log"); ax.set_ylabel("上位5店の前の期の率（%）")
ax.set_title("並べ方で「伸びた上位5店」が入れ替わる。%の変化は率の低い店に寄る")
save(fig, "a713_top5.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
