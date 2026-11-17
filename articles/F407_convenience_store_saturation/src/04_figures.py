"""図を4枚つくる（PNG、日付などのメタデータを入れない）。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
matplotlib.rcParams["svg.hashsalt"] = "20261116"
ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：経済産業省「商業動態統計」、総務省「消費者物価指数」「人口推計」をもとに作成者が加工して作成"
C1, C2, C3, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#8c8c8c"


def save(fig, name, src=SRC):
    fig.text(0.01, 0.01, src, fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def main():
    a = pd.read_csv(R / "annual_national.csv")
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    q = json.loads((R / "requestion.json").read_text(encoding="utf-8"))

    # fig1 店舗数と年の純増
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.91, top=0.86, bottom=0.16)
    ax.plot(a["year"], a["stores_dec"] / 1e4, color=C1, lw=2.4, marker="o", ms=3.5, label="12月末の店舗数（左の目盛り）")
    ax.set_ylabel("店舗数（万店）")
    ax.set_ylim(3, 6)
    ax2 = ax.twinx()
    net = a["stores_dec"].diff()
    ax2.bar(a["year"], net, color=GR, alpha=0.45, width=0.7, label="前の年からの純増（右の目盛り）")
    ax2.set_ylabel("純増（店）")
    ax2.set_ylim(-500, 6000)
    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    ax.axvspan(2016.5, 2025.5, color="#f2e6d9", alpha=0.6, zorder=0)
    ax.text(2021, 3.3, f"2017〜2025年の純増は\n平均 {m['stores_net_change_avg_2017_2025']:.0f} 店／年", ha="center", fontsize=10)
    ax.text(2013.3, 3.3, f"2011〜2016年は\n平均 {m['stores_net_change_avg_2010_2016']:,.0f} 店／年", ha="center", fontsize=10)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, frameon=False)
    ax.set_xlabel("年")
    fig.suptitle("コンビニの店舗数は2016年ごろから増えなくなった（2016→2025年 +%.1f%%）" % m["H1_stores_2016_2025_pct"], fontsize=13, x=0.02, ha="left")
    ax.set_title("商業動態統計のコンビニ（調査の見直しの段差はリンク係数でつないだ値）", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_store_count.png")

    # fig2 1店あたり販売額 名目と実質
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.86, bottom=0.16)
    ax.plot(a["year"], a["per_store_nom"] / 100, color=C1, lw=2.4, marker="o", ms=3.5, label="名目（その年の円）")
    ax.plot(a["year"], a["per_store_real"] / 100, color=C2, lw=2.4, marker="s", ms=3.5, label="実質（2025年の物価、消費者物価の総合で割った）")
    for y in [2019, 2025]:
        row = a[a["year"] == y].iloc[0]
        ax.annotate(f"{row['per_store_nom']/100:.2f}", (y, row["per_store_nom"] / 100), textcoords="offset points", xytext=(0, -16), ha="center", fontsize=9, color=C1)
        ax.annotate(f"{row['per_store_real']/100:.2f}", (y, row["per_store_real"] / 100), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=C2)
    ax.set_ylabel("1店あたりの年の販売額（億円）")
    ax.set_xlabel("年")
    ax.set_ylim(1.7, 2.6)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.grid(axis="y", color="#dddddd")
    fig.suptitle(f"1店あたりの販売額は名目で +{m['H2_per_store_nom_2019_2025_pct']:.1f}%、物価を除くと {m['H3_per_store_real_2019_2025_pct']:.1f}%（2019→2025年）", fontsize=13, x=0.02, ha="left")
    ax.set_title("年の販売額 ÷ 12か月の月末店舗数の平均", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig2_per_store_sales.png")

    # fig3 2019→2025年の1店あたり名目の変化を商品別に（寄与）
    it = pd.DataFrame(q["items"])
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.17, right=0.95, top=0.84, bottom=0.18)
    labels = list(it["item_ja"]) + ["合計"]
    vals = list(it["contribution_pt"]) + [q["per_store_nom_change_pct_2019_2025"]]
    cols = [C3 if v >= 0 else C2 for v in vals[:-1]] + [C1]
    y = np.arange(len(labels))[::-1]
    ax.barh(y, vals, color=cols, height=0.6)
    for yi, v, (_, row) in zip(y, vals, list(it.iterrows()) + [(None, None)]):
        txt = f"{v:+.2f} ポイント" if row is not None else f"{v:+.2f}%"
        if row is not None:
            txt += f"（その商品の1店あたり {row['change_pct']:+.1f}%）"
        ax.text(max(v, 0) + 0.15, yi, txt, va="center", ha="left", fontsize=9.5)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_xlim(-4, 14)
    ax.set_xlabel("1店あたり名目販売額の 2019→2025年 の変化への寄与（ポイント）")
    fig.suptitle("名目の伸びを支えたのは加工食品と非食品。サービスは減った", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"食品（FF・日配＋加工）の1店あたりは名目 +{q['food_items_per_store_change_pct']:.1f}%、食料の物価（+{m['cpi_food_2019_2025_pct']:.1f}%）で割ると {q['food_items_per_store_real_food_cpi_pct']:.1f}%", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig3_item_contribution.png")

    # fig4 経済産業局の区域別 人口10万人あたり店舗数（北から南）
    rg = pd.read_csv(R / "region_per_capita.csv")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.84, bottom=0.2)
    x = np.arange(len(rg)); w = 0.38
    ax.bar(x - w / 2, rg["per100k_2010"], width=w, color=GR, label="2010年")
    ax.bar(x + w / 2, rg["per100k_2024"], width=w, color=C1, label="2024年")
    for xi, v0, v1 in zip(x, rg["per100k_2010"], rg["per100k_2024"]):
        ax.text(xi - w / 2, v0 + 0.6, f"{v0:.0f}", ha="center", fontsize=8.5)
        ax.text(xi + w / 2, v1 + 0.6, f"{v1:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(rg["region_ja"])
    ax.set_ylabel("人口10万人あたりの店舗数（店）")
    ax.set_ylim(0, 70)
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.set_xlabel("経済産業局の区域（北から南の順。関東は新潟・長野・静岡などを含む）")
    fig.suptitle("2010年に店が少なかった区域ほど、その後に店が増え、差は縮まった", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"2010年の人口あたり店舗数と2010→2019年の店舗数の伸びの相関 {m['H4_corr_pearson']:.2f}（8区域）。区域の間のばらつき（変動係数）は {m['region_cv_2010']:.1f}% → {m['region_cv_2024']:.1f}%", fontsize=9, loc="left", color="#444444")
    save(fig, "fig4_region_per_capita.png")


if __name__ == "__main__":
    main()
