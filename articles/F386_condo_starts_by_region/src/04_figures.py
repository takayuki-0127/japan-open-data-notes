"""04 図（オフライン）：figures/ に PNG を4枚。日付を埋め込まない。"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888888", "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.8,
                     "svg.hashsalt": "20261116"})
C = ["#2a78d6", "#eb6834", "#1f9e74", "#8a5cc2"]
GRAY = "#555555"
SRC = "出典：国土交通省「建築着工統計調査」住宅着工統計（e-Stat）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))


def finish(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7.5, color=GRAY)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def shade(ax):
    for (a, b), lab in (((2005, 2007), "基準 2005〜07年"), ((2023, 2025), "直近 2023〜25年")):
        ax.axvspan(a - 0.5, b + 0.5, color="#f0f0f0", zorder=0)


def fig1():
    t = pd.read_csv(RES / "annual_by_metro.csv", index_col="year")
    groups = ["首都圏", "中部圏", "近畿圏", "地方圏"]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    shade(ax)
    bottom = np.zeros(len(t))
    for g, c in zip(groups, C):
        ax.bar(t.index, t[g] / 1e4, bottom=bottom, color=c, width=0.8, label=g, edgecolor="white", linewidth=0.6, zorder=2)
        bottom += t[g].values / 1e4
    ax.set_xlim(1987.3, 2025.7)
    ax.set_ylabel("着工戸数（万戸）")
    ax.set_title("分譲マンションの着工は2006年の23.9万戸が山、2025年は9.0万戸", loc="left", fontsize=12)
    n = M["national"]
    ax.text(2006, bottom.max() * 1.0 + 0.4, f"2005〜07年平均 {n['base_units']/1e4:.1f}万戸", ha="center", fontsize=9)
    ax.text(2024, 12.5, f"2023〜25年平均\n{n['recent_units']/1e4:.1f}万戸（{n['change_pct']:+.0f}%）", ha="center", fontsize=9)
    ax.legend(ncol=4, loc="upper right", frameon=False, fontsize=9)
    ax.set_ylim(0, 28)
    fig.text(0.01, 0.045, "首都圏＝埼玉・千葉・東京・神奈川、中部圏＝岐阜・静岡・愛知・三重、近畿圏＝京都・大阪・兵庫・奈良、地方圏＝それ以外の35道県。灰色は比べる期間",
             fontsize=7.5, color=GRAY)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.15)
    finish(fig, "fig1_condo_starts_by_metro.png")


def fig2():
    t = pd.read_csv(RES / "region8_compare.csv", index_col=0)
    order = list(t.index)  # 北から南
    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    y = np.arange(len(order))[::-1]
    v = t.change_pct.values
    ax.barh(y, v, color=C[0], height=0.6, zorder=2)
    for yi, (g, r) in zip(y, t.iterrows()):
        ax.text(r.change_pct + 1, yi, f"{r.change_pct:+.0f}%", va="center", ha="left", fontsize=9, color="white", zorder=4)
        ax.text(2, yi, f"{r.base_units:,.0f} → {r.recent_units:,.0f} 戸", va="center", ha="left", fontsize=8.5, color=GRAY)
    ax.set_yticks(y, order)
    ax.axvline(M["national"]["change_pct"], color=GRAY, ls="--", lw=1)
    ax.text(M["national"]["change_pct"] - 1, -0.75, f"全国 {M['national']['change_pct']:+.0f}%", ha="right", fontsize=8.5, color=GRAY)
    ax.set_ylim(-1.1, len(order) - 0.4)
    ax.set_xlim(-80, 30)
    ax.set_xlabel("2005〜07年平均から2023〜25年平均への増減率（%）")
    ax.set_title("8つの地方すべてで減った。減り方は中部・九州・沖縄・近畿で小さめ", loc="left", fontsize=12)
    fig.text(0.01, 0.045, "地方は北から南の順（減り方の順位ではない）。右の数字は1年あたりの平均戸数。中部は新潟〜愛知の9県、近畿は三重〜和歌山の7府県",
             fontsize=7.5, color=GRAY)
    fig.subplots_adjust(left=0.13, right=0.98, top=0.9, bottom=0.17)
    finish(fig, "fig2_change_by_region8.png")


def fig3():
    t = pd.read_csv(RES / "floor_per_unit_annual.csv", index_col="year")
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    shade(ax)
    for g, c in (("三大都市圏", C[0]), ("地方圏", C[3])):
        ax.plot(t.index, t[g], color=c, lw=2, zorder=3)
        ax.text(2025.4, t[g].iloc[-1], f"{g} {t[g].iloc[-1]:.0f}㎡", va="center", fontsize=9)
    ax.plot(t.index, t["全国"], color=GRAY, lw=1.2, ls="--", zorder=3)
    ax.text(2025.4, t["全国"].iloc[-1] + 2.5, f"全国 {t['全国'].iloc[-1]:.0f}㎡", va="center", fontsize=9, color=GRAY)
    ax.set_xlim(1987.5, 2031)
    ax.set_xticks(range(1990, 2026, 5))
    ax.set_ylim(55, 110)
    ax.set_ylabel("1戸あたり床面積（㎡）")
    f = M["floor_change_m2"]
    ax.set_title(f"1戸あたりの広さは2000年代半ばから縮み、三大都市圏は{f['三大都市圏']:+.0f}㎡", loc="left", fontsize=12)
    fig.text(0.01, 0.045, "床面積の合計÷戸数。灰色は比べる期間（2005〜07年、2023〜25年）", fontsize=7.5, color=GRAY)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.15)
    finish(fig, "fig3_floor_per_unit.png")


def fig4():
    q = M["requestion"]["detached_metro"]
    mt = M["metro"]
    groups = ["首都圏", "中部圏", "近畿圏", "地方圏"]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(len(groups))
    w = 0.36
    a = [mt[g]["change_pct"] for g in groups]
    b = [q[g]["change_pct"] for g in groups]
    ax.bar(x - w / 2 - 0.01, a, w, color=C[0], label="分譲マンション", zorder=2)
    ax.bar(x + w / 2 + 0.01, b, w, color=C[1], label="分譲一戸建て", zorder=2)
    for xi, (va, vb) in enumerate(zip(a, b)):
        for xx, v in ((xi - w / 2, va), (xi + w / 2, vb)):
            ax.text(xx, v + (2 if v >= 0 else -2), f"{v:+.0f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=9)
    ax.axhline(0, color="#888888", lw=1)
    ax.set_xticks(x, groups)
    ax.set_ylim(-75, 70)
    ax.set_ylabel("2005〜07年→2023〜25年の増減率（%）")
    s = M["requestion"]["mansion_share_of_bunjo"]
    ax.set_title(f"地方圏では分譲一戸建てが増え、分譲に占めるマンションは{s['地方圏_base']:.0f}%→{s['地方圏_recent']:.0f}%", loc="left", fontsize=12)
    ax.legend(frameon=False, loc="upper left")
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.12)
    finish(fig, "fig4_mansion_vs_detached.png")


fig1(); fig2(); fig3(); fig4()
