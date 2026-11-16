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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本銀行「全国企業短期経済観測調査」、内閣府「四半期別GDP速報」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(ROOT / "data" / "panel_quarterly.csv")
c = "TK99F0000601GCQ00000"
d["dDI"] = d[c] - d[c].shift(1)
CRISIS = {(2008, 4), (2009, 1), (2009, 2), (2020, 1), (2020, 2), (2020, 3), (2020, 4)}
d["crisis"] = [(y, q) in CRISIS for y, q in zip(d.year, d.q)]
s = d[(d.year + (d.q - 1) / 4 >= 1994.5)].dropna(subset=["dDI", "gdp_latest"])

# ---- 図1：散布図 --------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.2, 5.2))
n = s[~s.crisis]; k = s[s.crisis]
ax.scatter(n.dDI, n.gdp_latest, s=26, color=C[0], edgecolor="#fcfcfb", lw=1.2, label="ふだんの四半期")
ax.scatter(k.dDI, k.gdp_latest, s=40, color=C[1], edgecolor="#fcfcfb", lw=1.2, marker="D", label="2008〜09年・2020年の大きな落ち込みの期")
for _, rw in k.iterrows():
    ax.text(rw.dDI + 0.6, rw.gdp_latest, f"{int(rw.year)}年{int(rw.q)}期", fontsize=8.3, color=INK2, va="center")
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("短観の業況判断DI（全規模全産業）の前期差（ポイント）")
ax.set_ylabel("実質GDPの前期比（%、最新の値）")
ax.set_xlim(-29, 18)
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"同じ期のDIの変化とGDPは相関{main['crosscorr_dDI_y_lead_k']['0']:.2f}（落ち込みの期を除くと{main['corr_lag0_excl_crisis']:.2f}）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：1994年7-9月期〜2026年4-6月期。GDP は2026年4-6月期2次速報の時点の値。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_scatter_ddi_gdp.png")

# ---- 図2：ずらし相関 ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.2, 4.8))
ks = [-2, -1, 0, 1, 2]
x = np.arange(5); w = 0.36
v1 = [main["crosscorr_dDI_y_lead_k"][str(k)] for k in ks]; v2 = [main["crosscorr_excl_crisis"][str(k)] for k in ks]
ax.bar(x - w / 2, v1, width=w - 0.02, color=C[0], label="全期間")
ax.bar(x + w / 2, v2, width=w - 0.02, color=C[2], label="大きな落ち込みの期を除く")
for xi, a, b in zip(x, v1, v2):
    ax.text(xi - w / 2, a + 0.015, f"{a:.2f}", ha="center", fontsize=8.8, color=INK)
    ax.text(xi + w / 2, b + 0.015, f"{b:.2f}", ha="center", fontsize=8.8, color=INK)
ax.set_xticks(x, ["2期前のGDP", "1期前のGDP", "同じ期のGDP", "1期後のGDP", "2期後のGDP"])
ax.set_ylabel("DIの前期差との相関")
ax.set_ylim(0, 0.8)
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("DIの変化がいちばん合うのは、同じ期のGDP", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：全規模全産業。1994年7-9月期〜2026年4-6月期。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
save(fig, "fig2_crosscorr.png")

# ---- 図3：予測の誤差 ---------------------------------------------------------------------
cases = [("oos_latest_2008_2026", "最新のGDP\n全期間"), ("oos_latest_2008_2026_excl_crisis", "最新のGDP\n落ち込みの期を除く"),
         ("oos_first_2008_2026", "1次速報\n全期間"), ("oos_first_2008_2026_excl_crisis", "1次速報\n落ち込みの期を除く")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(4); w = 0.36
a = [main[k]["rmse_ar"] for k, _ in cases]; b = [main[k]["rmse_ardi"] for k, _ in cases]
ax.bar(x - w / 2, a, width=w - 0.02, color=INK2, label="前の期のGDPだけで予測")
ax.bar(x + w / 2, b, width=w - 0.02, color=C[0], label="＋同じ期のDIの変化")
for xi, (k, _) in zip(x, cases):
    ax.text(xi + w / 2, main[k]["rmse_ardi"] + 0.03, f"−{main[k]['improve_pct']:.0f}%", ha="center", fontsize=9.5, color=INK)
ax.set_xticks(x, [lab for _, lab in cases], fontsize=9.5)
ax.set_ylabel("予測の誤差（RMSE、%ポイント）")
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"落ち込みの期を除くと、1次速報への上乗せは{main['oos_first_2008_2026_excl_crisis']['improve_pct']:.0f}%だけ（最新のGDPでは{main['oos_latest_2008_2026_excl_crisis']['improve_pct']:.0f}%）", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：2008年1-3月期〜2026年4-6月期を、その時点より前のデータだけで推定し直しながら1期ずつ予測（拡張窓）。数字は誤差の縮み。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_oos_rmse.png")

# ---- 図4：問い直し（改定とDI） -------------------------------------------------------------
rv = pd.read_csv(R / "requestion_revisions.csv")
q = rv[~rv.crisis]
fig, ax = plt.subplots(figsize=(8.2, 5.0))
ax.scatter(q.dDI, q.rev, s=26, color=C[0], edgecolor="#fcfcfb", lw=1.2)
bb = np.polyfit(q.dDI, q.rev, 1); xs = np.linspace(q.dDI.min(), q.dDI.max(), 10)
ax.plot(xs, bb[1] + bb[0] * xs, color=INK2, lw=1.5, ls="--")
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("短観の業況判断DI（全規模全産業）の前期差（ポイント）")
ax.set_ylabel("あとで直された分（最新 − 1次速報、%ポイント）")
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
e = req["excl_crisis"]
ax.set_title(f"DIが上がった期ほど、GDPはあとで上に直された（相関{e['corr_rev_dDI']:.2f}）", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：2004年1-3月期〜2026年4-6月期のうち大きな落ち込みの期を除く{e['n']}期。破線は単純な回帰直線。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.11, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_revision_vs_ddi.png")
print("figures done")
