"""645 5段階の評価を平均で比べるか、上位2つの割合で比べるかで、店の順位はどれだけ入れ替わるのか

架空の40店のアンケート（各店300人、5段階の満足度）。店ごとに回答の分布の形を変える：
真ん中に集まる店・4に集まる店・1と5に分かれる店などを、潜在的な満足度（正規分布）を4つの区切りで切って作る。
平均・上位2つ（4と5）の割合・下位2つ（1と2）の割合で店を並べ、順位の入れ替わりを数える。
DuckDB（1スレッド）の SQL と Python の集計が一致することを確かめる。数字は置いた分布の形で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の店のアンケート（作成者が乱数で作成、seed 645）"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(645)
NS, NR = 40, 300
CUT = np.array([-1.6, -0.8, 0.2, 1.2])            # 潜在的な満足度を5段階に切る区切り
rows, meta = [], []
for s in range(1, NS + 1):
    mu = rng.normal(0.2, 0.35)
    sd = rng.choice([0.5, 0.8, 1.2, 1.7])            # 小さいと真ん中に集まり、大きいと両端に分かれる
    z = rng.normal(mu, sd, NR)
    score = np.searchsorted(CUT, z) + 1
    meta.append({"store_id": f"T{s:02d}", "mu": mu, "sd": sd})
    for i, sc in enumerate(score):
        rows.append((f"T{s:02d}", i + 1, int(sc)))
SV = pd.DataFrame(rows, columns=["store_id", "resp_id", "score"])
SV.to_csv(DATA / "survey.csv", index=False)
M = pd.DataFrame(meta).set_index("store_id")

g = SV.groupby("store_id").score
T = pd.DataFrame({"n": g.size(), "mean_score": g.mean(), "top2_pct": g.apply(lambda x: (x >= 4).mean() * 100),
                  "bottom2_pct": g.apply(lambda x: (x <= 2).mean() * 100)})
dist = SV.groupby(["store_id", "score"]).size().unstack(fill_value=0).div(NR).mul(100)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("survey", SV)
sq = con.execute((SQL / "02_likert_duckdb.sql").read_text(encoding="utf-8")).df().set_index("store_id")
assert np.allclose(sq[["mean_score", "top2_pct", "bottom2_pct"]].values, T.loc[sq.index, ["mean_score", "top2_pct", "bottom2_pct"]].values)

R = pd.DataFrame({"mean": T.mean_score.rank(ascending=False, method="min"),
                  "top2": T.top2_pct.rank(ascending=False, method="min"),
                  "bottom2": T.bottom2_pct.rank(ascending=True, method="min")})
T = T.join(R.add_prefix("rank_")).join(M).join(dist.add_prefix("pct_"))
T.round(3).to_csv(RES / "per_store.csv")


def cmp(a, b):
    d = (R[a] - R[b]).abs()
    ta = set(R[a].nsmallest(5).index); tb = set(R[b].nsmallest(5).index)
    ba = set(R[a].nlargest(5).index); bb = set(R[b].nlargest(5).index)
    return {"spearman": round(float(stats.spearmanr(R[a], R[b])[0]), 3), "moved_5plus": int((d >= 5).sum()),
            "moved_10plus": int((d >= 10).sum()), "max_move": int(d.max()), "top5_overlap": len(ta & tb), "bottom5_overlap": len(ba & bb)}


res = {"mean_vs_top2": cmp("mean", "top2"), "mean_vs_bottom2": cmp("mean", "bottom2"), "top2_vs_bottom2": cmp("top2", "bottom2")}
# 平均が近い（差0.05以内）のに上位2つの割合が10ポイント以上違う組
pairs = 0; ex_pair = None; best = 0
idx = list(T.index)
for i in range(len(idx)):
    for j in range(i + 1, len(idx)):
        a, b = T.loc[idx[i]], T.loc[idx[j]]
        if abs(a.mean_score - b.mean_score) <= 0.05 and abs(a.top2_pct - b.top2_pct) >= 10:
            pairs += 1
            if abs(a.top2_pct - b.top2_pct) > best:
                best = abs(a.top2_pct - b.top2_pct); ex_pair = (idx[i], idx[j])
by_sd = T.groupby("sd").apply(lambda x: pd.Series({"stores": len(x), "rank_diff_mean_minus_top2": float((x.rank_mean - x.rank_top2).mean())})).round(2)
by_sd.to_csv(RES / "by_spread.csv")
out = {"stores": NS, "respondents_per_store": NR, "compare": res, "pairs_same_mean_diff_top2": pairs,
       "example_pair": {k: {"mean": round(float(T.loc[k, "mean_score"]), 3), "top2": round(float(T.loc[k, "top2_pct"]), 1),
                            "bottom2": round(float(T.loc[k, "bottom2_pct"]), 1), "dist": [round(float(x), 1) for x in dist.loc[k].values]} for k in ex_pair},
       "by_spread": by_sd.reset_index().to_dict(orient="records")}
pd.DataFrame(res).T.to_csv(RES / "summary.csv")
json.dump(out, open(RES / "a645_main.json", "w"), ensure_ascii=False, indent=1)

col = {0.5: LIGHT, 0.8: BLUE, 1.2: ORANGE, 1.7: INK}
lab = {0.5: "真ん中に集まる", 0.8: "やや集まる", 1.2: "広がる", 1.7: "両端に分かれる"}
# 図1：平均と上位2つの割合
fig, ax = plt.subplots(figsize=(7.8, 4.4))
for sd, c in col.items():
    x = T[T.sd == sd]
    ax.scatter(x.mean_score, x.top2_pct, color=c, s=28, label=f"回答が{lab[sd]}店")
for k in ex_pair:
    ax.annotate(k, (T.loc[k, "mean_score"], T.loc[k, "top2_pct"]), fontsize=8, xytext=(4, 4), textcoords="offset points")
ax.set_xlabel("平均（5段階）"); ax.set_ylabel("上位2つ（4・5）の割合（%）"); ax.legend(frameon=False, fontsize=8.5)
ax.set_title("同じ平均でも、回答の広がり方で上位2つの割合は違う（架空の40店）")
save(fig, "a645_mean_vs_top2.png", SRC)

# 図2：順位の比較
fig, ax = plt.subplots(figsize=(7.5, 4.4))
for sd, c in col.items():
    x = T[T.sd == sd]
    ax.scatter(x.rank_mean, x.rank_top2, color=c, s=28, label=lab[sd])
ax.plot([1, NS], [1, NS], color=GRAY, ls="--", lw=0.8)
ax.set_xlabel("平均での順位"); ax.set_ylabel("上位2つの割合での順位"); ax.invert_xaxis(); ax.invert_yaxis()
ax.legend(frameon=False, fontsize=8.5, title="回答の形", title_fontsize=8.5)
c_ = res["mean_vs_top2"]
ax.set_title(f"順位の相関{c_['spearman']:.2f}、5位以上動いた店{c_['moved_5plus']}店、最大{c_['max_move']}位")
save(fig, "a645_rank_compare.png", SRC)

# 図3：例の2店の回答の分布
fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(1, 6); w = 0.38
for i, (k, c) in enumerate(zip(ex_pair, [BLUE, ORANGE])):
    e = out["example_pair"][k]
    ax.bar(x + (i - 0.5) * w, e["dist"], w, color=c, label=f"{k}：平均{e['mean']:.2f}・上位2つ{e['top2']:.0f}%・下位2つ{e['bottom2']:.0f}%")
ax.set_xticks(x); ax.set_xticklabels(["1", "2", "3", "4", "5"]); ax.set_xlabel("回答"); ax.set_ylabel("割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("平均がほぼ同じ2店：一方は真ん中に集まり、一方は両端に分かれる")
save(fig, "a645_example_pair.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
