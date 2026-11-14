"""P10 分かれ道の庭（garden of forking paths）：本当は差がない A/B テストで、分析の選び方が増えると
「どれか1つは有意」になる割合はどれだけ増えるか。架空のネット通販（各群 4,000人）。種を固定して2,000回。
分析者が選べるもの（どれも、もっともらしい選び方）
  指標3つ：購入した割合／1人あたりの購入額／1人あたりの購入点数
  対象4つ：全員／新規客／既存客／スマホ
  外れ値2つ：そのまま／上位1%を切る（額・点数のみ。購入した割合では同じ）
  期間2つ：2週間すべて／最初の1週
使い方: cd src && python p10_forking.py
"""
import json, itertools
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
N, SIMS = 4000, 2000
METRICS, SEGS, OUTL, PERIODS = ["購入した割合", "1人あたりの購入額", "1人あたりの購入点数"], ["全員", "新規客", "既存客", "スマホ"], ["そのまま", "上位1%を切る"], ["2週間", "最初の1週"]
PATHS = [p for p in itertools.product(METRICS, SEGS, OUTL, PERIODS) if not (p[0] == "購入した割合" and p[2] == "上位1%を切る")]


def group(rng):
    new = rng.random(N) < 0.3; mobile = rng.random(N) < 0.6
    out = {}
    for w in (1, 2):                                   # 週ごとに作り、1週目と2週間の合計を持つ
        buy = rng.random(N) < np.where(new, 0.03, 0.05)
        items = np.where(buy, 1 + rng.poisson(1.2, N), 0)
        amount = np.where(buy, rng.lognormal(8.3, 0.9, N), 0.0)
        out[w] = (buy, items, amount)
    wk1 = out[1]; tot = tuple(a + b if a.dtype != bool else (a | b) for a, b in zip(out[1], out[2]))
    return {"new": new, "mobile": mobile, "最初の1週": wk1, "2週間": tot}


def pval(a, b, metric, outl, seg_a, seg_b, period):
    ga, gb = a[period], b[period]
    idx = {"購入した割合": 0, "1人あたりの購入点数": 1, "1人あたりの購入額": 2}[metric]
    xa = ga[idx][seg_a].astype(float); xb = gb[idx][seg_b].astype(float)
    if outl == "上位1%を切る":
        cap = np.quantile(np.concatenate([xa, xb]), 0.99); xa = np.minimum(xa, cap); xb = np.minimum(xb, cap)
    return stats.ttest_ind(xa, xb, equal_var=False).pvalue


def seg_mask(g, seg):
    return {"全員": np.ones(N, bool), "新規客": g["new"], "既存客": ~g["new"], "スマホ": g["mobile"]}[seg]


rng = np.random.default_rng(10)
P = np.empty((SIMS, len(PATHS)))
for s in range(SIMS):
    a, b = group(rng), group(rng)                      # A と B は同じ作り方（本当の差はない）
    for j, (m, seg, o, per) in enumerate(PATHS):
        P[s, j] = pval(a, b, m, o, seg_mask(a, seg), seg_mask(b, seg), per)
np.save(R / "pvalues.npy", P.astype(np.float32))

pre = PATHS.index(("購入した割合", "全員", "そのまま", "2週間"))
sig = P < 0.05
by_k = []
order_rng = np.random.default_rng(11)
for k in range(1, len(PATHS) + 1):
    # k 通りの分析を試す（事前に決めた1つ＋ほかからランダムに k-1 通り）。どれか1つでも p<0.05 なら「有意」と報告する
    hits = []
    for s in range(SIMS):
        others = order_rng.choice([i for i in range(len(PATHS)) if i != pre], k - 1, replace=False)
        hits.append(sig[s, [pre, *others]].any())
    by_k.append({"k": k, "any_significant": float(np.mean(hits))})
K = pd.DataFrame(by_k); K.round(4).to_csv(R / "by_number_of_paths.csv", index=False, encoding="utf-8")
# 指標だけ選べる／対象だけ選べる場合
sel = lambda cond: [j for j, p in enumerate(PATHS) if cond(p)]
scen = {"事前に1つ決める（購入した割合・全員・2週間）": [pre],
        "指標だけ選べる（3通り）": sel(lambda p: p[1] == "全員" and p[2] == "そのまま" and p[3] == "2週間"),
        "対象だけ選べる（4通り）": sel(lambda p: p[0] == "購入した割合" and p[2] == "そのまま" and p[3] == "2週間"),
        "期間だけ選べる（2通り）": sel(lambda p: p[0] == "購入した割合" and p[1] == "全員" and p[2] == "そのまま"),
        f"全部選べる（{len(PATHS)}通り）": list(range(len(PATHS)))}
S = {k: round(float(sig[:, v].any(axis=1).mean()), 4) for k, v in scen.items()}
corr = np.corrcoef(stats.norm.ppf(np.clip(P, 1e-12, 1 - 1e-12)).T)
main = {"n_paths": len(PATHS), "sims": SIMS, "per_group": N, "scenarios": S,
        "single_path_fpr_mean": round(float(sig.mean()), 4),
        "independent_if_all_paths": round(1 - 0.95 ** len(PATHS), 4),
        "mean_corr_between_paths": round(float(corr[np.triu_indices(len(PATHS), 1)].mean()), 3)}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), dpi=120, gridspec_kw={"width_ratios": [1.1, 1]})
ax = axs[0]
ax.plot(K.k, K.any_significant * 100, marker="o", ms=3, color="#b5452b", label="試した分析のどれかが p<0.05")
ax.plot(K.k, (1 - 0.95 ** K.k) * 100, ls="--", color="#999", label="分析どうしが無関係なら")
ax.axhline(5, color="#1f5f8b", lw=1); ax.text(len(PATHS), 6, "5%（事前に1つ決めた場合）", ha="right", color="#1f5f8b", fontsize=8.5)
ax.set_xlabel("試した分析の数"); ax.set_ylabel("本当は差がないのに「有意」と言える割合（%）")
ax.set_title("分析の選び方が増えると、「有意」は簡単に見つかる", fontsize=10); ax.legend(fontsize=8.5); ax.grid(alpha=.3)
ax = axs[1]
ks = list(S); vs = [S[k] * 100 for k in ks]
ax.barh(range(len(ks)), vs, color=["#1f5f8b"] + ["#c0692b"] * 3 + ["#b5452b"])
for i, v in enumerate(vs): ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
ax.set_yticks(range(len(ks)), ks, fontsize=8.5); ax.invert_yaxis(); ax.set_xlabel("「有意」と言える割合（%）")
ax.set_title("どこが選べるかで、増え方が違う", fontsize=10)
for a_ in axs:
    for sp in ("top", "right"): a_.spines[sp].set_visible(False)
fig.suptitle(f"本当は差がない A/B テストを {SIMS:,} 回（架空のネット通販、各群 {N:,} 人）", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "p10_01_forking.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, indent=1))
