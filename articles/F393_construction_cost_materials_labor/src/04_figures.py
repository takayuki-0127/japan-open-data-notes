"""図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.edgecolor": "#888888", "axes.grid": True,
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.8})
C = ["#2a78d6", "#eb6834", "#1f9e74", "#8a5cc2", "#c2a01f", "#555555", "#d64f8a"]
GRAY = "#555555"
META = {"Software": None}


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def source(fig, text):
    fig.text(0.01, 0.012, text, fontsize=7.5, color=GRAY)

SRC = "出典：国土交通省「建設工事費デフレーター」、厚生労働省「毎月勤労統計調査」、日本銀行「企業物価指数」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
P = pd.read_csv(RES / "fy_panel_used.csv", index_col=0)


def fig1():
    p = P.loc[2000:2025]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    series = [("d_wood_house", "建設工事費デフレーター（木造住宅）", "#222222", 2.8), ("wood", "木材・木製品", C[4], 1.8),
              ("metalprod", "金属製品", C[3], 1.8), ("steel", "鉄鋼", C[5], 1.8), ("wage", "建設業の賃金（1人当たり）", C[1], 2.4)]
    for col, lab, c, lw in series:
        v = 100 * p[col] / p.loc[2020, col]
        ax.plot(p.index, v, color=c, lw=lw, label=f"{lab}（2025年度 {v.loc[2025]:.0f}）")
    ax.axvspan(2019.5, 2025.5, color="#f2f2f2", zorder=0)
    ax.set_xlim(2000, 2025.5); ax.set_xticks(range(2000, 2026, 5))
    ax.set_ylabel("2020年度＝100")
    ax.set_xlabel("年度")
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    ax.set_title("2020年度から、資材は3〜4割上がり、建設業の賃金は1割余り", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC)
    save(fig, "fig1_indices.png")


def fig2():
    c = pd.read_csv(RES / "contributions.csv")
    c = c[c.target.isin(["木造住宅", "非木造住宅"])]
    labels = [f"{t}\n{p}年度" for t, p in zip(c.target, c.period)]
    x = np.arange(len(c))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(x, c.material, 0.55, color=C[0], label="資材の寄与")
    ax.bar(x, c.labor, 0.55, bottom=c.material, color=C[1], label="人件費の寄与")
    ax.bar(x, c.other, 0.55, bottom=c.material + c.labor, color="#bbbbbb", label="説明できない分")
    for xi, (m, l, a) in enumerate(zip(c.material, c.labor, c.actual)):
        ax.text(xi, m / 2, f"{m:.1f}", ha="center", color="white", fontsize=9)
        ax.text(xi, m + l / 2, f"{l:.1f}", ha="center", color="white", fontsize=9)
        ax.text(xi, a + 0.6, f"計 {a:.1f}", ha="center", fontsize=9.5)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 25)
    ax.set_ylabel("デフレーターの変化（対数差×100）への寄与")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_title("2013〜19年度は人件費と資材が半々、2020〜25年度は資材が7割", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC + "。重みは非負の最小二乗で推定")
    save(fig, "fig2_contributions.png")


def fig3():
    cw = M["contrib"]["木造住宅"]["2020→2025"]["by_material"]
    cn = M["contrib"]["非木造住宅"]["2020→2025"]["by_material"]
    names = [k for k in cw if (abs(cw[k]) > 0.05 or abs(cn[k]) > 0.05)]
    y = np.arange(len(names))[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.barh(y + 0.2, [cw[k] for k in names], 0.4, color=C[4], label="木造住宅")
    ax.barh(y - 0.2, [cn[k] for k in names], 0.4, color=C[3], label="非木造住宅")
    for yi, k in zip(y, names):
        ax.text(cw[k] + 0.15, yi + 0.2, f"{cw[k]:.1f}", va="center", fontsize=9)
        ax.text(cn[k] + 0.15, yi - 0.2, f"{cn[k]:.1f}", va="center", fontsize=9)
    ax.set_yticks(y, names)
    ax.set_xlim(0, 14)
    ax.set_xlabel("2020→2025年度のデフレーターの変化への寄与（対数差×100）")
    ax.legend(loc="lower right", fontsize=9.5, frameon=False)
    ax.set_title("資材のうち、木造は木材と金属製品、非木造は金属製品が大きい", loc="left", fontsize=12)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.18, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC)
    save(fig, "fig3_material_breakdown.png")


def fig4():
    f = pd.read_csv(RES / "fit_wood_house.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(f.index, f.material, color=C[0], width=0.7, label="資材の寄与（推定）")
    ax.bar(f.index, f.labor, bottom=np.where(f.labor >= 0, f.material.clip(lower=0), f.material.clip(upper=0)), color=C[1], width=0.7, label="人件費の寄与（推定）")
    ax.plot(f.index, f.actual, color="#222222", marker="o", ms=3.5, lw=1.6, label="実際の前年度比")
    ax.axhline(0, color="#888888", lw=0.8)
    w = M["weights"]["木造住宅"]
    ax.text(0.02, 0.96, f"推定の重み：資材 {w['資材の合計']:.2f}、賃金 {w['賃金']:.2f}（公表の労務の重み {M['official_labor_weight']['住宅建築（木造）']:.3f}）、R² = {w['r2']:.2f}",
            transform=ax.transAxes, va="top", fontsize=9)
    ax.set_xlim(1990, 2026)
    ax.set_ylabel("木造住宅のデフレーターの前年度比（対数差×100）")
    ax.set_xlabel("年度")
    ax.legend(loc="lower left", fontsize=8.5, frameon=False, ncol=3)
    ax.set_title("木造住宅の年ごとの変化は、資材と賃金でほぼ説明できる", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC)
    save(fig, "fig4_fit_wood_house.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
