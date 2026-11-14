"""723 前年がマイナスの利益の伸び率を、ふつうの式で出すと、何店で向きが逆に見えるのか

架空の40店の営業利益（万円）の前年と今年。前年がマイナス（赤字）の店や、0に近い店を含む。
伸び率を3通りで出す：
  ふつうの式：（今年−前年）÷前年
  分母を絶対値：（今年−前年）÷|前年|
  差額：今年−前年（伸び率にしない）
「よくなった（差額が＋）のに伸び率が−」「悪くなったのに＋」の店（向きが逆に見える店）と、並びの入れ替わりを数える。
DuckDB の SQL でも同じ値を出し、Python と一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の40店の営業利益（作成者が乱数で作成、seed 723）"
rng = np.random.default_rng(723)
DATA.mkdir(exist_ok=True)
NS = 40
prev = np.round(rng.normal(300, 400, NS), 0)
prev[np.abs(prev) < 5] = 15                               # ちょうど0の店は作らない
cur = np.round(prev + rng.normal(60, 250, NS), 0)
P = pd.DataFrame({"store_id": [f"S{i+1:02d}" for i in range(NS)], "profit_prev": prev, "profit_cur": cur})
P.to_csv(DATA / "profits.csv", index=False)

P["diff"] = P.profit_cur - P.profit_prev
P["growth_plain"] = P["diff"] / P.profit_prev
P["growth_absbase"] = P["diff"] / P.profit_prev.abs()
P["flipped"] = np.sign(P["diff"]) != np.sign(P.growth_plain)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("p0", P[["store_id", "profit_prev", "profit_cur"]]); con.execute("CREATE TABLE profits AS SELECT * FROM p0")
dq = con.execute((SQL / "02_growth_duckdb.sql").read_text(encoding="utf-8")).df().set_index("store_id")
Pi = P.set_index("store_id")
for c in ["diff", "growth_plain", "growth_absbase"]: assert np.allclose(dq[c], Pi[c]), c
assert (dq.direction_flipped.astype(bool) == Pi.flipped).all()
assert dq.growth_or_null.isna().sum() == (Pi.profit_prev <= 0).sum()

for c in ["growth_plain", "growth_absbase", "diff"]: P["rank_" + c] = P[c].rank(ascending=False, method="min").astype(int)
P.round(4).to_csv(RES / "by_store.csv", index=False)
neg = P.profit_prev < 0
top5_plain = set(P.nsmallest(5, "rank_growth_plain").store_id); top5_abs = set(P.nsmallest(5, "rank_growth_absbase").store_id)
bot5_plain = set(P.nlargest(5, "rank_growth_plain").store_id)
small = P.profit_prev.abs() < 50
out = {"stores": NS, "prev_negative": int(neg.sum()), "improved": int((P["diff"] > 0).sum()),
       "flipped": int(P.flipped.sum()), "flipped_all_prev_negative": bool((P.flipped == neg).all()),
       "flipped_examples": P[P.flipped].sort_values("growth_plain").head(5)[["store_id", "profit_prev", "profit_cur", "growth_plain"]].round(3).to_dict("records"),
       "prev_abs_lt50": int(small.sum()), "max_abs_growth_plain_pct": round(float(P.growth_plain.abs().max() * 100), 0),
       "max_abs_growth_prev": float(P.loc[P.growth_plain.abs().idxmax(), "profit_prev"]),
       "spearman_plain_vs_diff": round(float(stats.spearmanr(P.growth_plain, P["diff"]).statistic), 3),
       "spearman_abs_vs_diff": round(float(stats.spearmanr(P.growth_absbase, P["diff"]).statistic), 3),
       "prev_negative_in_bottom5_plain": int(len(bot5_plain & set(P[neg].store_id))),
       "improved_in_bottom5_plain": int(len(bot5_plain & set(P[P["diff"] > 0].store_id))),
       "max_rank_move_plain_vs_abs": int((P.rank_growth_plain - P.rank_growth_absbase).abs().max()),
       "sql_matches_python": True}
json.dump(out, open(RES / "a723_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：前年の利益とふつうの伸び率
fig, ax = plt.subplots(figsize=(8.5, 4))
c = np.where(P["diff"] > 0, BLUE, ORANGE)
ax.scatter(P.profit_prev, P.growth_plain * 100, c=c, s=26, zorder=3)
ax.axhline(0, color=INK, lw=0.8); ax.axvline(0, color=GRAY, lw=0.8, ls="--")
ax.set_yscale("symlog", linthresh=100)
ax.set_xlabel("前年の営業利益（万円）"); ax.set_ylabel("ふつうの式の伸び率（%、±100%の外は対数）")
ax.scatter([], [], color=BLUE, label="今年のほうがよい店"); ax.scatter([], [], color=ORANGE, label="今年のほうが悪い店")
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title(f"前年がマイナスの店（点線の左の{out['flipped']}店）は、伸び率の向きが逆になる")
save(fig, "a723_prev_vs_growth.png", SRC)

# 図2：向きが逆に見えた店
F = P[neg].sort_values("profit_prev")
fig, ax = plt.subplots(figsize=(9, 3.8)); x = np.arange(len(F))
ax.bar(x - 0.2, F.profit_prev, 0.4, color=GRAY, label="前年")
ax.bar(x + 0.2, F.profit_cur, 0.4, color=np.where(F["diff"] > 0, BLUE, ORANGE), label="今年（青：よくなった、橙：悪くなった）")
for i, r in enumerate(F.itertuples()):
    ax.text(i, max(r.profit_prev, r.profit_cur, 0) + 30, f"{r.growth_plain * 100:+.0f}%", ha="center", fontsize=8)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(F.store_id, fontsize=8)
ax.set_ylabel("営業利益（万円）"); ax.legend(frameon=False, fontsize=8.5, loc="lower right")
ax.set_title("前年が赤字の店：数字はふつうの式の伸び率（向きが逆になる）")
save(fig, "a723_negative_base.png", SRC)

# 図3：3通りの順位
fig, ax = plt.subplots(figsize=(8, 3.8))
o = P.sort_values("rank_diff")
for i, r in enumerate(o.itertuples()):
    col = ORANGE if r.flipped else GRAY
    ax.plot([0, 1, 2], [r.rank_growth_plain, r.rank_growth_absbase, r.rank_diff], color=col, lw=1.4 if r.flipped else 0.7, alpha=0.9)
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["ふつうの伸び率", "分母を絶対値", "差額"]); ax.invert_yaxis()
ax.set_ylabel("順位（1位が上）"); ax.set_title("前年が赤字の店（橙）は、ふつうの伸び率で大きく順位が動く")
save(fig, "a723_ranks.png", SRC)
print(json.dumps(out, ensure_ascii=False))
