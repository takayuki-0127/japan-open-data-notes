"""142：主要耐久消費財の普及率はどんなS字を描いたか（ロジスティック曲線の当てはめ）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from common import *

d = load()
d.to_csv(DATA / "fukyuritsu.csv")
ITEMS = {"ルームエアコン": "ルームエアコン", "温水洗浄便座": "温水洗浄便座", "洗髪洗面化粧台": "洗髪洗面化粧台",
         "システムキッチン": "システムキッチン", "パソコン": "パソコン", "乗用車_全体": "乗用車",
         "テレビ_薄型（液晶、ﾌﾟﾗｽﾞﾏ等）": "薄型テレビ", "携帯電話_スマートフォン": "スマートフォン",
         "食器洗い機": "食器洗い機", "タブレット型端末": "タブレット型端末"}
rows, fits = [], {}
for col, name in ITEMS.items():
    full = d[col].dropna()
    s = full.loc[:full.idxmax()] if full.iloc[-1] < full.max() - 2 else full   # ピーク後に下がった品目は、ピークまでで当てはめる
    t = s.index.values.astype(float); y = s.values
    p0 = [min(100, y.max() * 1.05), 0.3, t[np.argmin(abs(y - y.max() / 2))]]
    try:
        (K, r, t0), cov = curve_fit(logistic, t, y, p0=p0, bounds=([y.max() * 0.9, 0.01, 1900], [100, 3, 2100]), maxfev=20000)
    except RuntimeError:
        continue
    pred = logistic(t, K, r, t0); rmse = float(np.sqrt(np.mean((y - pred) ** 2)))
    se = np.sqrt(np.diag(cov))
    first50 = full[full >= 50].index.min() if (full >= 50).any() else None
    peak_y, peak_v = int(full.idxmax()), float(full.max())
    rows.append({"item": name, "from": int(t.min()), "fit_to": int(t.max()), "first": float(y[0]), "latest": float(full.iloc[-1]),
                 "covers_takeoff": bool(y[0] < 0.25 * K),
                 "peak_year": peak_y, "peak": peak_v, "K": K, "K_se": se[0], "r": r, "t0_half_of_K": t0,
                 "years_10_to_90pct_of_K": 4.394 / r, "first_year_ge_50pct": first50, "rmse": rmse})
    fits[name] = (full, K, r, t0)
res = pd.DataFrame(rows).round(3)
res.to_csv(RES / "a142_logistic_fit.csv", index=False)
print(res.to_string())

# 図1：観測値と当てはめ（6品目）
show = ["ルームエアコン", "乗用車", "温水洗浄便座", "パソコン", "薄型テレビ", "食器洗い機"]
fig, axes = plt.subplots(2, 3, figsize=(10, 5.6), sharey=True)
for ax, name in zip(axes.flat, show):
    s, K, r, t0 = fits[name]
    tt = np.linspace(s.index.min() - 3, 2040, 300)
    ax.plot(tt, logistic(tt, K, r, t0), color=GRAY, lw=1.2, ls="--")
    ax.plot(s.index, s.values, color=BLUE, lw=2)
    ax.axhline(K, color=ORANGE, lw=0.8, ls=":")
    ax.set_title(f"{name}（上限{K:.0f}%）", fontsize=11, loc="left")
    ax.set_ylim(0, 105); ax.set_xlim(s.index.min() - 3, 2040)
    ax.tick_params(labelsize=8)
axes[0, 0].set_ylabel("普及率（％）"); axes[1, 0].set_ylabel("普及率（％）")
fig.suptitle("普及率（青）とロジスティック曲線（灰の点線）", x=0.02, ha="left", fontsize=13)
fig.text(0.0, -0.01, SOURCE + "。二人以上の世帯、各年3月末（1976年までは2月末）", fontsize=7.5, color=GRAY)
fig.tight_layout(); fig.savefig(FIG / "a142_curves.png"); plt.close(fig)

# 図2：上限と広がる速さ
r2 = res[res.covers_takeoff].sort_values("years_10_to_90pct_of_K")
fig, ax = plt.subplots(figsize=(8.6, 4.4))
y = np.arange(len(r2))
ax.barh(y, r2["years_10_to_90pct_of_K"], color=BLUE, height=0.6)
for i, (_, z) in enumerate(r2.iterrows()):
    ax.text(z["years_10_to_90pct_of_K"] + 0.5, i, f"{z['years_10_to_90pct_of_K']:.0f}年　上限{z['K']:.0f}%", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(r2["item"]); ax.invert_yaxis()
ax.set_xlabel("上限の10%から90%まで広がるのにかかる年数（当てはめ）")
ax.set_title("広がる速さと上限（普及の初期から記録がある品目）", loc="left")
ax.set_xlim(0, r2["years_10_to_90pct_of_K"].max() * 1.35)
fig.text(0.0, -0.03, SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a142_speed.png"); plt.close(fig)

# 図3：ピークの後に下がった品目
down = {"デジタルカメラ": "デジタルカメラ", "パソコン": "パソコン", "乗用車_全体": "乗用車",
        "テレビ_薄型（液晶、ﾌﾟﾗｽﾞﾏ等）": "薄型テレビ"}
drows = []
fig, ax = plt.subplots(figsize=(8.6, 4.2))
colors = [ORANGE, BLUE, GREEN, PURPLE, GRAY]
for (col, name), c in zip(down.items(), colors):
    s = d[col].dropna().loc[2000:]
    ax.plot(s.index, s.values, color=c, lw=2, label=name)
    full = d[col].dropna()
    drows.append({"item": name, "peak_year": int(full.idxmax()), "peak": float(full.max()), "latest_year": int(full.index.max()),
                  "latest": float(full.iloc[-1]), "change_pt": float(full.iloc[-1] - full.max())})
ax.axvline(2013.5, color=GRAY, lw=0.6, ls=":"); ax.text(2013.6, 22, "2013年4月\n調査方法の変更", fontsize=8, color=GRAY)
ax.axvline(2018.8, color=GRAY, lw=0.6, ls=":"); ax.text(2018.9, 22, "2018年10月\n郵送・オンライン", fontsize=8, color=GRAY)
ax.set_ylabel("普及率（％）"); ax.set_ylim(0, 105)
ax.set_title("ピークの後に下がった品目（2000〜2026年）", loc="left")
ax.legend(frameon=False, ncol=4, fontsize=9, loc="lower left")
fig.text(0.0, -0.03, SOURCE + "。点線は調査方法の変更（2013年4月、2018年10月）", fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a142_decline.png"); plt.close(fig)
dd = pd.DataFrame(drows); dd.to_csv(RES / "a142_peak_and_decline.csv", index=False); print(dd.to_string())
