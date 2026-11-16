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

SRC = "出典：総務省「住民基本台帳人口移動報告」をもとに作成者が加工して作成"
M = json.loads((RES / "main.json").read_text(encoding="utf-8"))
Y = pd.read_csv(RES / "yearly_japanese.csv")
AG = pd.read_csv(RES / "age_2025_japanese.csv")
CITIES = ["札幌市", "仙台市", "広島市", "福岡市"]
CODES = ["01100", "04100", "34100", "40130"]
REGLAB = {"札幌市": "北海道（札幌市以外）", "仙台市": "東北6県", "広島市": "中国5県", "福岡市": "九州・沖縄8県"}


def fig1():
    m = M["main_2025_japanese"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(4); w = 0.24
    reg = [m[c]["region"] for c in CODES]; tky = [m[c]["tokyo"] for c in CODES]; oth = [m[c]["other"] for c in CODES]; tot = [m[c]["total"] for c in CODES]
    ax.bar(x - w, np.array(reg) / 1e3, width=w, color=C[2], label="同じ地方との間")
    ax.bar(x, np.array(tky) / 1e3, width=w, color=C[1], label="東京圏との間")
    ax.bar(x + w, np.array(oth) / 1e3, width=w, color="#aaaaaa", label="その他の地域との間")
    ax.scatter(x, np.array(tot) / 1e3, marker="D", s=50, color="#222222", zorder=3, label="全体の転入超過")
    for xi, v in zip(x, tot):
        ax.annotate(f"全体 {v:+,}", (xi, v / 1e3), xytext=(0, -17 if v > 0 else 9), textcoords="offset points", ha="center", fontsize=9)
    for xi, v in zip(x, reg):
        ax.text(xi - w, v / 1e3 + 0.3, f"{v:+,}", ha="center", fontsize=8)
    for xi, v in zip(x, tky):
        ax.text(xi, v / 1e3 - 0.9, f"{v:+,}", ha="center", fontsize=8)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xticks(x, [f"{c}\n（同じ地方＝{REGLAB[c]}）" for c in CITIES], fontsize=9)
    ax.set_ylabel("転入超過（千人、2025年）")
    ax.set_ylim(-6, 15)
    ax.legend(loc="upper center", fontsize=8.5, frameon=False, ncol=4)
    ax.grid(axis="x", visible=False)
    ax.set_title("2025年：4都市とも同じ地方からは転入超過、東京圏へは転出超過", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.14)
    source(fig, SRC + "。日本人移動者。同じ県の当該都市以外の市町村を含む")
    save(fig, "fig1_2025_split.png")


def fig2():
    fig, axs = plt.subplots(1, 4, figsize=(9.6, 4.6), sharey=True)
    for ax, c in zip(axs, CITIES):
        d = Y[Y.city == c].set_index("year")
        ax.plot(d.index, d.region / 1e3, color=C[2], lw=2, marker="o", ms=3, label="同じ地方との間")
        ax.plot(d.index, d.tokyo / 1e3, color=C[1], lw=2, marker="o", ms=3, label="東京圏との間")
        ax.plot(d.index, d.total / 1e3, color="#222222", lw=2.2, label="全体")
        ax.axhline(0, color="#888888", lw=0.8)
        ax.set_title(c, fontsize=11)
        ax.set_xticks([2014, 2019, 2025], ["2014", "2019", "2025"], fontsize=8.5)
    axs[0].set_ylabel("転入超過（千人）")
    axs[0].set_ylim(-6, 15)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper right", fontsize=9, frameon=False, ncol=3, bbox_to_anchor=(0.98, 0.99))
    fig.suptitle("2014〜2025年の転入超過：広島市は2019年から全体がマイナスに", x=0.01, ha="left", fontsize=11.5, y=0.97)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.12, wspace=0.08)
    source(fig, SRC + "。日本人移動者")
    save(fig, "fig2_yearly.png")


def fig3():
    ages = list(M["region_by_age_4cities"].keys())
    reg = np.array([M["region_by_age_4cities"][a] for a in ages]); tky = np.array([M["tokyo_by_age_4cities"][a] for a in ages])
    lab = [a.replace("歳～", "〜").replace("歳", "").replace("以上", "+") for a in ages]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(len(ages)); w = 0.4
    ax.bar(x - w / 2, reg / 1e3, width=w, color=C[2], label="同じ地方との間")
    ax.bar(x + w / 2, tky / 1e3, width=w, color=C[1], label="東京圏との間")
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xticks(x, lab, fontsize=8.5, rotation=45)
    ax.set_xlabel("年齢（5歳階級）")
    ax.set_ylabel("転入超過（千人、4都市の合計、2025年）")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title(f"同じ地方から集まるのも、東京圏へ出ていくのも、中心は20代前半（東京圏の分の{M['tokyo_2029_share']:.0f}%が20代）", loc="left", fontsize=10.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.17)
    source(fig, SRC + "。日本人移動者。札幌・仙台・広島・福岡の4市の合計")
    save(fig, "fig3_age.png")


def fig4():
    q = M["requestion"]
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    x = np.arange(4); w = 0.36
    e = [q[c]["in_region"][0] for c in CITIES]; l = [q[c]["in_region"][1] for c in CITIES]
    ax.bar(x - w / 2, np.array(e) / 1e3, width=w, color="#9ecae1", label="2014〜2016年の平均")
    ax.bar(x + w / 2, np.array(l) / 1e3, width=w, color=C[0], label="2023〜2025年の平均")
    for xi, a, b in zip(x, e, l):
        ax.text(xi + w / 2, b / 1e3 + 0.6, f"{100*(b/a-1):+.0f}%", ha="center", fontsize=9)
        ax.text(xi - w / 2, a / 1e3 + 0.6, f"{a/1e3:.1f}", ha="center", fontsize=8, color="#555555")
    ax.set_xticks(x, CITIES)
    ax.set_ylabel("同じ地方からの転入者数（千人、年平均）")
    ax.set_ylim(0, 55)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.grid(axis="x", visible=False)
    ax.set_title("同じ地方からの転入者の数は4都市とも減った。転入超過は広島市以外で横ばいか増加", loc="left", fontsize=11.5)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.1)
    source(fig, SRC + "。日本人移動者")
    save(fig, "fig4_inflow_counts.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
