"""688 店の固定効果だけ入れて、年ごとの流れを入れないと、施策の効果はどれだけずれるのか

架空の店のパネル：100店 × 8年。売上の指数 y = 店の水準 + 年の流れ + 効果×施策 + 誤差。
  年の流れ：毎年 g ずつ伸びる（g = 0・0.1・0.25・0.5）＋年ごとの振れ（標準偏差0.5、全店共通）
  施策：店ごとに始める年がばらばら（3〜8年目、まだ始めない店も2割）。始めたら続ける。本当の効果は1.0
  誤差：標準偏差1
推定は2通り：
  店の固定効果のみ（店ごとに平均を引いてから回帰）
  店と年の固定効果（店の平均と年の平均を引いてから回帰＝二元配置の固定効果）
各 g で500回くり返し、効果の推定の平均・ばらつき・95%区間（店でまとめた標準誤差）の当たり方を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の店のパネル（作成者が乱数で作成、seed 688）"
rng = np.random.default_rng(688)
NS, NY, REPS, TAU = 100, 8, 500, 1.0
GS = [0.0, 0.1, 0.25, 0.5]


def make(g):
    a = rng.normal(0, 2, NS)
    yr = g * np.arange(NY) + rng.normal(0, 0.5, NY)
    start = rng.choice(np.r_[np.arange(2, NY), 99], NS, p=np.r_[np.full(NY - 2, 0.8 / (NY - 2)), 0.2])
    D = (np.arange(NY)[None, :] >= start[:, None]).astype(float)
    y = a[:, None] + yr[None, :] + TAU * D + rng.normal(0, 1, (NS, NY))
    return y, D, yr


def fit(y, D, twoway):
    yd = y - y.mean(1, keepdims=True); Dd = D - D.mean(1, keepdims=True)
    if twoway:
        yd = yd - yd.mean(0, keepdims=True); Dd = Dd - Dd.mean(0, keepdims=True)
    b = (Dd * yd).sum() / (Dd ** 2).sum()
    e = yd - b * Dd
    se = np.sqrt(((Dd * e).sum(1) ** 2).sum()) / (Dd ** 2).sum()   # 店でまとめた標準誤差
    return b, se


rows = []
for g in GS:
    for r in range(REPS):
        y, D, _ = make(g)
        for name, tw in [("unit_fe", False), ("twoway_fe", True)]:
            b, se = fit(y, D, tw)
            rows.append({"g": g, "rep": r, "model": name, "est": b, "se": se, "cover": int(abs(b - TAU) <= 1.96 * se)})
R = pd.DataFrame(rows); R.to_csv(RES / "reps.csv.gz", index=False, float_format="%.5g", compression={"method": "gzip", "mtime": 0})
S = R.groupby(["g", "model"]).agg(mean=("est", "mean"), sd=("est", "std"), cover=("cover", "mean")).reset_index()
S["bias"] = S["mean"] - TAU; S["cover"] *= 100
S.round(4).to_csv(RES / "summary.csv", index=False)
out = {"stores": NS, "years": NY, "reps": REPS, "true_effect": TAU,
       "summary": {f"g{g}": {m: {k: round(float(S[(S.g == g) & (S.model == m)][k].iloc[0]), 3) for k in ["mean", "sd", "cover"]}
                             for m in ["unit_fe", "twoway_fe"]} for g in GS}}
json.dump(out, open(RES / "a688_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例（g=1）：施策を始めた店の割合と、全体の流れ
y, D, yr = make(0.25)
fig, ax = plt.subplots(figsize=(8.5, 3.8)); ax2 = ax.twinx()
yrs = np.arange(1, NY + 1)
ax.bar(yrs, D.mean(0) * 100, color=LIGHT, label="施策を始めている店の割合（左）")
ax2.plot(yrs, y.mean(0), color=INK, marker="o", lw=2, label="全店の平均の売上指数（右）")
ax.set_xlabel("年"); ax.set_ylabel("施策の店の割合（%）"); ax2.set_ylabel("売上指数の平均")
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9)
ax.set_title("全体が伸びる年ほど、施策の店も増える（毎年0.25ずつ伸びる例）")
save(fig, "a688_example.png", SRC)

# 図2：伸びの大きさごとの推定の平均
fig, ax = plt.subplots(figsize=(8.5, 4))
for m, c, l in [("unit_fe", ORANGE, "店の固定効果のみ"), ("twoway_fe", BLUE, "店と年の固定効果")]:
    s = S[S.model == m]
    ax.errorbar(s.g, s["mean"], yerr=s["sd"], color=c, marker="o", lw=2, capsize=4, label=l)
    for gg, mm in zip(s.g, s["mean"]):
        ax.text(gg + 0.012, mm + (0.12 if m == "unit_fe" else -0.12), f"{mm:.2f}", color=c, fontsize=9, va="center")
ax.axhline(TAU, color=INK, ls="--", lw=0.8); ax.text(0.36, TAU - 0.25, "点線＝本当の効果1.0", fontsize=8.5)
ax.set_xticks(GS); ax.set_xlabel("全体の売上指数の1年あたりの伸び"); ax.set_ylabel("効果の推定（平均±標準偏差）")
ax.legend(frameon=False, loc="upper left"); ax.set_title("年の流れを入れないと、伸びの分が施策の効果に入り込む")
save(fig, "a688_bias.png", SRC)

# 図3：区間の当たり方
fig, ax = plt.subplots(figsize=(8.5, 3.6))
x = np.arange(len(GS)); w = 0.38
for k, (m, c, l) in enumerate([("unit_fe", ORANGE, "店の固定効果のみ"), ("twoway_fe", BLUE, "店と年の固定効果")]):
    v = S[S.model == m]["cover"].values
    ax.bar(x + (k - 0.5) * w, v, w, color=c, label=l)
    for i, vv in enumerate(v):
        ax.text(i + (k - 0.5) * w, vv, f"{vv:.0f}", ha="center", va="bottom", fontsize=9)
ax.axhline(95, color=INK, ls="--", lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"伸び {g}" for g in GS])
ax.set_ylabel("95%区間が本当の効果を含んだ割合（%）"); ax.set_ylim(0, 110); ax.legend(frameon=False, loc="upper right", fontsize=9)
ax.set_title("年の流れを入れないと、伸びがなくても区間は当たらない")
save(fig, "a688_coverage.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
