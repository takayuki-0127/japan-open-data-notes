"""04 図：figures/ に PNG を6枚。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parents[1]
R, F, P = ROOT / "results", ROOT / "figures", ROOT / "data" / "processed"
F.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "savefig.dpi": 160})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK2 = "#52514e"
top = pd.read_csv(R / "top10_adjusted.csv")
ev = pd.read_csv(R / "events_adjusted.csv")
ann = pd.read_csv(R / "annual_fy.csv")
pr = pd.read_csv(P / "deflator.csv")
dw = pd.read_csv(P / "dwellings.csv")
rob = pd.read_csv(R / "robustness.csv")
S = json.load(open(R / "summary.json"))
cut = S["big_events"]["住宅総合デフレーター"][0]

def save(fig, name):
    fig.savefig(F / name, bbox_inches="tight"); plt.close(fig)

# 図1 上位10事故：名目と、物価・住宅数で割り引いた値
t = top.sort_values("event_ym").reset_index(drop=True)
lab = [f"{n}（{y[:4]}）" for n, y in zip(t.name, t.event_ym)]
col = [C[0] if f <= 2004 else C[1] for f in t.fy]
fig, ax = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
y = np.arange(len(t))[::-1]
ax[0].barh(y, t.tot_oku, color=col, height=0.62)
for yy, v in zip(y, t.tot_oku): ax[0].text(v + 150, yy, f"{v:,.0f}", va="center", fontsize=9, color=INK2)
ax[0].set_yticks(y, lab); ax[0].set_title("名目の支払保険金（億円）", loc="left", fontsize=12)
ax[0].set_xlim(0, 12500)
ax[1].barh(y, t.yen_per_dwelling, color=col, height=0.62)
for yy, v in zip(y, t.yen_per_dwelling): ax[1].text(v + 250, yy, f"{v:,.0f}", va="center", fontsize=9, color=INK2)
ax[1].set_title("建設費（2020年度価格）で直し、住宅1戸あたり（円）", loc="left", fontsize=12)
ax[1].set_xlim(0, 20500)
for a in ax: a.grid(axis="y", visible=False)
from matplotlib.patches import Patch
fig.legend(handles=[Patch(color=C[0], label="1991〜2004年の事故"), Patch(color=C[1], label="2014年以降の事故")], loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.04))
fig.suptitle("名目では1位が3位の1.9倍。割り引くと1.14倍まで縮む", x=0.01, ha="left", fontsize=14)
save(fig, "fig1_top10_nominal_vs_adjusted.png")

# 図2 物価と住宅数（1991年度=1）
p = pr[(pr.fy >= 1991) & (pr.fy <= 2025)].copy()
yrs = np.arange(1991, 2026)
dwi = np.interp(yrs + 0.5, dw.year + 0.75, dw.dwellings)
last = dw.dwellings.iloc[-1]; slope = (dw.dwellings.iloc[-1] - dw.dwellings.iloc[-2]) / 5
dwi = np.where(yrs + 0.5 > 2023.75, last + slope * (yrs + 0.5 - 2023.75), dwi)
fig, ax = plt.subplots(figsize=(9, 4.8))
series = [("建設工事費デフレーター（住宅総合）", p.defl_house.values / p.defl_house.values[0], C[0]),
          ("消費者物価指数（総合）", p.cpi_all.values / p.cpi_all.values[0], C[1]),
          ("住宅数（全国）", dwi / dwi[0], C[2])]
for n, v, c in series:
    ax.plot(p.fy, v, color=c, lw=2, label=n)
    ax.text(2025.4, v[-1], f"{n} {v[-1]:.2f}", color="#0b0b0b", va="center", fontsize=9.5)
ax.axhline(1, color=INK2, lw=0.8)
ax.set_xlim(1990, 2025); ax.set_ylabel("1991年度＝1")
ax.legend(frameon=False, loc="upper left")
ax.set_title("割り引くものさし：住宅数は1.49倍、建設費は1.46倍、物価全体は1.21倍に", loc="left", fontsize=13)
save(fig, "fig2_price_and_dwellings.png")

# 図3 大きな事故の年表（住宅1戸あたり実質）
fig, ax = plt.subplots(figsize=(10, 4.8))
x = t.event_ym.str[:4].astype(int) + (t.event_ym.str[5:7].astype(int) - 0.5) / 12
big = t.yen_per_dwelling >= cut
ax.axhspan(cut, 20500, color="#f0efec", zorder=0)
ax.axhline(cut, color=INK2, lw=1, ls="--")
ax.text(1991.2, cut + 300, f"ここより上（{cut:,}円／戸以上）は上位10表に必ず入る＝取りこぼしなし", fontsize=9.5, color=INK2)
ax.scatter(x[big], t.yen_per_dwelling[big], s=70, color=C[1], zorder=3, edgecolor="#fcfcfb", linewidth=1.5)
ax.scatter(x[~big], t.yen_per_dwelling[~big], s=55, color="#b9b8b2", zorder=3, edgecolor="#fcfcfb", linewidth=1.5)
OFF = {"平成30年台風21号": (-0.4, -150, "right"), "平成27年台風15号": (-0.4, -150, "right"), "平成30年7月豪雨": (0.4, -350, "left")}
for xx, yy, n in zip(x, t.yen_per_dwelling, t.name):
    dx, dy, ha = OFF.get(n, (0.3, 250, "left"))
    ax.text(xx + dx, yy + dy, n, fontsize=8.5, color="#0b0b0b", ha=ha)
ax.axvline(2013.25, color=INK2, lw=0.8)
ax.text(2001.5, 19700, "1991〜2012年度：22年で3件", ha="center", fontsize=10.5)
ax.text(2019.6, 19700, "2013〜2025年度：13年で5件", ha="center", fontsize=10.5)
ax.set_xlim(1990, 2026.5); ax.set_ylim(0, 20500)
ax.set_ylabel("実質保険金／住宅1戸（円）")
ax.set_title("大きな事故は3件→5件と多いが、件数が少なく偶然と区別できない（片側 p=0.13）", loc="left", fontsize=12.5)
save(fig, "fig3_big_events_timeline.png")

# 図4 2012〜2025年度：年度合計（住宅1戸あたり実質）
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.bar(ann.fy, ann.yen_per_dwelling, color=C[0], width=0.62)
for f_, v in zip(ann.fy, ann.yen_per_dwelling):
    ax.text(f_, v + 300, f"{v:,.0f}", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(ann.fy, [str(v) for v in ann.fy], fontsize=9.5)
ax.set_ylabel("実質保険金／住宅1戸（円）"); ax.set_xlabel("年度（協会が個別に調べた自然災害の合計）")
ax.grid(axis="x", visible=False)
ax.set_title(f"14年度分のうち2018・2019年度だけで合計の{(ann.real_yen[ann.fy.isin([2018, 2019])].sum() / ann.real_yen.sum()) * 100:.0f}%。右肩上がりではない（ケンドールのτ={S['annual_tau_pd'][0]:+.2f}）", loc="left", fontsize=12)
save(fig, "fig4_annual_fy2012_2025.png")

# 図5 件数（頻度）と1件あたり（重さ）
grp = {"台風": C[0], "大雨": C[1], "雪": C[2]}
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for per, c in list(grp.items()) + [("その他", C[3])]:
    d = ev[ev.peril == per] if per != "その他" else ev[~ev.peril.isin(grp)]
    ax.scatter(d.claims_per_1000, d.real_man_per_claim, s=np.sqrt(d.real_oku) * 4 + 12, color=c, alpha=0.85, label=per,
               edgecolor="#fcfcfb", linewidth=1.5, zorder=3)
old = top[top.fy <= 2004]
ax.scatter(old.claims_per_1000, old.real_man_per_claim, s=np.sqrt(old.real_oku) * 4 + 12, facecolor="none", edgecolor=INK2, linewidth=1.5, label="1991〜2004年の上位事故（参考）", zorder=3)
lbl = {"平成30年台風21号": "2018 台風21号", "令和元年台風19号（東日本台風）": "2019 台風19号", "平成30年7月豪雨": "2018 7月豪雨",
       "令和6年4月16日の降雹（兵庫県中心）": "2024 ひょう", "2014年2月の大雪": "2014 2月雪"}
POS = {"2018 7月豪雨": (1.15, 0), "2019 台風19号": (1.12, 0), "2018 台風21号": (1.12, 0), "2014 2月雪": (0.82, 8), "2024 ひょう": (1.12, -6)}
for _, r in ev[ev.title.isin(lbl)].iterrows():
    mx, dy = POS[lbl[r.title]]
    ax.text(r.claims_per_1000 * mx, r.real_man_per_claim + dy, lbl[r.title], fontsize=8.5, va="center", ha="left" if mx > 1 else "right")
ax.text(14, 95, "白抜き：1991・1999・2004年の台風", fontsize=8.5, color=INK2, ha="center")
ax.set_xscale("log"); ax.set_xlim(0.008, 60); ax.set_xlabel("支払件数／住宅1,000戸（対数目盛）"); ax.set_ylabel("1件あたり実質保険金（万円）")
from matplotlib.ticker import FuncFormatter
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
ax.legend(frameon=False, fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1), markerscale=0.6)
ax.set_title("1件あたりの重さを決めるのは時代より災害の種類：大雨（浸水）は台風（風）の約2倍", loc="left", fontsize=12)
save(fig, "fig5_frequency_vs_severity.png")

# 図6 頑健性
r6 = rob.iloc[:8].copy()
names = ["基準", "建設総合デフレーター", "CPI総合", "CPI（帰属家賃除く）", "割り引かない", "住宅数を階段で", "世帯数で割る", "火災・新種だけ"]
names2 = names + ["自動車だけ", "14年間の上位1事故を除く", "上位2事故を除く", "名目100億円以上の事故だけ"]
fig, ax = plt.subplots(1, 2, figsize=(11.5, 5.2))
yy = np.arange(len(r6))[::-1]
ax[0].scatter(r6.top10_new_over_old_max, yy, s=70, color=C[0], zorder=3)
ax[0].axvline(1, color=INK2, lw=1)
for v, y_ in zip(r6.top10_new_over_old_max, yy): ax[0].text(v + 0.02, y_ + 0.18, f"{v:.2f}", fontsize=9)
ax[0].set_yticks(yy, names); ax[0].set_xlim(0.8, 1.45); ax[0].set_ylim(-0.6, len(r6) - 0.4)
ax[0].set_title("最大の事故どうし（2018台風21号÷1991台風19号）", loc="left", fontsize=11)
y2 = np.arange(len(rob))[::-1]
cc = [C[1]] * 8 + [C[3]] * (len(rob) - 8)
ax[1].scatter(rob.halves_ratio, y2, s=70, color=cc, zorder=3)
ax[1].axvline(1, color=INK2, lw=1)
for v, y_ in zip(rob.halves_ratio, y2): ax[1].text(v + 0.02, y_ + 0.18, f"{v:.2f}", fontsize=9)
ax[1].set_yticks(y2, names2); ax[1].set_xlim(0.5, 1.35)
ax[1].set_title("年度合計の後半÷前半（2019〜25 ÷ 2012〜18年度）", loc="left", fontsize=11)
for a in ax: a.grid(axis="y", visible=False)
fig.suptitle("最大の事故どうしは1.1〜1.3倍で安定。年度合計の前後比は、1つの事故を抜くだけで逆転する", x=0.01, ha="left", fontsize=13)
fig.tight_layout()
save(fig, "fig6_robustness.png")
print(sorted(p_.name for p_ in F.glob("*.png")))
