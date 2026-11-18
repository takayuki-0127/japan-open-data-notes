"""図を4枚つくる（PNG、日付などのメタデータを入れない）。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
S = "財務省「法人企業統計調査」（四半期別調査、時系列データ）"
C1, C2, C3, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#8c8c8c"


def save(fig, name):
    fig.text(0.01, 0.01, "出典：" + S + "をもとに作成者が加工して作成", fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def base(ax):
    ax.axhline(1.0, color="#444444", lw=1)
    ax.axhspan(1.0, 1.2, color="#eeeeee", zorder=0)
    ax.grid(axis="y", color="#dddddd")
    ax.set_xlabel("年度")


def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    rq = json.loads((R / "requestion.json").read_text(encoding="utf-8"))
    d = pd.read_csv(R / "ratio_by_year.csv")
    A = d[(d["ind"] == "all") & (d["size"] == "A")]

    # fig1 長期の比
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    ax.plot(A["fy"], A["R_exsw"], color=C1, lw=2.2, label="ソフトウェアを除く設備投資 ÷ 減価償却費")
    z = A.dropna(subset=["R_sw"])
    ax.plot(z["fy"], z["R_sw"], color=C2, lw=2.2, label="ソフトウェアを含む設備投資 ÷ 減価償却費")
    base(ax)
    ax.text(1956, 1.08, "灰色の帯：1.0〜1.2（ほぼ減価償却並み）", fontsize=9, color="#555555")
    ax.set_ylabel("設備投資 ÷ 減価償却費（倍）")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    p = {x["period"]: x for x in m["periods"]}
    fig.suptitle(f"設備投資は、1990年度までは減価償却の約{m['R_exsw_1954_1990_mean']:.1f}倍。2002〜2012年度は約{p['2002-2012']['R_sw_mean']:.2f}倍まで下がった", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"全産業（金融業・保険業を除く）・全規模、年度。2025年度はソフトウェアを含めて{m['R_sw_2025']:.2f}倍", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_ratio_long.png")

    # fig2 規模別
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    for size, lab, c in [("B", "資本金10億円以上", C1), ("C", "1億〜10億円", C3), ("D", "1千万〜1億円", C2)]:
        z = d[(d["ind"] == "all") & (d["size"] == size)].dropna(subset=["R_sw"])
        ax.plot(z["fy"], z["R_sw"], color=c, lw=2.2, label=lab)
    base(ax)
    ax.set_ylabel("設備投資（ソフトウェアを含む）÷ 減価償却費（倍）")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    h3 = m["H3"]
    fig.suptitle(f"資本金1億円未満の会社は、減価償却並みに近い（2002〜2025年度の平均{h3['R_D']:.2f}倍）", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"全産業（金融業・保険業を除く）。平均は10億円以上{h3['R_B']:.2f}倍、1億〜10億円{h3['R_C']:.2f}倍", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig2_by_size.png")

    # fig3 製造業と非製造業
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    for ind, lab, c in [("mfg", "製造業", C1), ("nonmfg", "非製造業（金融業・保険業を除く）", C2)]:
        z = d[(d["ind"] == ind) & (d["size"] == "A")].dropna(subset=["R_sw"])
        ax.plot(z["fy"], z["R_sw"], color=c, lw=2.2, label=lab)
    base(ax)
    ax.set_ylabel("設備投資（ソフトウェアを含む）÷ 減価償却費（倍）")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    h4 = m["H4"]
    t = {(x["ind"], x["size"]): x for x in m["by_size_industry"]}
    fig.suptitle(f"2021〜2025年度は、製造業も非製造業も2011〜2015年度より比が高い", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"全規模。全産業では{h4['R_2011_2015']:.2f}倍 → {h4['R_2021_2025']:.2f}倍。製造業 {t[('mfg','A')]['R_sw_2011_2015']:.2f} → {t[('mfg','A')]['R_sw_2021_2025']:.2f}、"
                 f"非製造業 {t[('nonmfg','A')]['R_sw_2011_2015']:.2f} → {t[('nonmfg','A')]['R_sw_2021_2025']:.2f}", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig3_mfg_nonmfg.png")

    # fig4 帳簿の設備の残高
    s = pd.read_csv(R / "requestion_stock.csv")
    z = s[(s["ind"] == "all") & (s["size"] == "A") & (s["fy"] >= 1974)]
    g = rq["all_A"]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    ax.plot(z["fy"], z["stock_oku"] / 1e4, color=C1, lw=2.4)
    ax.scatter([1998, 2025], [g["stock_1998_tril"], g["stock_2025_tril"]], color=C2, zorder=3)
    ax.annotate(f"1998年度 {g['stock_1998_tril']:.0f}兆円", (1998, g["stock_1998_tril"]), xytext=(1986, 330), fontsize=9,
                arrowprops=dict(arrowstyle="-", color=GR))
    ax.annotate(f"2025年度 {g['stock_2025_tril']:.0f}兆円", (2025, g["stock_2025_tril"]), xytext=(2013, 335), fontsize=9,
                arrowprops=dict(arrowstyle="-", color=GR))
    ax.set_ylim(0, 360)
    ax.grid(axis="y", color="#dddddd"); ax.set_xlabel("年度")
    ax.set_ylabel("土地を除く有形固定資産＋建設仮勘定（兆円、年度末）")
    fig.suptitle("帳簿の上の設備の残高は、2025年度でも1998年度とほぼ同じ", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"全産業（金融業・保険業を除く）・全規模。2003〜2025年度の純投資（ソフトウェアを除く）の合計{g['cum_net_exsw_2003_2025_tril']:.0f}兆円に対し、"
                 f"残高は{g['stock_change_2002_2025_tril']:.0f}兆円増", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig4_book_stock.png")


if __name__ == "__main__":
    main()
