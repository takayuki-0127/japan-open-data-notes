"""659 ARIMA の次数を AIC で選ぶと、本当の次数を何%で当て、予測はどれだけ悪くなるのか

本当の系列は ARMA(1,1)（φ=0.6、θ=0.4、雑音の標準偏差1、平均0）。長さ n=48・120・240（月次なら4年・10年・20年）。
候補は ARIMA(p,0,q)、p・q は0〜2の9通り（定数項あり）。AIC と BIC でいちばん小さいものを選ぶ。
選んだ次数・本当の次数・いつも AR(1) の3通りで12期先まで予測し、実際の値との誤差（RMSE）を比べる。
各長さ100回、seed 659。
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.arima_process import arma_generate_sample
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
warnings.filterwarnings("ignore")
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 659）"
rng = np.random.default_rng(659)
PHI, THETA, H, REPS = 0.6, 0.4, 12, 100
NS = [48, 120, 240]
ORDERS = [(p, q) for p in range(3) for q in range(3)]
rows = []
for n in NS:
    for r in range(REPS):
        y_all = arma_generate_sample([1, -PHI], [1, THETA], n + H, burnin=200, distrvs=rng.standard_normal)
        y, fut = y_all[:n], y_all[n:]
        fits = {}
        for o in ORDERS:
            try:
                fits[o] = ARIMA(y, order=(o[0], 0, o[1])).fit()
            except Exception:
                continue
        aic = {o: f.aic for o, f in fits.items()}; bic = {o: f.bic for o, f in fits.items()}
        oa, ob = min(aic, key=aic.get), min(bic, key=bic.get)
        rec = {"n": n, "rep": r, "aic_p": oa[0], "aic_q": oa[1], "bic_p": ob[0], "bic_q": ob[1]}
        for name, o in [("aic", oa), ("bic", ob), ("true", (1, 1)), ("ar1", (1, 0))]:
            fc = fits[o].forecast(H)
            err = fc - fut
            rec[f"rmse_{name}"] = float(np.sqrt(np.mean(err ** 2)))
            rec[f"e1_{name}"] = float(err[0] ** 2)
        rows.append(rec)
R = pd.DataFrame(rows); R.round(5).to_csv(RES / "reps.csv", index=False)
summ = {}
for n in NS:
    s = R[R.n == n]
    d = {"aic_hit_pct": round(float(((s.aic_p == 1) & (s.aic_q == 1)).mean() * 100), 1),
         "bic_hit_pct": round(float(((s.bic_p == 1) & (s.bic_q == 1)).mean() * 100), 1),
         "aic_more_params_pct": round(float(((s.aic_p + s.aic_q) > 2).mean() * 100), 1),
         "aic_fewer_params_pct": round(float(((s.aic_p + s.aic_q) < 2).mean() * 100), 1),
         "bic_fewer_params_pct": round(float(((s.bic_p + s.bic_q) < 2).mean() * 100), 1)}
    for k in ["aic", "bic", "true", "ar1"]:
        d[f"rmse12_{k}"] = round(float(s[f"rmse_{k}"].mean()), 4)
        d[f"rmse1_{k}"] = round(float(np.sqrt(s[f"e1_{k}"].mean())), 4)
    d["rmse12_aic_vs_true_pct"] = round((d["rmse12_aic"] / d["rmse12_true"] - 1) * 100, 2)
    d["rmse1_aic_vs_true_pct"] = round((d["rmse1_aic"] / d["rmse1_true"] - 1) * 100, 2)
    d["rmse1_ar1_vs_true_pct"] = round((d["rmse1_ar1"] / d["rmse1_true"] - 1) * 100, 2)
    summ[str(n)] = d
cnt = {str(n): R[R.n == n].groupby(["aic_p", "aic_q"]).size().to_dict() for n in NS}
out = {"true_order": [1, 1], "phi": PHI, "theta": THETA, "reps": REPS, "horizon": H, "by_n": summ,
       "aic_choice_counts": {n: {f"{p},{q}": int(v) for (p, q), v in c.items()} for n, c in cnt.items()}}
json.dump(out, open(RES / "a659_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame(summ).T.to_csv(RES / "summary.csv")

# 図1：当たる割合
fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(len(NS)); w = 0.35
a = [summ[str(n)]["aic_hit_pct"] for n in NS]; b = [summ[str(n)]["bic_hit_pct"] for n in NS]
ax.bar(x - w / 2, a, w, color=BLUE, label="AIC"); ax.bar(x + w / 2, b, w, color=ORANGE, label="BIC")
for i in range(len(NS)):
    ax.text(i - w / 2, a[i] + 1.5, f"{a[i]:.0f}%", ha="center", fontsize=9); ax.text(i + w / 2, b[i] + 1.5, f"{b[i]:.0f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{n}期" for n in NS]); ax.set_ylabel("本当の次数(1,1)を選んだ割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9); ax.set_title("系列が短いと、本当の次数はなかなか選ばれない")
save(fig, "a659_hit_rate.png", SRC)
# 図2：選ばれた次数の内訳（n=120、AIC）
c = R[R.n == 120].groupby(["aic_p", "aic_q"]).size()
grid = np.zeros((3, 3))
for (p, q), v in c.items():
    grid[p, q] = v
fig, ax = plt.subplots(figsize=(5.8, 4.4))
im = ax.imshow(grid, cmap="Blues")
for p in range(3):
    for q in range(3):
        ax.text(q, p, f"{int(grid[p, q])}", ha="center", va="center", fontsize=11, color="white" if grid[p, q] > grid.max() * 0.6 else "black")
ax.set_xticks(range(3)); ax.set_yticks(range(3)); ax.set_xlabel("MA の次数 q"); ax.set_ylabel("AR の次数 p")
ax.add_patch(plt.Rectangle((0.5, 0.5), 1, 1, fill=False, ec=ORANGE, lw=2.5))
ax.set_title("120期・AIC で選んだ次数（100回、枠が本当）", fontsize=11)
save(fig, "a659_choice_grid.png", SRC)
# 図3：予測の誤差
fig, ax = plt.subplots(figsize=(8.5, 3.8))
w = 0.2
for i, (k, col, lab) in enumerate([("true", GRAY, "本当の次数"), ("aic", BLUE, "AIC で選んだ次数"), ("bic", ORANGE, "BIC で選んだ次数"), ("ar1", LIGHT, "いつも AR(1)")]):
    v = [summ[str(n)][f"rmse1_{k}"] for n in NS]
    ax.bar(x + (i - 1.5) * w, v, w, color=col, label=lab)
ax.set_xticks(x); ax.set_xticklabels([f"{n}期" for n in NS]); ax.set_ylabel("1期先の予測の誤差（RMSE）"); ax.set_ylim(0.9, None)
ax.legend(frameon=False, fontsize=8.5, ncol=2); ax.set_title("次数を外しても、1期先の予測の悪化は小さい")
save(fig, "a659_forecast.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
