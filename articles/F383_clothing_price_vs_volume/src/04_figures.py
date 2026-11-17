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
                     "axes.edgecolor": "#888888", "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.8})
C = ["#2a78d6", "#eb6834", "#1f9e74", "#8a5cc2"]
GRAY = "#555555"
SRC = "出典：総務省「家計調査」（二人以上の世帯）「消費者物価指数」（2025年基準）をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))


def finish(fig, name, note=None):
    if note:
        fig.text(0.01, 0.045, note, fontsize=7.5, color=GRAY)
    fig.text(0.01, 0.012, SRC, fontsize=7.5, color=GRAY)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def fig1():
    t = pd.read_csv(RES / "annual_national.csv", index_col="year")
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for col, lab, c, ls in (("nominal_idx2000", "支出（名目）", C[0], "-"), ("cpi_idx2000", "服と靴の物価", C[1], "-"),
                            ("real_idx2000", "量（実質＝支出÷物価）", C[2], "-")):
        ax.plot(t.index, t[col], color=c, lw=2, ls=ls)
        ax.text(2025.4, t[col].iloc[-1], f"{lab} {t[col].iloc[-1]:.0f}", va="center", fontsize=9)
    ax.axhline(100, color="#999999", lw=0.8)
    ax.set_xlim(1999.5, 2031.5)
    ax.set_xticks(range(2000, 2026, 5))
    ax.set_ylim(40, 130)
    ax.set_ylabel("2000年＝100")
    n = M["national_2000_2025"]
    ax.set_title(f"支出は{n['nominal_pct']:+.0f}%。物価は{n['price_pct']:+.0f}%で、減ったのは量（{n['real_pct']:+.0f}%）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.15)
    finish(fig, "fig1_nominal_price_real.png", "被服及び履物、1世帯あたり年間。物価は消費者物価指数の「被服及び履物」（暦年の年平均）")


def fig2():
    t = pd.read_csv(RES / "items_decomposition.csv")
    t = t[t["item"] != "被服及び履物"]
    order = list(t["item"])  # 家計調査の表の順
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    y = np.arange(len(order))[::-1]
    h = 0.26
    for k, (col, lab, c) in enumerate((("nominal_pct", "支出（名目）", C[0]), ("price_pct", "物価", C[1]), ("real_pct", "量（実質）", C[2]))):
        ax.barh(y + (1 - k) * h, t[col], height=h - 0.03, color=c, label=lab, zorder=2)
    for yi, r in zip(y, t.itertuples()):
        ax.text(min(r.real_pct, r.nominal_pct) - 2, yi - h, f"{r.real_pct:+.0f}%", va="center", ha="right", fontsize=8.5)
        ax.text(max(r.price_pct, 0) + 1.5, yi, f"{r.price_pct:+.0f}%", va="center", ha="left", fontsize=8.5, color=GRAY)
    ax.set_yticks(y, [f"{o}\n（2025年 {int(v):,}円）" for o, v in zip(order, t.nominal_2025)], fontsize=9)
    ax.axvline(0, color="#888888", lw=1)
    ax.set_xlim(-100, 55)
    ax.set_xlabel("2000→2025年の変化率（%）")
    ax.legend(ncol=3, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0), fontsize=9)
    ax.set_title("どの費目も物価は横ばいか上がり、減ったのは量", loc="left", fontsize=12, pad=26)
    fig.subplots_adjust(left=0.2, right=0.98, top=0.88, bottom=0.17)
    finish(fig, "fig2_items_decomposition.png", "費目は家計調査の表の順。量の数字は緑の棒の値。生地・糸類は「衣料」の物価で割った")


def fig3():
    t = pd.read_csv(RES / "age_real_annual.csv", index_col="year")
    A = list(t.columns)
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    x = np.arange(len(A))
    w = 0.38
    v0, v1 = t.loc[2002] / 1e4, t.loc[2025] / 1e4
    ax.bar(x - w / 2 - 0.01, v0, w, color=C[3], label="2002年（2025年の物価で）", zorder=2)
    ax.bar(x + w / 2 + 0.01, v1, w, color=C[2], label="2025年", zorder=2)
    for xi, a in enumerate(A):
        ax.text(xi + w / 2, v1[a] + 0.4, f"{M['age'][a]['real_pct']:+.0f}%", ha="center", fontsize=9)
    ax.set_xticks(x, [a.replace("～", "〜") for a in A])
    ax.set_ylabel("実質の支出（万円／年、2025年の物価）")
    ax.set_ylim(0, 30)
    ss = M["age_shift_share_real_2025yen"]
    ax.set_title(f"すべての年齢で量が減った。減少のうち年齢構成の変化の分は{ss['composition_share_pct']:.0f}%", loc="left", fontsize=12)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.15)
    finish(fig, "fig3_age_real.png", "世帯主の年齢別、1世帯あたり年間の被服及び履物。全国共通の物価指数で割った。数字は2002→2025年の実質の変化")


def fig4():
    t = pd.read_csv(RES / "long_1970_2025.csv", index_col="year")
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(t.index, t.nominal_linked / 1e4, color=C[0], lw=2)
    ax.plot(t.index, t.real_2025yen / 1e4, color=C[2], lw=2)
    ax.text(2025.5, t.nominal_linked.iloc[-1] / 1e4 - 1.5, "支出（名目）", fontsize=9, va="center")
    ax.text(2025.5, t.real_2025yen.iloc[-1] / 1e4 + 1.5, "量（実質、\n2025年の物価）", fontsize=9, va="center")
    L = M["long"]
    ax.annotate(f"名目の山 {L['nominal_peak_year']}年\n{L['nominal_peak_yen']/1e4:.1f}万円", xy=(L["nominal_peak_year"], L["nominal_peak_yen"] / 1e4),
                xytext=(1996, 36), fontsize=9, arrowprops=dict(arrowstyle="-", color=GRAY))
    ax.set_xlim(1969, 2033)
    ax.set_xticks(range(1970, 2026, 10))
    ax.set_ylim(0, 45)
    ax.set_ylabel("万円／年（1世帯あたり）")
    d = L["decomp"]
    ax.set_title(f"量は1991年から大きく減った（1991→2025年{d['1991_2025']['real_pct']:+.0f}%、1970→91年は{d['1970_1991']['real_pct']:+.0f}%）", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.15)
    finish(fig, "fig4_long_run.png", "1970〜99年は長期時系列表20-3-a（非農林漁家）を2000〜07年の重なりの比（0.994）でつないだ。2000年からは農林漁家を含む")


fig1(); fig2(); fig3(); fig4()
