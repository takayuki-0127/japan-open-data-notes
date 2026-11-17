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

SRC = "出典：農林水産省「農地の移動と転用（農地の権利移動・借賃等調査）」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
W = pd.read_csv(RES / "wide_table.csv")
N = W[W.level == "national"].set_index("year")


def fig1():
    parts = [("housing", "住宅用地", C[0]), ("pcf", "公的施設・商業・工場", C[3]), ("parking", "駐車場・資材置場", C[5]),
             ("renew_etc", "再エネ等（再エネ発電設備＋その他）", C[1]), ("forest", "植林", C[2]), ("rest", "その他（農林漁業施設・土石採取・不明）", "#bbbbbb")]
    n = N.copy()
    n["pcf"] = n.public + n.commerce + n.factory
    n["rest"] = n.total - n[["housing", "pcf", "parking", "renew_etc", "forest"]].sum(axis=1)
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    bottom = np.zeros(len(n))
    for col, lab, c in parts:
        ax.bar(n.index, n[col] / 1000, bottom=bottom / 1000, color=c, width=0.7, label=lab)
        bottom += n[col].values
    for x, t in zip(n.index, n.total):
        ax.text(x, t / 1000 + 0.2, f"{t/1000:.1f}", ha="center", fontsize=8)
    ax.set_ylim(0, 22)
    ax.set_xticks(n.index, [str(y) for y in n.index], fontsize=8.5)
    ax.set_ylabel("転用された農地の面積（千ha）")
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=2)
    ax.set_title("農地の転用面積：2010年の1.2万haから2017年の1.8万haへ、増えたのは再エネ等と植林", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。2014年以前の再エネはその他に含まれる")
    save(fig, "fig1_area_by_use.png")


def fig2():
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for col, lab, c in [("s_housing", "住宅用地", C[0]), ("s_renew_etc", "再エネ等", C[1]), ("s_forest", "植林", C[2]), ("s_parking", "駐車場・資材置場", C[5])]:
        ax.plot(N.index, N[col], color=c, lw=2.3, marker="o", ms=3.5, label=lab)
        ax.annotate(f"{lab} {N[col].iloc[-1]:.1f}%", (N.index[-1], N[col].iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=c)
    ax.plot(N.loc[2015:].index, N.loc[2015:, "s_renewable"], color=C[1], lw=1.4, ls="--", label="うち再エネ発電設備（2015年から）")
    ax.set_xlim(2009.5, 2026.8); ax.set_xticks(range(2010, 2024, 2))
    ax.set_ylim(0, 40)
    ax.set_ylabel("転用面積に占める割合（%）")
    ax.legend(loc="upper right", fontsize=8.5, frameon=False, bbox_to_anchor=(0.86, 1))
    ax.set_title("住宅の割合は3割台から2割台に下がり、再エネ等と植林が上がった", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig2_shares.png")


def fig3():
    b = M["blocks"]; names = list(b.keys()); x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for k, (key, lab, c) in enumerate([("前", "2010〜12年", "#f7c7ae"), ("中", "2015〜19年", "#f0905c"), ("後", "2021〜23年", C[1])]):
        ax.bar(x + (k - 1) * 0.27, [b[n][key] for n in names], 0.27, color=c, label=lab)
    ax.set_xticks(x, names)
    ax.set_ylim(0, 35)
    ax.set_ylabel("転用面積に占める再エネ等の割合（%）")
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    ax.set_title("再エネ等の割合（ブロック別、表の順）：11のうち10で2010年代に上がった", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "。期間中の面積の合計から割合を計算")
    save(fig, "fig3_block_renew.png")


def fig4():
    d = pd.read_csv(RES / "requestion_share_change.csv", index_col=0)
    d = d.iloc[::-1]
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.barh(y + 0.2, d["前→中"], 0.4, color=C[0], label="2010〜12年 → 2015〜19年")
    ax.barh(y - 0.2, d["中→後"], 0.4, color=C[2], label="2015〜19年 → 2021〜23年")
    for yi, (a, b) in enumerate(zip(d["前→中"], d["中→後"])):
        ax.text(a + (0.3 if a >= 0 else -0.3), yi + 0.2, f"{a:+.1f}", va="center", ha="left" if a >= 0 else "right", fontsize=8.5)
        ax.text(b + (0.3 if b >= 0 else -0.3), yi - 0.2, f"{b:+.1f}", va="center", ha="left" if b >= 0 else "right", fontsize=8.5)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_yticks(y, d.index, fontsize=9)
    ax.set_xlim(-14, 16)
    ax.set_xlabel("転用面積に占める割合の変化（ポイント）")
    ax.legend(loc="lower right", fontsize=9, frameon=False)
    ax.set_title("割合が上がったのは再エネ等と植林、下がったのは住宅と公的施設", loc="left", fontsize=12)
    ax.grid(axis="y", visible=False)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig4_share_change.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
