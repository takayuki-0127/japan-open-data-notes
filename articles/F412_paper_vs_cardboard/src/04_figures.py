"""図を4枚つくる（PNG、日付などのメタデータを入れない）。"""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = "Noto Sans CJK JP"
ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
S = "経済産業省「生産動態統計」年報（e-Stat 掲載分）"
C1, C2, C3, C4, C5, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#9b5fa5", "#c9a227", "#8c8c8c"


def save(fig, name):
    fig.text(0.01, 0.01, "出典：" + S + "をもとに作成者が加工して作成", fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    rq = json.loads((R / "requestion.json").read_text(encoding="utf-8"))
    a = pd.read_csv(D / "annual.csv", index_col=0)
    P = lambda s: a[f"production__{s}"] / 1e4
    g = m["grades"]

    # fig1 紙の品種別（積み上げ）
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.78, top=0.83, bottom=0.16)
    parts = [("printing_info", "印刷・情報用紙", C1), ("newsprint", "新聞巻取紙", C2), ("sanitary", "衛生用紙", C3),
             ("wrapping", "包装用紙", C5), ("misc_paper", "雑種紙", GR)]
    ax.stackplot(a.index, *[P(s) for s, _, _ in parts], colors=[c for _, _, c in parts], labels=[l for _, l, _ in parts], alpha=0.9)
    ax.set_ylabel("生産量（万t）"); ax.set_xlabel("年"); ax.grid(axis="y", color="#dddddd")
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9, frameon=False)
    ax.set_xlim(2008, 2025)
    fig.suptitle(f"紙の生産は2008年から2025年に{(1 - g['paper_total']['ratio_2025_2008']) * 100:.0f}%減った。減少の{m['share_newsprint_printing_in_decline'] * 100:.0f}%は新聞と印刷・情報用紙", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"紙計 {g['paper_total']['v2008'] / 1e4:.0f}万t → {g['paper_total']['v2025'] / 1e4:.0f}万t。衛生用紙は{g['sanitary']['v2008'] / 1e4:.0f}万t → {g['sanitary']['v2025'] / 1e4:.0f}万t でほぼ横ばい",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_paper_by_grade.png")

    # fig2 紙・板紙・段ボール原紙
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.83, bottom=0.16)
    ax.plot(a.index, P("paper_total"), color=C1, lw=2.4, label="紙計")
    ax.plot(a.index, P("board_total"), color=C3, lw=2.2, label="板紙計")
    ax.plot(a.index, P("containerboard"), color=C2, lw=2.4, label="うち段ボール原紙（ライナー＋中芯）")
    pk = g["containerboard"]["peak_year"]
    ax.scatter([pk], [g["containerboard"]["peak_value"] / 1e4], color=C2, zorder=3)
    ax.annotate(f"最大 {pk}年 {g['containerboard']['peak_value'] / 1e4:.0f}万t", (pk, g["containerboard"]["peak_value"] / 1e4),
                xytext=(2014.3, 1080), fontsize=9, arrowprops=dict(arrowstyle="-", color=GR))
    ax.set_xticks(range(2008, 2026, 2))
    ax.set_ylim(0, 2000); ax.set_ylabel("生産量（万t）"); ax.set_xlabel("年"); ax.grid(axis="y", color="#dddddd")
    ax.legend(loc="upper right", fontsize=9, frameon=False)
    fig.suptitle(f"段ボール原紙は{pk}年まで少し増え、その後は減った。2025年は2008年の{g['containerboard']['ratio_2025_2008'] * 100:.0f}%", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"段ボール原紙 {g['containerboard']['v2008'] / 1e4:.0f}万t（2008年）→ {g['containerboard']['v2025'] / 1e4:.0f}万t（2025年）。板紙が紙を上回ったのは{m['year_board_exceeds_paper']}年から",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig2_paper_vs_board.png")

    # fig3 通販・宅配・引越用
    u = pd.read_csv(R / "mailorder_share.csv")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.9, top=0.83, bottom=0.16)
    ax.bar(u["year"], u["use_mailorder"] / 1e5, color=C2, alpha=0.85, label="通販・宅配・引越用の消費（億㎡、左の軸）")
    ax.set_ylabel("通販・宅配・引越用（億㎡）"); ax.set_xlabel("年"); ax.set_ylim(0, 7)
    ax.set_xticks(range(2008, 2026, 2))
    ax2 = ax.twinx()
    ax2.plot(u["year"], u["mailorder_share_pct"], color=C1, lw=2.4, marker="o", ms=4, label="段ボールの消費全体に占める割合（%、右の軸）")
    ax2.set_ylim(0, 7); ax2.set_ylabel("割合（%）")
    ax.axvline(2013.5, color=GR, ls="--", lw=1)
    ax.text(2013.6, 6.6, "2013→2014年に段ボール側だけ段差", fontsize=8.5, color="#555555")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=9, frameon=False)
    ax.grid(axis="y", color="#dddddd")
    fig.suptitle(f"通販・宅配・引越用は{m['mailorder_ratio_2025_2008']:.1f}倍に。それでも段ボールの使い道の{m['mailorder_share_2025']:.1f}%", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"段ボールの消費（次工程投入）の部門別内訳。割合は2008年{m['mailorder_share_2008']:.1f}%、2014年{m['mailorder_share_2014']:.1f}%、2025年{m['mailorder_share_2025']:.1f}%",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig3_mailorder_share.png")

    # fig4 使い道ごとの増減（2014→2025）
    t = pd.read_csv(R / "requestion_use_change.csv").sort_values("change_2014_2025")
    fig, ax = plt.subplots(figsize=(9, 5.4))
    fig.subplots_adjust(left=0.30, right=0.95, top=0.83, bottom=0.15)
    cols = [C2 if u_ == "use_mailorder" else (C1 if v > 0 else GR) for u_, v in zip(t["use"], t["change_2014_2025"])]
    ax.barh(t["name_ja"], t["change_2014_2025"] / 1e5, color=cols)
    ax.axvline(0, color="#444444", lw=0.8)
    for y_, v in enumerate(t["change_2014_2025"] / 1e5):
        ax.text(v + (0.05 if v >= 0 else -0.05), y_, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    ax.set_xlabel("2014年から2025年の増減（億㎡）"); ax.grid(axis="x", color="#dddddd")
    ax.set_xlim(-2, 6.5)
    pf = rq["uses"]["use_processed_food"]; mo = rq["uses"]["use_mailorder"]
    fig.suptitle(f"段ボールの使い道で、いちばん増えたのは加工食品用（飲料を含む）。増えた分の{rq['use_processed_food_share_of_increases'] * 100:.0f}%", fontsize=12.5, x=0.02, ha="left")
    ax.set_title(f"段ボールの消費の合計は{rq['total_2014'] / 1e5:.1f}億㎡ → {rq['total_2025'] / 1e5:.1f}億㎡。通販・宅配・引越用は増えた分の{rq['use_mailorder_share_of_increases'] * 100:.0f}%",
                 fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig4_use_change.png")


if __name__ == "__main__":
    main()
