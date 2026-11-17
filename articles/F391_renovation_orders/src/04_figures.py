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

SRC = "出典：国土交通省「建築物リフォーム・リニューアル調査」「建築着工統計調査」「建設工事費デフレーター」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
T = pd.read_csv(RES / "annual_table.csv")


def fig1():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    a = T[T.fiscal_year <= 2016]; b = T[T.fiscal_year >= 2016]
    ax.plot(a.fiscal_year, a.total / 1e4, color="#9cbfe9", lw=1.6, ls="--", marker="o", ms=3, label="名目（2015年度以前は参考）")
    ax.plot(b.fiscal_year, b.total / 1e4, color=C[0], lw=2.4, marker="o", ms=4, label="名目（その年の値段）")
    rr = T[T.real_total.notna()]
    ax.plot(rr.fiscal_year, rr.real_total / 1e4, color=C[1], lw=2.4, marker="o", ms=4, label="実質（2020年度の値段、建築補修デフレーターで割る）")
    for df, col, c in ((b, "total", C[0]), (rr, "real_total", C[1])):
        x = df.iloc[-1]
        ax.annotate(f"{x[col]/1e4:.1f}兆円", (x.fiscal_year, x[col] / 1e4), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=c)
    g = M["growth_main"]
    ax.text(0.98, 0.04, f"2016〜18年度平均→2023〜25年度平均：名目 {g['nominal_total']:+.1f}%、実質 {g['real_total']:+.1f}%",
            transform=ax.transAxes, ha="right", fontsize=9.5)
    ax.set_xlim(2010.5, 2027.3); ax.set_xticks(range(2011, 2026, 2))
    ax.set_ylim(0, 18)
    ax.set_ylabel("リフォーム・リニューアル工事の受注高（兆円）")
    ax.set_xlabel("年度")
    ax.set_title("リフォームの受注高：名目は2025年度に16.4兆円、実質では2016〜18年度を下回る", loc="left", fontsize=11.5)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC)
    save(fig, "fig1_orders_nominal_real.png")


def fig2():
    b = T[T.fiscal_year >= 2016]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(b.fiscal_year, b.ratio_housing * 100, color=C[0], lw=2.4, marker="o", ms=4, label="住宅")
    ax.plot(b.fiscal_year, b.ratio_nonres * 100, color=C[2], lw=2.4, marker="o", ms=4, label="非住宅")
    for col, c in (("ratio_housing", C[0]), ("ratio_nonres", C[2])):
        x = b.iloc[-1]
        ax.annotate(f"{x[col]*100:.0f}%", (x.fiscal_year, x[col] * 100), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9.5, color=c)
    q = M["ratio"]
    ax.text(0.02, 0.04, f"3年平均（2016-18→2023-25年度）：住宅 {q['housing0']*100:.1f}%→{q['housing1']*100:.1f}%、非住宅 {q['nonres0']*100:.1f}%→{q['nonres1']*100:.1f}%",
            transform=ax.transAxes, fontsize=9.5)
    ax.set_xlim(2015.5, 2026.5); ax.set_xticks(range(2016, 2026))
    ax.set_ylim(0, 90)
    ax.set_ylabel("リフォーム受注高 ÷ 新築の工事費予定額（%）")
    ax.set_xlabel("年度")
    ax.set_title("新築の工事費と比べたリフォーム：住宅は少し上がり、非住宅は横ばい", loc="left", fontsize=12)
    ax.legend(loc="upper left", fontsize=9.5, frameon=False)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC + "。どちらも名目")
    save(fig, "fig2_ratio_to_new.png")


def fig3():
    p = pd.read_csv(RES / "purpose_shares.csv")
    h = p[(p.group == "住宅") & (p.fiscal_year >= 2017)]
    cols = [("省エネルギー対策", C[1]), ("耐震性向上", C[2]), ("増床", C[4]), ("防災･防犯･安全性向上", C[5])]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for c, col in cols:
        ax.plot(h.fiscal_year, h["share_" + c], color=col, lw=2.2, marker="o", ms=3.5, label=f"{c}（2025年度 {h['share_' + c].iloc[-1]:.1f}%）")
    deg = h["share_劣化や壊れた部位の更新･修繕"]
    ax.text(0.02, 0.96, f"「劣化や壊れた部位の更新・修繕」は各年度 {deg.min():.0f}〜{deg.max():.0f}%（図の外）", transform=ax.transAxes, va="top", fontsize=9.5)
    ax.set_xlim(2016.5, 2025.5); ax.set_xticks(range(2017, 2026))
    ax.set_ylim(0, 9)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.9), fontsize=8.5, frameon=False)
    ax.set_ylabel("住宅の受注高に占める割合（主たる工事目的、%）")
    ax.set_xlabel("年度")
    ax.set_title("住宅のリフォームの目的：省エネが2023年度から増え、2025年度は6.6%", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC + "。割合の分母は「不明」を除く")
    save(fig, "fig3_housing_purpose_share.png")


def fig4():
    u = pd.read_csv(RES / "requestion_nonres_use.csv")
    u = u[~u.use.isin(["医療施設", "老人福祉施設"])].iloc[::-1]  # 医療・福祉の施設は扱わない
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    y = np.arange(len(u))
    cols = [C[0] if v >= 0 else C[1] for v in u.growth]
    ax.barh(y, u.growth, color=cols, height=0.6)
    for yi, v, n in zip(y, u.growth, u.late_nominal):
        ax.text(v + (1 if v >= 0 else -1), yi, f"{v:+.0f}%（{n/1e4:.2f}兆円）", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, u.use)
    ax.set_xlim(-60, 45)
    ax.set_xlabel("実質の受注高の変化（2017〜19年度平均→2023〜25年度平均、%）\nかっこは2023〜25年度の名目の年平均", fontsize=9.5)
    ax.set_title("非住宅のリフォーム（用途別、表の順）：事務所・学校・宿泊は増、店舗・飲食は減", loc="left", fontsize=11.5)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.22, right=0.97, top=0.9, bottom=0.18)
    source(fig, "出典：国土交通省「建築物リフォーム・リニューアル調査」「建設工事費デフレーター」をもとに作成者が加工して作成。非住宅総合デフレーターで実質化")
    ax.text(0.98, 0.03, "一部の用途（2つ）は載せていない", transform=ax.transAxes, ha="right", fontsize=8.5, color=GRAY)
    save(fig, "fig4_nonres_use_growth.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
