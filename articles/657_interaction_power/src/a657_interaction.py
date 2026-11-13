"""657 交互作用を見つけるには、主効果を見つけるときの何倍の件数が要るのか

架空の店の実験：施策A（する・しない）を、2種類の店（駅前・郊外）に同じ数ずつ割り付ける（2×2、どのマスも同じ件数）。
指標のばらつきは標準偏差1。
  主効果：施策の効果の平均（2種類の店の平均）が 0.2
  交互作用：施策の効果の「店の種類による差」が 0.2（駅前0.3・郊外0.1）／ 0.1（0.25・0.15）
回帰 y = a + b·A + c·B + d·A×B（A・B は ±1/2 で符号化）で b と d を検定する。
件数（全体）を100〜6,400で変え、各2,000回。検出力80%に要る件数を比べる。1回分は statsmodels と一致を確かめる。seed 657。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 657）"
rng = np.random.default_rng(657)
REPS = 2000
NS = [100, 200, 400, 600, 700, 760, 800, 840, 900, 1200, 1600, 2000, 2400, 2800, 3000, 3200, 3400, 4000, 6400, 9600, 11200, 12000, 12400, 12800, 13200, 14000, 16000]


def sim(n_total, main, inter, r, reps=REPS):
    k = n_total // 4
    # マスの平均：A=±1/2, B=±1/2 の組み合わせ
    cells = [(a, b) for a in (-0.5, 0.5) for b in (-0.5, 0.5)]
    means = np.stack([r.normal(main * a + inter * a * b, 1, (reps, k)).mean(axis=1) for a, b in cells], axis=1)
    # 残差の分散（マスの中のばらつき）を作るため、平方和を別に引く
    ss = r.chisquare(4 * (k - 1), reps)  # 分散1の正規なので、マス内の平方和はカイ二乗
    s2 = ss / (4 * (k - 1))
    m = dict(zip(cells, means.T))
    b_hat = ((m[(0.5, -0.5)] + m[(0.5, 0.5)]) - (m[(-0.5, -0.5)] + m[(-0.5, 0.5)])) / 2
    d_hat = (m[(0.5, 0.5)] - m[(-0.5, 0.5)]) - (m[(0.5, -0.5)] - m[(-0.5, -0.5)])
    se_b = np.sqrt(s2 / k); se_d = np.sqrt(4 * s2 / k)
    df = 4 * (k - 1)
    pb = 2 * stats.t.sf(np.abs(b_hat / se_b), df); pd_ = 2 * stats.t.sf(np.abs(d_hat / se_d), df)
    return (pb < 0.05).mean(), (pd_ < 0.05).mean(), b_hat.mean(), d_hat.mean()


# 1回分を statsmodels で確かめる（マスの平均から出した推定と同じになるか）
r0 = np.random.default_rng(6571); k = 100
rows = []
for a in (-0.5, 0.5):
    for b in (-0.5, 0.5):
        y = r0.normal(0.2 * a + 0.2 * a * b, 1, k)
        rows += [(a, b, v) for v in y]
D = pd.DataFrame(rows, columns=["A", "B", "y"])
fit = smf.ols("y ~ A * B", D).fit()
cm = D.groupby(["A", "B"]).y.mean()
b_chk = ((cm[(0.5, -0.5)] + cm[(0.5, 0.5)]) - (cm[(-0.5, -0.5)] + cm[(-0.5, 0.5)])) / 2
d_chk = (cm[(0.5, 0.5)] - cm[(-0.5, 0.5)]) - (cm[(0.5, -0.5)] - cm[(-0.5, -0.5)])
assert np.isclose(fit.params["A"], b_chk) and np.isclose(fit.params["A:B"], d_chk)
assert np.isclose(fit.bse["A:B"] / fit.bse["A"], 2.0)

rows = []
for n in NS:
    pb, pd2, bm, dm = sim(n, 0.2, 0.2, rng)
    _, pd1, _, dm1 = sim(n, 0.2, 0.1, rng)
    rows.append({"n": n, "power_main_0.2": pb, "power_inter_0.2": pd2, "power_inter_0.1": pd1, "mean_b": bm, "mean_d_0.2": dm, "mean_d_0.1": dm1})
R = pd.DataFrame(rows); R.round(4).to_csv(RES / "power.csv", index=False)


def need(col):
    s = R[R[col] >= 0.8]
    return int(s.n.iloc[0]) if len(s) else None


# 理論の件数（正規近似）：主効果 n = 4·(z_a+z_b)²/δ²、交互作用は16倍の分散
z = stats.norm.ppf(0.975) + stats.norm.ppf(0.8)
theory = {"main_0.2": 4 * z ** 2 / 0.2 ** 2, "inter_0.2": 16 * z ** 2 / 0.2 ** 2, "inter_0.1": 16 * z ** 2 / 0.1 ** 2}
out = {"reps": REPS, "sd": 1.0, "main_effect": 0.2,
       "n_needed_80pct_sim": {"main_0.2": need("power_main_0.2"), "inter_0.2": need("power_inter_0.2"), "inter_0.1": need("power_inter_0.1")},
       "n_needed_80pct_theory": {k: round(v) for k, v in theory.items()},
       "power_at_n800": {c: round(float(R.set_index("n").loc[800, c]) * 100, 1) for c in ["power_main_0.2", "power_inter_0.2", "power_inter_0.1"]},
       "power_at_n3200": {c: round(float(R.set_index("n").loc[3200, c]) * 100, 1) for c in ["power_main_0.2", "power_inter_0.2", "power_inter_0.1"]},
       "power_at_n12800": {c: round(float(R.set_index("n").loc[12800, c]) * 100, 1) for c in ["power_main_0.2", "power_inter_0.2", "power_inter_0.1"]},
       "se_ratio_inter_over_main": 2.0, "statsmodels_check_A": round(float(fit.params["A"]), 4), "statsmodels_check_AB": round(float(fit.params["A:B"]), 4)}
json.dump(out, open(RES / "a657_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：検出力の曲線
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(R.n, R["power_main_0.2"] * 100, marker="o", color=BLUE, label="主効果 0.2（施策の効果の平均）")
ax.plot(R.n, R["power_inter_0.2"] * 100, marker="s", color=ORANGE, label="交互作用 0.2（効果の差 0.3 と 0.1）")
ax.plot(R.n, R["power_inter_0.1"] * 100, marker="^", color=GRAY, label="交互作用 0.1（効果の差 0.25 と 0.15）")
ax.axhline(80, color=GRAY, lw=0.8, ls="--"); ax.set_xscale("log"); ax.set_xticks([100, 400, 800, 1600, 3200, 6400, 12800]); ax.set_xticklabels(["100", "400", "800", "1,600", "3,200", "6,400", "12,800"])
ax.set_xlabel("全体の件数（4つのマスに同じ数ずつ、対数の目盛り）"); ax.set_ylabel("見つけた割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("同じ大きさでも、交互作用を見つけるには4倍の件数が要る")
save(fig, "a657_power_curves.png", SRC)
# 図2：要る件数
fig, ax = plt.subplots(figsize=(8, 3.4))
lab = ["主効果 0.2", "交互作用 0.2", "交互作用 0.1"]
sv = [need("power_main_0.2"), need("power_inter_0.2"), need("power_inter_0.1")]
ax.barh(lab[::-1], sv[::-1], color=[BLUE, ORANGE, GRAY][::-1])
for i, (v, t) in enumerate(zip(sv[::-1], [theory["inter_0.1"], theory["inter_0.2"], theory["main_0.2"]])):
    ax.text(v, i, f" 約{v:,}件（計算の目安 {t:,.0f}件）", va="center", fontsize=9)
ax.set_xlim(0, max(sv) * 1.45); ax.set_xlabel("検出力80%に要る全体の件数（試した件数のうち80%を初めて超えたところ）", fontsize=10)
ax.set_title("交互作用が半分の大きさなら、16倍の件数が要る")
save(fig, "a657_n_needed.png", SRC, y=-0.05)
# 図3：なぜ4倍か：推定のばらつき
r2 = np.random.default_rng(6572)
bs, ds = [], []
for _ in range(2000):
    k = 200
    m = {}
    for a in (-0.5, 0.5):
        for b in (-0.5, 0.5):
            m[(a, b)] = r2.normal(0.2 * a + 0.2 * a * b, 1, k).mean()
    bs.append(((m[(0.5, -0.5)] + m[(0.5, 0.5)]) - (m[(-0.5, -0.5)] + m[(-0.5, 0.5)])) / 2)
    ds.append((m[(0.5, 0.5)] - m[(-0.5, 0.5)]) - (m[(0.5, -0.5)] - m[(-0.5, -0.5)]))
fig, ax = plt.subplots(figsize=(8, 3.8))
bins = np.linspace(-0.4, 0.8, 60)
ax.hist(bs, bins=bins, color=BLUE, alpha=0.7, label=f"主効果の推定（標準偏差 {np.std(bs):.3f}）")
ax.hist(ds, bins=bins, color=ORANGE, alpha=0.6, label=f"交互作用の推定（標準偏差 {np.std(ds):.3f}）")
ax.axvline(0.2, color="black", lw=1.2, ls="--"); ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("推定値（本当はどちらも0.2）"); ax.set_ylabel("回数（2,000回中）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("全体800件：交互作用の推定は、主効果の2倍の幅で揺れる")
save(fig, "a657_estimate_spread.png", SRC)
out["spread_n800"] = {"sd_main": round(float(np.std(bs)), 4), "sd_inter": round(float(np.std(ds)), 4)}
json.dump(out, open(RES / "a657_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
