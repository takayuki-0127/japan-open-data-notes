"""757 LOESS の span を小さくするか大きくするかで、曲がり具合の見え方と誤差はどう入れ替わるのか

正解の分かる曲線 f(x) = 2.0・exp(-(x-3)²/0.5) + 0.8・sin(0.9x)（x は 0〜10、x=3 付近に細い山）に、
標準偏差0.5の誤差を足した200点。LOESS（局所的な直線、statsmodels の lowess、頑健化なし it=0）の span を
0.05〜0.9 で変え、各300回：本当の曲線との誤差（RMSE）、山の高さの再現、山の位置のずれを測る。
5-fold の交差検証で span を選んだときの誤差も出す。seed 757。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 757）"
rng = np.random.default_rng(757)
N, SD, REPS = 200, 0.5, 300
SPANS = [0.05, 0.1, 0.15, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9]
grid = np.linspace(0.5, 9.5, 181)
f = lambda x: 2.0 * np.exp(-(x - 3) ** 2 / 0.5) + 0.8 * np.sin(0.9 * x)
ftrue = f(grid)
peak_true_x = grid[np.argmax(ftrue)]; peak_true_h = ftrue.max()


def fit(x, y, frac, xv):
    return lowess(y, x, frac=frac, it=0, xvals=xv)


rows = []; cvsel = []
for r in range(REPS):
    x = np.sort(rng.uniform(0, 10, N)); y = f(x) + rng.normal(0, SD, N)
    for s in SPANS:
        fh = fit(x, y, s, grid)
        rows.append((r, s, np.sqrt(np.nanmean((fh - ftrue) ** 2)), np.nanmax(fh[(grid > 2) & (grid < 4)]), grid[np.nanargmax(np.where((grid > 2) & (grid < 4), fh, -np.inf))]))
    if r < 100:  # 交差検証は100回分
        fold = rng.permutation(N) % 5
        cve = []
        for s in SPANS:
            e = []
            for k in range(5):
                tr = fold != k
                p = fit(x[tr], y[tr], s, x[~tr])
                e.append(np.nanmean((p - y[~tr]) ** 2))
            cve.append(np.mean(e))
        best = SPANS[int(np.argmin(cve))]
        rmse_best = [rw[2] for rw in rows if rw[0] == r and rw[1] == best][0]
        oracle = min(rw[2] for rw in rows if rw[0] == r)
        cvsel.append((r, best, rmse_best, oracle))
R = pd.DataFrame(rows, columns=["rep", "span", "rmse", "peak_h", "peak_x"])
CV = pd.DataFrame(cvsel, columns=["rep", "span_cv", "rmse_cv", "rmse_oracle"])
S = R.groupby("span").agg(rmse=("rmse", "mean"), peak_h=("peak_h", "mean"), peak_h_sd=("peak_h", "std"),
                          peak_x_abs_err=("peak_x", lambda v: np.mean(np.abs(v - peak_true_x)))).reset_index()
S["peak_h_pct"] = S.peak_h / peak_true_h * 100
S.round(4).to_csv(RES / "summary.csv", index=False)
CV.round(4).to_csv(RES / "cv_choice.csv", index=False)
best_span = float(S.span[S.rmse.idxmin()])
gS = lambda s, c: float(S[S.span == s][c].iloc[0])
out = {"n": N, "noise_sd": SD, "reps": REPS, "spans": SPANS, "true_peak_height": round(float(peak_true_h), 2), "true_peak_x": round(float(peak_true_x), 2),
       "rmse_by_span": {str(s): round(gS(s, "rmse"), 3) for s in SPANS},
       "peak_height_pct_by_span": {str(s): round(gS(s, "peak_h_pct"), 1) for s in SPANS},
       "peak_x_abs_err_by_span": {str(s): round(gS(s, "peak_x_abs_err"), 2) for s in SPANS},
       "best_span_by_mean_rmse": best_span, "best_rmse": round(gS(best_span, "rmse"), 3),
       "rmse_span_0_75_vs_best_ratio": round(gS(0.75, "rmse") / gS(best_span, "rmse"), 2),
       "rmse_span_0_05_vs_best_ratio": round(gS(0.05, "rmse") / gS(best_span, "rmse"), 2),
       "cv_reps": len(CV), "cv_span_counts": {str(k): int(v) for k, v in CV.span_cv.value_counts().sort_index().items()},
       "cv_rmse_mean": round(float(CV.rmse_cv.mean()), 3), "oracle_rmse_mean": round(float(CV.rmse_oracle.mean()), 3)}
json.dump(out, open(RES / "a757_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1回分のデータと3つの span
rng2 = np.random.default_rng(7570)
x = np.sort(rng2.uniform(0, 10, N)); y = f(x) + rng2.normal(0, SD, N)
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.scatter(x, y, s=8, color=GRAY, alpha=0.6, label="データ（200点）")
ax.plot(grid, ftrue, color="k", lw=2, label="本当の曲線")
for s, c in [(0.05, ORANGE), (best_span, GREEN), (0.75, BLUE)]:
    ax.plot(grid, fit(x, y, s, grid), color=c, lw=1.8, label=f"span {s}")
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper right")
ax.set_ylim(-2.2, 4.2)
ax.set_title("span が小さいとぎざぎざ、大きいと山がつぶれる")
save(fig, "a757_example.png", SRC)
# 図2：誤差と山の高さ
fig, ax1 = plt.subplots(figsize=(8, 3.8))
ax1.plot(S.span, S.rmse, marker="o", color=BLUE, label="本当の曲線との誤差（RMSE、左）")
ax1.set_xlabel("span（近くの点として使う割合）"); ax1.set_ylabel("RMSE", color=BLUE)
ax2 = ax1.twinx(); ax2.plot(S.span, S.peak_h_pct, marker="s", color=ORANGE, label="山の高さの再現（%、右）")
ax2.axhline(100, color=ORANGE, lw=0.8, ls=":"); ax2.set_ylabel("山の高さ（本当の高さに対する%）", color=ORANGE)
ax2.spines["right"].set_visible(True)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper center")
ax1.set_title(f"誤差がいちばん小さいのは span {best_span}。0.75 では山が{100 - gS(0.75, "peak_h_pct"):.0f}%低くなる")
save(fig, "a757_tradeoff.png", SRC)
# 図3：交差検証で選んだ span
fig, ax = plt.subplots(figsize=(7.5, 3.6))
cnt = CV.span_cv.value_counts().reindex(SPANS, fill_value=0)
ax.bar([str(s) for s in SPANS], cnt.values, color=[GREEN if s == best_span else LIGHT for s in SPANS])
ax.set_xlabel("交差検証で選ばれた span"); ax.set_ylabel("回数（100回のうち）")
ax.set_title(f"交差検証で選ぶと誤差は平均{out['cv_rmse_mean']}（その回でいちばんよい span なら{out['oracle_rmse_mean']}）", fontsize=12)
save(fig, "a757_cv.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
