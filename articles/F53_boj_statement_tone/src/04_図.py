"""04_図：記事の図を作る"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import RES, FIG, RAW, POS, NEG

C_D, C_E, C_CI, C_G = "#2a6fb0", "#d0672b", "#555555", "#e3e3e3"


def shade(ax):
    c = pd.read_csv(RAW / "cycle_dates.csv")
    c["month"] = pd.to_datetime(c.month + "-01")
    pk = c[c.type == "peak"].month.tolist()
    tr = c[c.type == "trough"].month.tolist()
    for p in pk:
        t = [x for x in tr if x > p]
        if p.year >= 2007 and t:
            ax.axvspan(max(p, pd.Timestamp("2008-06-01")), t[0], color=C_G, zorder=0, lw=0)


def main():
    t = pd.read_csv(RES / "meeting_scores.csv", parse_dates=["date", "month"])
    k = json.load(open(RES / "key_numbers.json"))
    ci = pd.read_csv(RAW / "f13_ci.csv", parse_dates=["month"]).set_index("month")
    ci12 = (ci.ci_coin.pct_change(12, fill_method=None) * 100).loc["2008-01":]

    # 1 時系列
    fig, ax = plt.subplots(figsize=(10, 4.6))
    shade(ax)
    ax.plot(t.date, t.smooth_dict, color=C_D, lw=2, label="辞書法（直近3会合の平均）")
    ax.plot(t.date, t.smooth_emb_z / 2, color=C_E, lw=2, label="埋め込み（標準化÷2、直近3会合の平均）")
    ax.scatter(t.date, t.score, s=8, color=C_D, alpha=0.35)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylim(-1.3, 1.3)
    ax.set_ylabel("弱気 ←  スコア  → 強気")
    ax2 = ax.twinx()
    ax2.plot(ci12.index, ci12.values, color=C_CI, lw=1, ls="--", label="景気動向指数（一致）12か月前比")
    ax2.set_ylabel("CI 一致 12か月前比（%）", color=C_CI)
    ax2.set_ylim(-35, 35)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="lower right", fontsize=8, frameon=False)
    ax.set_title("日銀の公表文の景気判断：強気・弱気のスコア（灰色は景気後退期）", fontsize=11)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(FIG / "f53_timeline.png")
    plt.close(fig)

    # 2 語の数（年ごと）
    W = pd.read_csv(RES / "word_counts_by_year.csv", index_col=0)
    top_p = W[POS].sum().sort_values(ascending=False).head(5).index.tolist()
    top_n = W[NEG].sum().sort_values(ascending=False).head(5).index.tolist()
    nm = t.groupby(t.date.dt.year).size()
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, ws, ttl, cmap in ((axs[0], top_p, "強気の語（多い順に5つ）", "Blues"), (axs[1], top_n, "弱気の語（多い順に5つ）", "Oranges")):
        per = W[ws].div(nm, axis=0)
        bottom = np.zeros(len(per))
        cols = plt.get_cmap(cmap)(np.linspace(0.85, 0.35, len(ws)))
        for w, c in zip(ws, cols):
            ax.bar(per.index, per[w], bottom=bottom, color=c, label=w, width=0.8)
            bottom += per[w].values
        ax.set_title(ttl, fontsize=10)
        ax.legend(fontsize=8, frameon=False, loc="upper left", ncol=2)
        ax.set_xticks(per.index[::2])
        ax.tick_params(axis="x", labelsize=8, rotation=45)
    axs[0].set_ylabel("1会合あたりの出現回数")
    fig.suptitle("景気の現状判断の文に出てきた語", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "f53_words.png")
    plt.close(fig)

    # 3 辞書法と埋め込みの比較
    fig, ax = plt.subplots(figsize=(6.2, 4.8))
    rec = t.recession == 1
    ax.scatter(t.score[~rec], t.score_emb_z[~rec], s=18, color=C_D, alpha=0.7, label="拡張期")
    ax.scatter(t.score[rec], t.score_emb_z[rec], s=22, color=C_E, alpha=0.9, label="後退期")
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("辞書法のスコア（−1〜+1）")
    ax.set_ylabel("埋め込みのスコア（標準化）")
    ax.set_title(f"2つの測り方の一致（{len(t)}会合、相関 {k['dict_emb_corr']:.2f}）", fontsize=11)
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "f53_scatter.png")
    plt.close(fig)

    # 4 景気との時間のずれ
    L = pd.read_csv(RES / "lag_corr.csv")
    L = L[L.h.astype(str) == "12"]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(L.k, L.r_dict, marker="o", color=C_D, label="辞書法")
    ax.plot(L.k, L.r_emb, marker="s", color=C_E, label="埋め込み")
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xticks(range(-6, 7))
    ax.set_xlabel("景気動向指数を比べる月（会合の月から何か月ずれるか。マイナス＝過去）")
    ax.set_ylabel("相関係数")
    ax.set_ylim(0, 0.5)
    ax.set_title("スコアと、景気動向指数（一致）12か月前比の相関", fontsize=11)
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "f53_lag.png")
    plt.close(fig)

    # 5 金利・株価
    tl = pd.read_csv(RAW / "f18_topix_longrate.csv", parse_dates=["month"]).set_index("month").loc["2008-01":]
    cr = pd.read_csv(RAW / "f43_boj_callrate.csv", encoding="utf-8-sig")
    cr["month"] = pd.to_datetime(cr.date.astype(str) + "01")
    cr = cr.set_index("month").value.loc["2008-01":]
    fig, axs = plt.subplots(2, 1, figsize=(10, 5.6), sharex=True)
    ax = axs[0]
    shade(ax)
    ax.plot(t.date, t.smooth_dict, color=C_D, lw=2, label="辞書法のスコア（直近3会合）")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("スコア")
    a2 = ax.twinx()
    a2.plot(cr.index, cr.values, color="#7a3d9a", lw=1.4, label="無担保コールレート")
    a2.plot(tl.index, tl["長期金利"], color="#7a3d9a", lw=1, ls=":", label="長期金利")
    a2.set_ylabel("金利（%）")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, frameon=False, loc="upper left")
    jumps = cr[cr.diff() > 0.08].index    # コールレートが前月より 0.08%ポイント超上がった月（利上げ）
    for d in jumps:
        ax.axvline(d, color="#7a3d9a", lw=0.8, alpha=0.6)
    ax = axs[1]
    shade(ax)
    ax.plot(t.date, t.smooth_dict, color=C_D, lw=2, label="辞書法のスコア（直近3会合）")
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("スコア")
    a3 = ax.twinx()
    a3.plot(tl.index, tl["株価（TOPIX）"], color="#2b8a3e", lw=1.2, label="TOPIX（月次）")
    a3.set_ylabel("TOPIX")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = a3.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, frameon=False, loc="upper left")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axs[0].set_title("スコアと金利（上、縦線はコールレートが上がった月）・株価（下）", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / "f53_rates.png")
    plt.close(fig)

    # 6 頑健性
    R = pd.read_csv(RES / "robustness.csv")
    fig, ax = plt.subplots(figsize=(8.5, 5))
    y = np.arange(len(R))[::-1]
    ax.barh(y + 0.18, R.r_ci12_known, height=0.36, color=C_D, label="会合の時点の景気（2か月前の12か月前比）")
    ax.barh(y - 0.18, R.r_ci12_after6, height=0.36, color=C_E, label="6か月後の景気（12か月前比）")
    ax.set_yticks(y)
    ax.set_yticklabels(R.variant, fontsize=8)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("スコアとの相関係数")
    ax.set_title("作り方を変えたときの、景気との相関", fontsize=11)
    ax.legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(0.0, -0.12), ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "f53_robust.png")
    plt.close(fig)
    print("figures done")


if __name__ == "__main__":
    main()
