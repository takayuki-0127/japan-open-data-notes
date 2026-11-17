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

SRC = "出典：総務省「住宅・土地統計調査」時系列統計表をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))


def fig1():
    t = pd.read_csv(RES / "japan_trend.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(t))
    ax.bar(x, t.public / 1e4, 0.6, color=[C[1] if y == 2003 else C[0] for y in t.year])
    for xi, v in zip(x, t.public / 1e4):
        ax.text(xi, v + 3, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, [str(y) for y in t.year], fontsize=9)
    ax.set_ylim(0, 420)
    ax.set_ylabel("公営の借家に住む世帯（万、人が住む住宅の数）")
    ax2 = ax.twinx()
    ax2.plot(x, t.public_share, color=GRAY, marker="o", lw=1.5, label="人が住む住宅に占める割合（%、右）")
    for xi, v in zip(x, t.public_share):
        ax2.text(xi, v + 0.25, f"{v:.1f}", ha="center", fontsize=8, color=GRAY)
    ax2.set_ylim(-8, 7); ax2.set_ylabel("割合（%）"); ax2.grid(False); ax2.spines["right"].set_visible(True)
    ax2.legend(loc="upper right", fontsize=9, frameon=False)
    ax2.set_yticks([0, 2, 4, 6])
    ax.set_title("公営の借家：2003年の218万がいちばん多く、2023年は176万（−19%）", loc="left", fontsize=12)
    ax.set_xlabel("調査年（1963・1968年は沖縄県を含まない）")
    fig.subplots_adjust(left=0.09, right=0.92, top=0.9, bottom=0.15)
    source(fig, SRC)
    save(fig, "fig1_public_housing_count.png")


def fig2():
    a = pd.read_csv(RES / "age_rates.csv", index_col=0)
    x = np.arange(len(a))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.bar(x - 0.2, a.rate_2003, 0.4, color="#9cbfe9", label="2003年")
    ax.bar(x + 0.2, a.rate_2023, 0.4, color=C[0], label="2023年")
    for xi, (u, v) in enumerate(zip(a.rate_2003, a.rate_2023)):
        ax.text(xi - 0.2, u + 0.1, f"{u:.1f}", ha="center", fontsize=8.5)
        ax.text(xi + 0.2, v + 0.1, f"{v:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, a.index)
    ax.set_ylim(0, 8)
    ax.set_xlabel("家計を主に支える者の年齢")
    ax.set_ylabel("その年齢の世帯のうち公営の借家に住む割合（%）")
    dc = M["decomposition_2003_2023"]
    ax.text(0.02, 0.97, f"2003→2023年の変化 {dc['change']/1e4:+.1f}万世帯\n＝ 高齢の世帯が増えた分 {dc['composition']/1e4:+.1f}万 ＋ 年齢ごとの割合が下がった分 {dc['rate']/1e4:+.1f}万",
            transform=ax.transAxes, va="top", fontsize=9.5)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, 0.82), fontsize=9.5, frameon=False, ncol=2)
    ax.set_title("どの年齢でも公営に住む割合は下がった。若い世帯ほど大きく下がった", loc="left", fontsize=12)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.15)
    source(fig, SRC + "。年齢不詳を除く")
    save(fig, "fig2_age_rates.png")


def fig3():
    rg = M["regions"]
    names = list(rg.keys()); x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    for k, (y, c) in enumerate([(1983, "#c9dbf3"), (2003, "#9cbfe9"), (2023, C[0])]):
        v = [rg[n][f"share_{y}"] for n in names]
        ax.bar(x + (k - 1) * 0.27, v, 0.27, color=c, label=f"{y}年")
        if y == 2023:
            for xi, vv in zip(x, v):
                ax.text(xi + 0.27, vv + 0.12, f"{vv:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(x, names)
    ax.set_ylim(0, 10)
    ax.set_ylabel("人が住む住宅に占める公営の借家の割合（%）")
    ax.set_title("地方別（北から南）：8地方すべてで2003年より下がった", loc="left", fontsize=12)
    ax.legend(loc="upper right", fontsize=9.5, frameon=False)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC)
    save(fig, "fig3_region_share.png")


def fig4():
    q = pd.read_csv(RES / "requestion_rent.csv")
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    ax.plot(q.year, q.monthly_ratio, color=C[0], lw=2.3, marker="o", label="1か月当たり家賃の比")
    ax.plot(q.year, q.tatami_ratio, color=C[1], lw=2.3, marker="o", label="1畳当たり家賃の比")
    for col, c in (("monthly_ratio", C[0]), ("tatami_ratio", C[1])):
        ax.annotate(f"{q[col].iloc[-1]:.1f}%", (q.year.iloc[-1], q[col].iloc[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9.5, color=c)
    ax.set_xlim(1971, 2027); ax.set_xticks(q.year)
    ax.set_ylim(0, 70)
    ax.set_ylabel("公営の借家の家賃 ÷ 借家全体の家賃（%）")
    ax.set_title("公営の家賃は借家全体の約4割。1990年代に下がり、2008年からはほぼ一定", loc="left", fontsize=12)
    ax.legend(loc="lower left", fontsize=9.5, frameon=False)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.12)
    source(fig, SRC + "（第34-1表）")
    save(fig, "fig4_rent_ratio.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
