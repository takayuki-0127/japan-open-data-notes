"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本銀行「外国為替市況」、財務省「国債金利情報」、米国財務省 Daily Treasury Par Yield Curve Rates をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.4, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
m = pd.read_csv(ROOT / "data" / "monthly.csv", index_col=0)
t = pd.to_datetime(m.index + "-15")

# 図1：水準（上下2段）
fig, (a1, a2) = plt.subplots(2, 1, figsize=(9, 6.4), sharex=True, gridspec_kw={"height_ratios": [1, 1]})
a1.plot(t, m.usdjpy_avg, color=INK, lw=1.6); a1.set_ylabel("ドル円（円/ドル、月中平均）")
a1.grid(axis="y", color=GRID, lw=0.8)
a2.plot(t, m.spread2, color=C[0], lw=1.6, label="2年")
a2.plot(t, m.spread10, color=C[1], lw=1.2, ls="--", label="10年")
a2.axhline(0, color=INK2, lw=0.8); a2.set_ylabel("金利差（米国−日本、%ポイント）")
a2.legend(frameon=False, loc="upper right", ncol=2); a2.grid(axis="y", color=GRID, lw=0.8)
a1.set_title("ドル円と日米の金利差（1990年1月〜2026年10月）", loc="left", fontsize=12.5, color=INK, pad=12)
fig.text(0.01, 0.01, SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.1, hspace=0.12)
save(fig, "fig1_levels.png")

# 図2：期間別の R²
per = pd.read_csv(R / "regression_by_period.csv")
P = ["1990〜1999", "2000〜2007", "2008〜2012", "2013〜2020", "2021〜2026", "全期間"]
x = np.arange(len(P))
fig, ax = plt.subplots(figsize=(9, 5.2))
for k, (sp, lab, c) in enumerate([("spread2", "2年の金利差", C[0]), ("spread10", "10年の金利差", C[1])]):
    v = [float(per[(per.period == p) & (per.spread == sp)].r2.iloc[0]) for p in P]
    ax.bar(x + (k - 0.5) * 0.38, v, width=0.38, color=c, label=lab)
    for i, vv in enumerate(v):
        ax.text(x[i] + (k - 0.5) * 0.38, vv + 0.008, f"{vv:.2f}", ha="center", fontsize=8.8)
ax.set_xticks(x, P); ax.set_ylim(0, 0.55); ax.set_ylabel("月ごとの変化の決定係数（R²）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "金利差で説明できる月々の動きの割合は、2008〜12年と2021年以降に大きかった")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.14)
save(fig, "fig2_r2_by_period.png")

# 図3：36か月の移動相関
rc = pd.read_csv(R / "rolling_corr36.csv", index_col=0)
tt = pd.to_datetime(rc.index + "-15")
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(tt, rc.corr36_spread2, color=C[0], lw=1.8, label="2年の金利差")
ax.plot(tt, rc.corr36_spread10, color=C[1], lw=1.1, ls="--", label="10年の金利差")
ax.fill_between(tt, rc.corr36_spread2, 0, where=rc.corr36_spread2 < 0, color=C[1], alpha=0.25, lw=0)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylim(-0.4, 0.9)
ax.set_ylabel("相関係数（直近36か月、月ごとの変化どうし）"); ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "月ごとの変化の相関が負になったのは、1996〜97年など短い時期だけ")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.12)
save(fig, "fig3_rolling_corr.png")

# 図4：2021年以降の累積（問い直し）
pa = pd.read_csv(R / "requestion_path.csv", index_col=0)
tp = pd.to_datetime(pa.index + "-15")
rq = main["requestion"]
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.plot(tp, pa.actual, color=INK, lw=2.4, label="ドル円の実際の変化")
ax.plot(tp, pa.fitted_in2021_26, color=C[0], lw=1.8, label=f"金利差で説明できる分（傾き {rq['beta_in_2021_26']:.1f}、2021〜26年で推定）")
ax.plot(tp, pa.fitted_pre2021, color=C[0], lw=1.4, ls="--", label=f"同（傾き {main['beta_pre2021']['beta']:.1f}、1990〜2020年で推定）")
sp = pd.Timestamp(rq["spread_peak_month"] + "-15")
ax.axvline(sp, color=INK2, lw=0.9, ls=":")
ax.text(sp, 47, f" 金利差が最も開いた月\n （{rq['spread_peak_month'][:4]}年{int(rq['spread_peak_month'][5:])}月）", fontsize=9, color=INK2, va="top")
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylim(-5, 50)
ax.set_ylabel("2021年1月からの変化（対数×100、円安が上）"); ax.legend(frameon=False, loc="upper left", fontsize=9)
finish(fig, ax, "2023年10月以降、金利差は縮んだが円安は続いた")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.12)
save(fig, "fig4_since_2021.png")
print("ok")
