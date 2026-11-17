"""04 図：fig1〜fig4 → figures/（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, save, style, C, INK2

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES, FIG, DATA = ROOT / "results", ROOT / "figures", ROOT / "data"
FIG.mkdir(exist_ok=True)
SRC = "出典：国土交通省「不動産価格指数（住宅）」（季節調整値、2010年平均＝100）、総務省「消費者物価指数」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
yr = pd.read_csv(RES / "annual_index_sa.csv")
g = pd.read_csv(RES / "growth_by_area.csv")

# 図1：全国の年平均
fig, ax = plt.subplots(figsize=(8, 4.8))
years = [str(y) for y in range(2009, 2026)]
col = {"マンション": C[1], "住宅地": C[2], "戸建住宅": C[0]}
for t in ["マンション", "戸建住宅", "住宅地"]:
    v = yr[(yr.area == "全国") & (yr.type == t)][years].values[0]
    ax.plot(range(2009, 2026), v, color=col[t], lw=2.2, marker="o", ms=3)
    dy = {"マンション": 0, "戸建住宅": 4, "住宅地": -3}[t]
    ax.text(2025.3, v[-1] + dy, f"{t} {v[-1]:.0f}", color=col[t], va="center", fontsize=10)
cpi = pd.read_csv(DATA / "cpi_monthly.csv")
cpi["year"] = cpi.month.str[:4].astype(int)
ca = cpi.groupby("year").cpi.mean()
ca = 100 * ca / ca[2010]
ax.plot(ca.loc[2009:2025].index, ca.loc[2009:2025].values, color=INK2, lw=1.4, ls="--")
ax.text(2025.3, ca[2025] - 10, f"消費者物価 {ca[2025]:.0f}", color=INK2, va="center", fontsize=9.5)
ax.set_xlim(2008.5, 2028.8)
ax.set_xticks(range(2009, 2026, 2))
ax.set_ylabel("指数（2010年平均＝100）")
ax.set_title("全国：マンションは2013年から2倍、戸建住宅は物価とほぼ同じ伸び", loc="left", fontsize=12)
style(ax)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.17)
save(fig, FIG / "fig1_national_by_type.png", SRC, "年平均。消費者物価は総合を2010年平均＝100に直したもの（点線）")

# 図2：地域別の伸び（北から南、圏・都府県は後ろ）
fig, ax = plt.subplots(figsize=(8, 6.4))
areas = g["area"].tolist()
y = np.arange(len(areas))[::-1]
ax.scatter(g["マンション_名目"], y, color=C[1], s=36, label="マンション（名目）", zorder=3)
ax.scatter(g["戸建住宅_名目"], y, color=C[0], s=36, label="戸建住宅（名目）", zorder=3)
ax.scatter(g["戸建住宅_実質"], y, facecolors="none", edgecolors=C[0], s=36, label="戸建住宅（実質）", zorder=3)
for yi, a, b in zip(y, g["戸建住宅_実質"], g["マンション_名目"]):
    ax.plot([a, b], [yi, yi], color="#d0cfca", lw=1, zorder=1)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(y)
ax.set_yticklabels(areas)
ax.axhline(y[9] - 0.5, color="#d0cfca", lw=0.8, ls=":")
ax.set_xlabel("2013年平均→2025年平均の伸び（%）")
ax.set_title(f"どの地域もマンションの伸びが大きい。戸建住宅の実質の伸びは{M['real_detached_range'][0]:.0f}〜+{M['real_detached_range'][1]:.0f}%", loc="left", fontsize=12)
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color="#e4e3df", lw=0.8); ax.set_axisbelow(True)
fig.subplots_adjust(left=0.17, right=0.97, top=0.93, bottom=0.14)
save(fig, FIG / "fig2_growth_by_area.png", SRC, "実質＝消費者物価（総合）で割り引いた値。地域は北から南、点線の下は三大都市圏と東京都・愛知県・大阪府")

# 図3：底の月
def ym(s):
    a, b = map(int, s.split("-")); return a + (b - 0.5) / 12
fig, ax = plt.subplots(figsize=(8, 6.2))
for yi, (_, r) in zip(y, g.iterrows()):
    a, b = ym(r["底の月_マンション"]), ym(r["底の月_戸建住宅"])
    ax.plot([a, b], [yi, yi], color="#d0cfca", lw=1.2, zorder=1)
    ax.scatter(a, yi, color=C[1], s=36, zorder=3)
    ax.scatter(b, yi, color=C[0], s=36, zorder=3)
ax.scatter([], [], color=C[1], label="マンションの底"); ax.scatter([], [], color=C[0], label="戸建住宅の底")
ax.set_yticks(y); ax.set_yticklabels(areas)
ax.axhline(y[9] - 0.5, color="#d0cfca", lw=0.8, ls=":")
ax.set_xlim(2008.5, 2019.5)
ax.set_xlabel("12か月移動平均がいちばん低かった月（2009年以降）")
ax.set_title(f"マンションは2009〜10年に底を打ち、戸建住宅は多くの地域で数年遅れた", loc="left", fontsize=12)
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color="#e4e3df", lw=0.8); ax.set_axisbelow(True)
fig.subplots_adjust(left=0.17, right=0.97, top=0.93, bottom=0.14)
save(fig, FIG / "fig3_trough_timing.png", SRC, "季節調整値の中心化12か月移動平均の最小の月")

# 図4：問い直し（長い系列）
lr = pd.read_csv(RES / "requestion_long_series.csv")
fig, axes = plt.subplots(1, 3, figsize=(9, 4.2), sharey=True)
for ax, ar in zip(axes, ["東京都", "愛知県", "大阪府"]):
    s = lr[(lr.area == ar) & (lr.type == "戸建住宅")]
    ax.plot(s.year, s.index_sa, color=C[0], lw=2, label="戸建住宅")
    c = yr[(yr.area == ar) & (yr.type == "マンション")][years].values[0]
    ax.plot(range(2009, 2026), c, color=C[1], lw=2, label="マンション")
    r = M["requestion"][f"{ar}_戸建住宅"]
    ax.set_title(f"{ar}：戸建は{r['山の年']}年の山の{r['2025は山の%']:.0f}%", fontsize=10.5, loc="left")
    style(ax)
axes[0].set_ylabel("指数（2010年平均＝100）")
axes[0].legend(frameon=False, fontsize=9, loc="upper right")
fig.suptitle("問い直し：戸建住宅は1990年前後の山には戻っていない", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.2, wspace=0.08)
SRC4 = ("出典：国土交通省「不動産価格指数（住宅）」（季節調整値）。\n2008年3月以前（愛知県・大阪府は2006年11月以前）は国土交通省のほか"
        "（公社）東京都・愛知県・大阪府不動産鑑定士協会。いずれもこれをもとに作成者が加工して作成")
fig.subplots_adjust(bottom=0.27)
save(fig, FIG / "fig4_requestion_long.png", SRC4, "年平均。東京都・愛知県・大阪府は戸建住宅と住宅地だけ1984年4月から公表。マンションは2008年4月から")
print("ok")
