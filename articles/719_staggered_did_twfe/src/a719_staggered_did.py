"""719 施策の開始時期が店ごとにずれ、効果が時間とともに大きくなるとき、ふつうの二方向固定効果の推定はどれだけずれるのか

架空の店の12期（0〜11期）の売上（指数）。店の固定の差（標準偏差3）・全店共通の期の動き・ノイズ（標準偏差1）。
施策の開始は 2期・5期・8期の3つのグループ（各20店）と、施策のない店20店。
効果の置き方：
  一定：開始した期から毎期 +2
  伸びる：開始した期から +s、+2s、+3s …（s＝伸び方、基本は0.5）
推定の2通り：
  二方向固定効果（TWFE）：y ＝ 店の効果 ＋ 期の効果 ＋ β×施策中 の β
  開始時期ごとに分けた差の差：グループ g・期 t ごとに、g−1期からの変化を「まだ施策をしていない店」の変化と比べ、店の数で平均
正解：施策をした店・期のすべてについての本当の効果の平均。
場面は3つ（一定・施策なしあり／伸びる・施策なしあり／伸びる・施策なしなし）。各300回。
施策のない店がない場面では、最後のグループの開始後は比べる相手がいないので、差の差はそれより前の期だけで出し、
正解も同じ店・期で計算する。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の店の12期の売上（作成者が乱数で作成、seed 719）"
rng = np.random.default_rng(719)
T, NG = 12, 20
STARTS = [2, 5, 8]


def make(slope, const, never=True):
    groups = STARTS + ([np.inf] if never else [])
    g = np.repeat(groups, NG); N = g.size
    alpha = rng.normal(0, 3, N); gamma = np.cumsum(rng.normal(0.3, 0.5, T))
    t = np.arange(T)
    e = t[None, :] - g[:, None]                        # 開始からの期（負なら前）
    D = (e >= 0).astype(float)
    eff = np.where(e >= 0, const + slope * (e + 1), 0.0)
    y = alpha[:, None] + gamma[None, :] + eff + rng.normal(0, 1, (N, T))
    return g, y, D, eff


def twfe(y, D):
    def dm(a): return a - a.mean(1, keepdims=True) - a.mean(0, keepdims=True) + a.mean()
    yd, dd = dm(y), dm(D)
    return float((yd * dd).sum() / (dd * dd).sum())


def cs(g, y, eff):
    est, tru, w = [], [], []
    for gg in STARTS:
        tr = g == gg
        for t in range(gg, T):
            ctrl = g > t                               # まだ施策をしていない店（施策なしを含む）
            if ctrl.sum() == 0: continue
            d_tr = (y[tr, t] - y[tr, gg - 1]).mean(); d_c = (y[ctrl, t] - y[ctrl, gg - 1]).mean()
            est.append(d_tr - d_c); tru.append(eff[tr, t].mean()); w.append(tr.sum())
    w = np.array(w, float)
    return float(np.dot(est, w) / w.sum()), float(np.dot(tru, w) / w.sum())


SCEN = [("一定の効果・施策なしの店あり", 0.0, 2.0, True), ("伸びる効果・施策なしの店あり", 0.5, 0.0, True),
        ("伸びる効果・施策なしの店なし", 0.5, 0.0, False)]
REPS = 300
rows = []
for name, s, c, nv in SCEN:
    for r in range(REPS):
        g, y, D, eff = make(s, c, nv)
        truth_all = float(eff[D == 1].mean())
        b = twfe(y, D); c_est, c_tru = cs(g, y, eff)
        rows.append({"scenario": name, "truth_all": truth_all, "twfe": b, "cs": c_est, "cs_truth": c_tru})
R = pd.DataFrame(rows)
S = R.groupby("scenario", sort=False).agg(truth_all=("truth_all", "mean"), twfe=("twfe", "mean"), twfe_sd=("twfe", "std"),
                                          cs=("cs", "mean"), cs_sd=("cs", "std"), cs_truth=("cs_truth", "mean")).reset_index()
S.round(4).to_csv(RES / "summary.csv", index=False)

# 伸び方 s を変えたとき（施策なしの店なし）
SL = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
sl_rows = []
for s in SL:
    tw, tr, cse, cst = [], [], [], []
    for r in range(100):
        g, y, D, eff = make(s, 1.0, False)
        tw.append(twfe(y, D)); tr.append(eff[D == 1].mean()); a, b = cs(g, y, eff); cse.append(a); cst.append(b)
    sl_rows.append({"slope": s, "truth_all": np.mean(tr), "twfe": np.mean(tw), "cs": np.mean(cse), "cs_truth": np.mean(cst)})
SLD = pd.DataFrame(sl_rows); SLD.round(4).to_csv(RES / "by_slope.csv", index=False)
neg = SLD[SLD.twfe < 0]
flip = float(neg.slope.min()) if len(neg) else None

out = {"periods": T, "starts": STARTS, "stores_per_group": NG, "reps": REPS,
       "scenarios": {r.scenario: {"truth_all": round(r.truth_all, 2), "twfe": round(r.twfe, 2), "twfe_sd": round(r.twfe_sd, 2),
                                  "cs": round(r.cs, 2), "cs_sd": round(r.cs_sd, 2), "cs_truth": round(r.cs_truth, 2)} for r in S.itertuples()},
       "slope_rows": {str(r.slope): {"truth_all": round(r.truth_all, 2), "twfe": round(r.twfe, 2), "cs": round(r.cs, 2), "cs_truth": round(r.cs_truth, 2)} for r in SLD.itertuples()},
       "slope_reps": 100, "const_in_slope_runs": 1.0}
json.dump(out, open(RES / "a719_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1つのデータの平均の推移（伸びる効果・施策なしの店なし）
g, y, D, eff = make(0.5, 0.0, False)
fig, ax = plt.subplots(figsize=(8, 3.8))
for gg, col in zip(STARTS, [ORANGE, BLUE, GREEN]):
    m = y[g == gg].mean(0); ax.plot(range(T), m, marker="o", ms=3, color=col, label=f"{gg}期に開始")
    ax.axvline(gg - 0.5, color=col, lw=0.8, ls=":")
ax.set_xlabel("期"); ax.set_ylabel("売上の指数（グループの平均）"); ax.legend(frameon=False)
ax.set_title("開始の早いグループほど、あとの期で効果が大きくなっている")
save(fig, "a719_paths.png", SRC)

# 図2：場面ごとの推定と正解
fig, ax = plt.subplots(figsize=(9, 3.9)); x = np.arange(len(S)); wd = 0.26
ax.bar(x - wd, S.truth_all, wd, color=GRAY, label="正解（施策した店・期の効果の平均）")
ax.bar(x, S.twfe, wd, color=ORANGE, yerr=S.twfe_sd, ecolor=INK, capsize=3, label="二方向固定効果")
ax.bar(x + wd, S.cs, wd, color=BLUE, yerr=S.cs_sd, ecolor=INK, capsize=3, label="開始時期ごとの差の差")
for i, r in enumerate(S.itertuples()):
    for dx, v, sd in [(-wd, r.truth_all, 0), (0, r.twfe, r.twfe_sd), (wd, r.cs, r.cs_sd)]:
        ax.text(i + dx, (v + sd + 0.08) if v >= 0 else (v - sd - 0.25), f"{v:.2f}", ha="center", fontsize=8.5)
    if abs(r.cs_truth - r.truth_all) > 0.05: ax.text(i + wd, r.cs + r.cs_sd + 0.35, f"同じ店・期の\n正解 {r.cs_truth:.2f}", ha="center", fontsize=7.5, color=BLUE)
ax.set_ylim(-0.7, 3.2)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(S.scenario, fontsize=9); ax.set_ylabel("効果の推定（指数）")
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3); ax.set_title(f"効果が伸びると、二方向固定効果は小さく出る（{REPS}回の平均、線は標準偏差）")
save(fig, "a719_estimates.png", SRC, y=-0.1)

# 図3：伸び方を変えたとき
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(SLD.slope, SLD.truth_all, marker="o", color=GRAY, label="正解（すべての施策した店・期）")
ax.plot(SLD.slope, SLD.twfe, marker="o", color=ORANGE, label="二方向固定効果")
ax.plot(SLD.slope, SLD.cs, marker="o", color=BLUE, label="開始時期ごとの差の差")
ax.plot(SLD.slope, SLD.cs_truth, ls="--", color=BLUE, lw=0.8, label="差の差と同じ店・期の正解")
ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("1期ごとの効果の伸び s（効果＝1＋s×開始からの期数、開始した期を1と数える）"); ax.set_ylabel("効果の推定（指数）")
ax.legend(frameon=False, fontsize=8.5); ax.set_title("施策なしの店がないと、効果が伸びても二方向固定効果はほとんど増えない（各100回）")
save(fig, "a719_by_slope.png", SRC)
print(json.dumps(out, ensure_ascii=False))
