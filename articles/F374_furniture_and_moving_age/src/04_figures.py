"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
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
BLUE, ORANGE, GRAY, GREEN, LIGHT, BROWN = "#2a78d6", "#eb6834", "#555555", "#3a9e6f", "#9bb7d9", "#8a5a2b"
SRC = ("出典：総務省「家計調査」家計収支編 二人以上の世帯 年報、「住民基本台帳人口移動報告」をもとに作成者が加工して作成")
META = {"Software": None}
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def fig1():
    p = pd.read_csv(RES / "age_profile_mean_2013_2025.csv", index_col=0).loc[AGES]
    r = pd.read_csv(RES / "move_rate_10y.csv", index_col=0).loc[AGES]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    x = np.arange(len(AGES))
    bottom = np.zeros(len(AGES))
    for it, c in [("一般家具", BROWN), ("室内装備・装飾品", ORANGE), ("寝具類", LIGHT)]:
        v = p[it].values / 1000
        ax.bar(x, v, 0.6, bottom=bottom, color=c, label=it)
        bottom += v
    for i, t in enumerate(bottom):
        ax.text(i, t + 0.4, f"{t:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(AGES)
    ax.set_ylabel("1世帯当たり年間の支出（千円、2013〜2025年の平均）")
    ax.set_ylim(0, 36)
    ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=3)
    ax2 = ax.twinx()
    ax2.plot(x, r["total"], color=BLUE, marker="o", lw=2)
    for i, v in enumerate(r["total"]):
        ax2.text(i + 0.12, v + 0.4, f"{v:.1f}%", color=BLUE, fontsize=8.5)
    ax2.set_ylabel("移動率（%、2024年、青の線）", color=BLUE)
    ax2.set_ylim(0, 20)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax.set_title("引っ越しは20代が飛びぬけて多いが、家具・インテリアの支出は年齢でそれほど違わない", fontsize=11.5)
    save(fig, "fig1_age_profile_vs_moves.png")


def fig2():
    s = pd.read_csv(RES / "season_2013_2024.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    mo = s.index.values
    ax.plot(mo, s["movers_idx"], color=BLUE, lw=2.2, marker="o", label="引っ越し（移動者数）")
    ax.plot(mo, s["家具・インテリア_idx"], color=BROWN, lw=2.2, marker="s", label="家具・インテリアの支出")
    ax.plot(mo, s["ベッド_idx"], color=ORANGE, lw=1.5, ls="--", marker="^", label="うちベッド")
    ax.axhline(1, color="#888888", lw=0.8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels([f"{i}月" for i in range(1, 13)])
    ax.set_ylabel("その年の月平均＝1（2013〜2024年の平均）")
    ax.set_ylim(0.5, 2.4)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("引っ越しは3〜4月に2倍。家具・インテリアの支出は12月が多く、春の山はない", fontsize=11.5)
    save(fig, "fig2_monthly_pattern.png")


def fig3():
    m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
    c = m["corr_age_by_item"]
    keys = ["テーブル・ソファー", "一般家具", "ベッド", "家具・インテリア", "寝具類", "家具・家事用品", "カーテン", "室内装備・装飾品"]
    v = [c[k] for k in keys]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    y = np.arange(len(keys))[::-1]
    ax.barh(y, v, color=[BROWN if x > 0 else LIGHT for x in v], height=0.6)
    for yy, x in zip(y, v):
        ax.text(x + (0.03 if x >= 0 else -0.03), yy, f"{x:.2f}", va="center", ha="left" if x >= 0 else "right", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(keys)
    ax.axvline(0, color="#888888", lw=0.8)
    ax.set_xlim(-1, 1)
    ax.set_xlabel("年齢別（6区分）の支出と移動率の相関")
    ax.set_title("家具そのもの（テーブル・ソファーなど）は引っ越しの多い年齢で多く、\nカーテンや室内装飾品は年齢の高い世帯で多い", fontsize=11.5)
    save(fig, "fig3_corr_by_item.png")


def fig4():
    s = pd.read_csv(RES / "share_2025.csv", index_col=0).loc[AGES]
    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    x = np.arange(len(AGES))
    for j, (k, c, lab) in enumerate([("share_households_pct", "#bbbbbb", "世帯数"),
                                      ("share_interior_pct", BROWN, "家具・インテリアの支出の総額"),
                                      ("share_furn_pct", ORANGE, "うち一般家具")]):
        ax.bar(x + (j - 1) * 0.27, s[k], 0.27, color=c, label=lab)
        for i, v in enumerate(s[k]):
            ax.text(x[i] + (j - 1) * 0.27, v + 0.6, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(AGES)
    ax.set_ylabel("二人以上の世帯の全体に占める割合（%、2025年）")
    ax.set_ylim(0, 40)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.set_title("家具・インテリアの支出の総額の47%は、世帯主が60歳以上の世帯", fontsize=11.5)
    save(fig, "fig4_share_by_age.png")


def main():
    fig1()
    fig2()
    fig3()
    fig4()
    print(json.dumps(sorted(p.name for p in FIG.glob("*.png")), ensure_ascii=False))


if __name__ == "__main__":
    main()
