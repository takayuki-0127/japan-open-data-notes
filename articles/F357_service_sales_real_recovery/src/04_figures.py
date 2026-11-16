"""04_figures.py : 図を figures/ に PNG で作る（オフライン、日付を埋め込まない）。"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
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
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.8, "svg.hashsalt": "f357"})
NOM, REAL, GRAY = "#2a78d6", "#eb6834", "#555555"
SRC_SALES = "出典：総務省「サービス産業動態統計調査」、日本銀行「企業向けサービス価格指数」、総務省「消費者物価指数」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


def to_x(ym):
    return [(v // 100) + ((v % 100) - 0.5) / 12 for v in ym]


def fig1():
    mm = pd.read_csv(RES / "rolling12_index.csv")
    x = mm[(mm.group == "total") & (mm.ym >= 201812)]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(to_x(x.ym), x.nominal, color=NOM, lw=2, label="名目（その時の値段）")
    ax.plot(to_x(x.ym), x.real, color=REAL, lw=2, label="実質（2019年の値段）")
    ax.axhline(100, color=GRAY, lw=1, ls="--")
    last = x.iloc[-1]
    ax.annotate(f"{last.nominal:.1f}", (to_x([last.ym])[0], last.nominal), xytext=(4, 0),
                textcoords="offset points", va="center", color="#222222")
    ax.annotate(f"{last.real:.1f}", (to_x([last.ym])[0], last.real), xytext=(4, 0),
                textcoords="offset points", va="center", color="#222222")
    ax.set_title("対象業種の売上（12か月合計、2019年=100）：名目は上回り、実質はまだ下", loc="left", fontsize=12)
    ax.set_ylabel("2019年=100")
    ax.set_xlabel("12か月合計の最後の月")
    ax.set_xlim(2018.9, 2026.9)
    ax.legend(loc="lower right", frameon=False)
    fig.text(0.01, 0.01, SRC_SALES, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "fig1_total_nominal_real.png")


def fig2():
    dv = pd.read_csv(RES / "division_ratios.csv")
    fig, ax = plt.subplots(figsize=(8, 5.2))
    y = range(len(dv))[::-1]
    h = 0.36
    ax.barh([v + h / 2 for v in y], dv.nominal - 100, height=h, color=NOM, label="名目")
    ax.barh([v - h / 2 for v in y], dv.real - 100, height=h, color=REAL, label="実質")
    for v, (n, r) in zip(y, zip(dv.nominal, dv.real)):
        ax.text(n - 100 + (0.5 if n >= 100 else -0.5), v + h / 2, f"{n:.1f}", va="center",
                ha="left" if n >= 100 else "right", fontsize=8.5)
        ax.text(r - 100 + (0.5 if r >= 100 else -0.5), v - h / 2, f"{r:.1f}", va="center",
                ha="left" if r >= 100 else "right", fontsize=8.5)
    ax.set_yticks(list(y))
    ax.set_yticklabels(dv.division)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_xlabel("2019年からの差（2025年の年計、2019年=100 からのポイント）")
    ax.set_xlim(-26, 26)
    ax.set_title("大分類別の売上（2025年、2019年=100）：実質で上回るのは情報通信など2つ", loc="left", fontsize=12)
    ax.legend(loc="lower left", frameon=False)
    ax.grid(axis="y", visible=False)
    fig.text(0.01, 0.01, SRC_SALES, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "fig2_division_nominal_real.png")


def fig3():
    mm = pd.read_csv(RES / "rolling12_index.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), sharey=True)
    for ax, g, t in zip(axes, ["face", "biz"], ["対面・家計向け（宿泊・飲食・娯楽など7業種）", "事業所向け（23業種）"]):
        x = mm[(mm.group == g) & (mm.ym >= 201812)]
        ax.plot(to_x(x.ym), x.nominal, color=NOM, lw=2, label="名目")
        ax.plot(to_x(x.ym), x.real, color=REAL, lw=2, label="実質")
        ax.axhline(100, color=GRAY, lw=1, ls="--")
        last = x.iloc[-1]
        for v in (last.nominal, last.real):
            ax.annotate(f"{v:.1f}", (to_x([last.ym])[0], v), xytext=(3, 0), textcoords="offset points",
                        va="center", fontsize=8.5)
        ax.set_title(t, fontsize=10.5, loc="left")
        ax.set_xlim(2018.9, 2027.2)
    axes[0].set_ylabel("12か月合計、2019年=100")
    axes[0].legend(loc="lower right", frameon=False)
    fig.suptitle("値段を除くと、対面の業種は2019年の約87%にとどまる", x=0.01, ha="left", fontsize=12)
    fig.text(0.01, 0.01, SRC_SALES, fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    save(fig, "fig3_face_vs_business.png")


def fig4():
    sz = pd.read_csv(RES / "size_share_target.csv")
    sizes = ["10人未満", "10〜29人", "30〜99人", "100〜299人", "300人以上"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    w = 0.26
    cols = {2018: "#9fc3ee", 2019: NOM, 2023: "#123f75"}
    for k, yv in enumerate((2018, 2019, 2023)):
        v = sz[sz.year == yv].set_index("size").loc[sizes, "share_pct"]
        xs = [i + (k - 1) * w for i in range(len(sizes))]
        ax.bar(xs, v, width=w - 0.02, color=cols[yv], label=f"{yv}年")
        if yv != 2018:
            for xx, vv in zip(xs, v):
                ax.text(xx, vv + 0.5, f"{vv:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(range(len(sizes)))
    ax.set_xticklabels(sizes)
    ax.set_xlabel("事業所・企業等の事業従事者の規模")
    ax.set_ylabel("対象業種の売上に占める割合（%）")
    ax.set_title("規模別の売上の割合：2019→2023年の動きは、2018→2019年の揺れと同じくらい", loc="left", fontsize=12)
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    fig.text(0.01, 0.01, "出典：総務省「サービス産業動向調査」年報 第3表（各年の月平均、段差の調整なし）をもとに作成者が加工して作成",
             fontsize=7, color=GRAY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "fig4_size_share.png")


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    print("ok")
