"""図を4枚つくる（PNG、日付などのメタデータを入れない）。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
S_METI = "経済産業省「商業動態統計」"
C1, C2, C3, C4, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#9b5fa5", "#8c8c8c"


def save(fig, name, src):
    fig.text(0.01, 0.01, "出典：" + src + "をもとに作成者が加工して作成", fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    A = pd.read_csv(R / "dept_annual.csv")
    A = A[A["year"] >= 2010]

    # fig1 年の販売額（名目・実質）
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.16)
    ax.plot(A["year"], A["total"] / 1e6, color=C1, lw=2.4, marker="o", ms=4, label="名目（その年の円）")
    ax.plot(A["year"], A["total_real"] / 1e6, color=C2, lw=2.4, marker="s", ms=4, label="実質（2025年の物価、消費者物価の総合で割った）")
    for y in [2019, 2024, 2025]:
        row = A[A["year"] == y].iloc[0]
        ax.annotate(f"{row['total']/1e6:.2f}", (y, row["total"] / 1e6), textcoords="offset points", xytext=(0, -16), ha="center", fontsize=9, color=C1)
    row = A[A["year"] == 2019].iloc[0]
    ax.annotate(f"{row['total_real']/1e6:.2f}", (2019, row["total_real"] / 1e6), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=C2)
    ax.axhline(A.loc[A["year"] == 2019, "total"].iloc[0] / 1e6, color=C1, lw=0.8, ls=":")
    ax.set_ylabel("百貨店の年の販売額（兆円）"); ax.set_xlabel("年")
    ax.set_ylim(4, 8.5); ax.grid(axis="y", color="#dddddd")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    fig.suptitle(f"百貨店の販売額は2025年に2019年を{abs(m['H1_dept_2019_2025_pct']):.1f}%下回った（物価を除くと{abs(m['dept_real_2019_2025_pct']):.1f}%下）", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"2024年は名目で2019年を{m['dept_2019_2024_pct']:.1f}%上回ったが、2025年は前の年より{abs(m['dept_2024_2025_pct']):.1f}%減った", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_dept_sales.png", S_METI + "、総務省「消費者物価指数」")

    # fig2 商品別の増減（億円）
    it = pd.read_csv(R / "items.csv")
    it = it[~it["item"].isin(["total", "clothes", "others"])].sort_values("diff_oku")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    fig.subplots_adjust(left=0.22, right=0.95, top=0.84, bottom=0.16)
    cols = [C3 if x > 0 else C2 for x in it["diff_oku"]]
    y = np.arange(len(it))
    ax.barh(y, it["diff_oku"], color=cols, height=0.62)
    for yi, dv, pc in zip(y, it["diff_oku"], it["pct_2019_2025"]):
        ax.text(dv + (40 if dv >= 0 else -40), yi, f"{dv:+,.0f}億円（{pc:+.1f}%）", va="center", ha="left" if dv >= 0 else "right", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(it["item_ja"])
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_xlim(-2900, 2900)
    ax.set_xlabel("2019→2025年の販売額の増減（億円）")
    fig.suptitle("増えたのは身の回り品と化粧品などのその他の商品。食品と服は減った", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"合計は {m['delta_dept_oku_2019_2025']:+,.0f}億円。訪日客の買物代の総額（推計）は同じ期間に {m['delta_shopping_oku_2019_2025']:+,.0f}億円", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig2_items_change.png", S_METI + "、日本政府観光局「訪日外客数」、観光庁「インバウンド消費動向調査」")

    # fig3 月次 2019年同月比
    mm = pd.read_csv(R / "monthly_vs2019.csv")
    t = np.arange(len(mm))
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    fig.subplots_adjust(left=0.08, right=0.97, top=0.84, bottom=0.2)
    ax.plot(t, mm["visitors_vs2019"], color=GR, lw=2, label="訪日外客数（総数）")
    ax.plot(t, mm["visitors_china_vs2019"], color=GR, lw=1.4, ls="--", label="訪日外客数（中国）")
    ax.plot(t, mm["total_vs2019"], color=C1, lw=2.4, label="百貨店の販売額（合計）")
    ax.plot(t, mm["accessories_vs2019"], color=C4, lw=1.8, label="百貨店の身の回り品")
    ax.plot(t, mm["food_vs2019"], color=C2, lw=1.6, label="百貨店の飲食料品")
    ax.axhline(100, color="#333333", lw=0.8)
    lab = [f"{a}年{b}月" if b in (1,) else (f"{b}月" if b in (4, 7, 10) else "") for a, b in zip(mm["year"], mm["month"])]
    ax.set_xticks(t); ax.set_xticklabels(lab, fontsize=8, rotation=0)
    ax.set_ylabel("2019年の同じ月＝100")
    ax.set_ylim(0, 200)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False, ncol=2)
    fig.suptitle("訪日客が2019年を大きく上回っても、百貨店の販売額は2019年の前後にとどまった", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"2023年1月〜2026年9月の{m['H3_n_months']}か月。訪日外客数と百貨店の合計の相関 {m['H3_corr']:.2f}（2024年以降に絞ると {m['robust']['3. 2024年1月以降に絞る|H3']:.2f}）", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig3_monthly_vs2019.png", S_METI + "、日本政府観光局「訪日外客数」（2026年の一部は推計値）")

    # fig4 大都市のある都道府県とそれ以外
    rg = pd.read_csv(R / "region_groups.csv")
    rg = rg[rg["year"].isin([2018, 2019, 2023, 2024, 2025])]
    b19 = rg[rg["year"] == 2019].iloc[0]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.84, bottom=0.2)
    x = np.arange(len(rg)); w = 0.38
    vb = rg["big"] / b19["big"] * 100; vr = rg["rest"] / b19["rest"] * 100
    ax.bar(x - w / 2, vb, width=w, color=C1, label="大都市のある9都道府県（北海道・東京・神奈川・愛知・京都・大阪・兵庫・広島・福岡）")
    ax.bar(x + w / 2, vr, width=w, color=GR, label="それ以外（全国 − 9都道府県）")
    for xi, a, b in zip(x, vb, vr):
        ax.text(xi - w / 2, a + 1, f"{a:.0f}", ha="center", fontsize=9)
        ax.text(xi + w / 2, b + 1, f"{b:.0f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in rg["year"]])
    ax.set_ylabel("2019年＝100"); ax.set_ylim(0, 125)
    ax.legend(loc="lower left", fontsize=8.5, frameon=True, framealpha=0.9)
    ax.set_xlabel("百貨店の年の販売額（名目）")
    fig.suptitle(f"大都市のある都道府県は2019年比 {m['H4_big_pct']:+.1f}%、それ以外は {m['H4_rest_pct']:+.1f}%", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"9都道府県の全国に占める割合は {m['big_share_2019_pct']:.1f}% → {m['big_share_2025_pct']:.1f}%。宮城県は百貨店の値が秘匿のため「それ以外」に入る", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig4_region_groups.png", S_METI + "（時系列データ、参考表（年報））")


if __name__ == "__main__":
    main()
