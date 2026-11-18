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
S = "経済産業省「生産動態統計」、財務省「貿易統計」"
C1, C2, C3, C4, C5, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#9b5fa5", "#c9a227", "#8c8c8c"


def save(fig, name):
    fig.text(0.01, 0.01, "出典：" + S + "をもとに作成者が加工して作成", fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    rq = json.loads((R / "requestion.json").read_text(encoding="utf-8"))
    t = pd.read_csv(R / "annual_panel.csv", index_col=0)
    yrs = list(t.index)

    # fig1 生産と輸出の額、輸出の割合
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.9, top=0.83, bottom=0.16)
    ax.bar(t.index, t["prod_oku"], color="#c9d9e6", label="生産金額（部品・付帯装置を含む）")
    ax.bar(t.index, t["exp_oku"], color=C1, width=0.55, label="輸出額（HS 8479.50＋8428.70）")
    ax.set_ylabel("億円"); ax.set_xlabel("年"); ax.set_xticks(range(2009, 2026, 2)); ax.set_ylim(0, 8000)
    ax2 = ax.twinx()
    ax2.plot(t.index, t["ratio_pct"], color=C2, lw=2.4, marker="o", ms=4, label="輸出 ÷ 生産（%、右の軸）")
    ax2.set_ylim(0, 80); ax2.set_ylabel("輸出 ÷ 生産（%）")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, frameon=False)
    ax.grid(axis="y", color="#dddddd")
    fig.suptitle(f"輸出は生産金額の約4割。割合は2009〜12年平均{m['ratio_mean_2009_2012']:.0f}%から2022〜25年平均{m['ratio_mean_2022_2025']:.0f}%へ", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"産業用ロボット。2025年は生産{m['prod_2025_oku']:,.0f}億円、輸出{m['exp_2025_oku']:,.0f}億円（{m['ratio_2025_pct']:.1f}%）。最も高いのは{m['ratio_max_year']}年の{m['ratio_max']:.1f}%",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_production_exports.png")

    # fig2 前年比
    z = t.loc[2010:]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    ax.plot(z.index, z["dl_prod"], color=C1, lw=2.6, marker="o", ms=4, label="生産金額")
    ax.plot(z.index, z["dl_exp"], color=C2, lw=2.2, marker="s", ms=4, label="輸出額")
    ax.plot(z.index, z["dl_rest"], color=C3, lw=1.8, ls="--", label="生産 − 輸出（国内向けなどの残り）")
    ax.axhline(0, color="#444444", lw=0.8)
    ax.set_ylabel("前年比（%、対数の差×100）"); ax.set_xlabel("年"); ax.set_xticks(range(2010, 2026, 2))
    ax.grid(axis="y", color="#dddddd"); ax.legend(loc="upper right", fontsize=9, frameon=False)
    fig.suptitle(f"生産と輸出は同じ向きに動く（前年比の相関{m['corr_dl_2010_2025']:.2f}）。ただ「生産 − 輸出」も同じように動く", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"2010〜2025年。生産と「生産 − 輸出」の相関は{m['corr_dl_rest_2010_2025']:.2f}。同じ向きに動いた年は{m['n_years_corr']}年のうち{m['same_sign_years']}年",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig2_yoy.png")

    # fig3 輸出先の割合
    bc = pd.read_csv(R / "exports_share_by_country.csv")
    keys = [(105, "中国", C2), (304, "米国", C1), (209, "ルクセンブルク", C4), (103, "韓国", C3), (207, "オランダ", C5)]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.78, top=0.83, bottom=0.16)
    bottom = pd.Series(0.0, index=yrs)
    for code, lab, col in keys:
        s = bc[bc["country"] == code].set_index("year")["share_pct"].reindex(yrs).fillna(0)
        ax.bar(yrs, s, bottom=bottom, color=col, label=lab); bottom += s
    ax.bar(yrs, 100 - bottom, bottom=bottom, color="#d9d9d9", label="その他")
    ax.set_ylim(0, 100); ax.set_ylabel("輸出額に占める割合（%）"); ax.set_xlabel("年"); ax.set_xticks(range(2009, 2026, 2))
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9, frameon=False)
    cs = m["china_share"]
    fig.suptitle(f"輸出先の1位は{m['china_top_from']}年から中国。割合は{cs['2009']:.0f}%（2009年）→ {cs['2021']:.0f}%（2021年）→ {cs['2025']:.0f}%（2025年）", fontsize=12.5, x=0.02, ha="left")
    ax.set_title("HS 8479.50＋8428.70 の輸出額の国別の割合。仕向け地（届け先として申告された国）で数える", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig3_destinations.png")

    # fig4 1台あたりの額
    u = pd.read_csv(R / "requestion_unit_value.csv", index_col=0)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    ax.plot(u.index, u["prod_unit_value_man"], color=C1, lw=2.4, marker="o", ms=4, label="生産1台あたり（プレイバック・数値制御ロボット）")
    ax.plot(u.index, u["exp_unit_value_man"], color=C2, lw=2.4, marker="s", ms=4, label="輸出1台あたり（HS 8479.50＋8428.70）")
    ax.set_ylim(0, 500); ax.set_ylabel("万円／台"); ax.set_xlabel("年"); ax.set_xticks(range(2009, 2026, 2))
    ax.grid(axis="y", color="#dddddd"); ax.legend(loc="upper right", fontsize=9, frameon=False)
    fig.suptitle(f"輸出1台あたりの額は、生産1台あたりの約半分（2009〜2025年の平均{rq['ratio_unit_value_mean']:.2f}倍）", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"2025年は生産{rq['prod_unit_value_2025']:.0f}万円、輸出{rq['exp_unit_value_2025']:.0f}万円（{rq['ratio_unit_value_2025']:.2f}倍）。台数で見た輸出の割合が金額より大きいのは、この差による",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig4_unit_value.png")


if __name__ == "__main__":
    main()
