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
S = "内閣府「機械受注統計調査」「四半期別GDP速報」"
C1, C2, C3, GR = "#2a6f97", "#e07a2d", "#5a9e5a", "#8c8c8c"


def save(fig, name, src=S):
    fig.text(0.01, 0.01, "出典：" + src + "をもとに作成者が加工して作成", fontsize=8, color="#555555", ha="left", va="bottom")
    fig.savefig(F / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def qdate(labels):
    return pd.to_datetime([f"{l[:4]}-{(int(l[-1]) - 1) * 3 + 2:02d}-15" for l in labels]).values


def main():
    m = json.loads((R / "main.json").read_text(encoding="utf-8"))
    rq = json.loads((R / "requestion.json").read_text(encoding="utf-8"))
    q = pd.read_csv(R / "quarterly_panel.csv").set_index("t")
    q["cy"] = np.log(q["capex_nominal"] / q["capex_nominal"].shift(4)) * 100
    q["oy"] = np.log(q["core"] / q["core"].shift(4)) * 100
    z = q.dropna(subset=["oy"])

    # fig1 前年同期比の動き
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.84, bottom=0.16)
    x = qdate(z["label"])
    ax.plot(x, z["oy"], color=C2, lw=2, label="機械受注（船舶・電力を除く民需）")
    ax.plot(x, z["cy"], color=C1, lw=2.4, label="設備投資（GDP の民間企業設備、名目）")
    ax.axhline(0, color="#444444", lw=0.8)
    ax.set_ylabel("前年の同じ四半期との比（%、対数の差×100）"); ax.set_xlabel("年")
    ax.grid(axis="y", color="#dddddd"); ax.legend(loc="lower left", fontsize=9, frameon=False)
    fig.suptitle(f"機械受注と設備投資の山と谷はほぼ重なる。受注の振れは約{m['sd_yoy_orders']/m['sd_yoy_capex']:.1f}倍", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"季節調整済。前年同期比の標準偏差は受注{m['sd_yoy_orders']:.1f}、設備投資{m['sd_yoy_capex']:.1f}（ポイント）。{m['period']}", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig1_yoy_lines.png")

    # fig2 ずれごとの相関（四半期・月）
    lq = pd.read_csv(R / "lag_corr_quarterly.csv")
    lm = pd.read_csv(R / "lag_corr_monthly.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.2))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.8, bottom=0.17, wspace=0.25)
    ax = axes[0]
    w = 0.38
    ax.bar(lq["lag_q"] - w / 2, lq["corr_yoy"], width=w, color=C1, label="前年同期比どうし")
    ax.bar(lq["lag_q"] + w / 2, lq["corr_qoq"], width=w, color=C2, label="前期比どうし")
    ax.axhline(0, color="#444444", lw=0.8)
    ax.set_xlabel("受注を何四半期前にずらしたか"); ax.set_ylabel("設備投資との相関")
    ax.set_title("四半期で見る", fontsize=11); ax.legend(loc="upper right", fontsize=9, frameon=False)
    ax.set_ylim(-0.2, 1); ax.grid(axis="y", color="#dddddd")
    ax = axes[1]
    ax.plot(lm["lag_months"], lm["corr"], color=C1, lw=2.2, marker="o", ms=4)
    ax.set_xlabel("受注を何か月前にずらしたか（3か月平均の中心の月）"); ax.set_title("月で見る（前年同月比どうし）", fontsize=11)
    ax.set_ylim(-0.2, 1); ax.grid(axis="y", color="#dddddd"); ax.set_xticks(range(0, 13, 2))
    ax.annotate(f"最大 {m['month_best_corr']:.2f}（{m['month_best_lag']}か月）", (m["month_best_lag"], m["month_best_corr"]), textcoords="offset points", xytext=(10, 10), fontsize=9)
    fig.suptitle(f"先取りは長くても1四半期ほど。受注を0〜4か月ずらした相関はほとんど同じ", fontsize=13, x=0.02, ha="left")
    fig.text(0.02, 0.875, f"四半期の前年同期比：ずれ0で{m['H1_corr_by_lag']['0']:.2f}、1で{m['H1_corr_by_lag']['1']:.2f}、2で{m['H1_corr_by_lag']['2']:.2f}、4で{m['H1_corr_by_lag']['4']:.2f}。前期比どうしは同じ期の{m['H2_max_corr_qoq']:.2f}が最大", fontsize=9.5, color="#444444")
    save(fig, "fig2_lag_corr.png")

    # fig3 8年の窓での相関（問い直し）
    rw = pd.read_csv(R / "requestion_rolling_lag.csv")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.82, bottom=0.17)
    xx = qdate(rw["end_label"])
    for k, col in [(0, C1), (1, C2), (2, C3)]:
        ax.plot(xx, rw[f"corr_lag{k}"], color=col, lw=2.2, label=f"ずれ{k}四半期（受注が{k}期前）")
    ax.set_ylim(0, 1); ax.grid(axis="y", color="#dddddd")
    ax.set_xlabel("8年（32四半期）の窓の終わりの期"); ax.set_ylabel("前年同期比どうしの相関")
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    fig.suptitle("受注が1期先行する形は、リーマン・ショックの時期を窓に含むときにはっきり出ていた", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"窓の終わりが{rq['first_window_end']}では1期のずれが最大（{rq['first_window_best_corr']:.2f}）。2008〜09年が窓から外れる2018年ごろに相関が下がり、{rq['last_window_end']}では同じ期が最大（{rq['last_window_best_corr']:.2f}）", fontsize=9, loc="left", color="#444444")
    save(fig, "fig3_rolling_lag.png")

    # fig4 受注 ÷ 設備投資
    cv = pd.read_csv(R / "requestion_coverage.csv")
    fig, ax = plt.subplots(figsize=(9, 5.2))
    fig.subplots_adjust(left=0.09, right=0.9, top=0.82, bottom=0.17)
    ax.plot(cv["year"], cv["ratio_pct"], color=C1, lw=2.4, marker="o", ms=4, label="受注 ÷ 設備投資（左の目盛り）")
    ax.set_ylabel("機械受注 ÷ 設備投資（名目、%）"); ax.set_xlabel("年"); ax.set_ylim(0, 14)
    ax.set_xticks(range(2006, 2026, 2))
    ax.grid(axis="y", color="#dddddd")
    ax2 = ax.twinx()
    ax2.plot(cv["year"], cv["capex_tn"], color=GR, lw=1.5, ls="--", label="設備投資（右、兆円）")
    ax2.plot(cv["year"], cv["orders_tn"] * 10, color=C2, lw=1.5, ls=":", label="機械受注×10（右、兆円）")
    ax2.set_ylabel("兆円"); ax2.set_ylim(0, 140)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=9, frameon=False)
    fig.suptitle(f"設備投資に対する機械受注の大きさは{rq['ratio_2006']:.1f}%（2006年）から{rq['ratio_2025']:.1f}%（2025年）へ下がった", fontsize=13, x=0.02, ha="left")
    ax.set_title(f"受注は{rq['orders_2006_tn']:.1f}兆円→{rq['orders_2025_tn']:.1f}兆円とほぼ横ばい、設備投資は{rq['capex_2006_tn']:.1f}兆円→{rq['capex_2025_tn']:.1f}兆円。どちらも名目", fontsize=9.5, loc="left", color="#444444")
    save(fig, "fig4_coverage.png")


if __name__ == "__main__":
    main()
