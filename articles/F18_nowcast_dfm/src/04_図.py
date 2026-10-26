"""04 図：figures/ に6枚"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import RES, FIG, DATA, SERIES

FIG.mkdir(exist_ok=True)
C_DFM, C_AR, C_MEAN, C_ACT = "#1a73e8", "#9aa0a6", "#e37400", "#202124"
VN = ["1か月目", "2か月目", "3か月目", "翌月"]


def shade(ax, rec):
    r = rec.astype(bool)
    start = None
    for t, v in r.items():
        if v and start is None:
            start = t
        if not v and start is not None:
            ax.axvspan(start, t, color="#dadce0", alpha=0.7, lw=0); start = None
    if start is not None:
        ax.axvspan(start, r.index[-1], color="#dadce0", alpha=0.7, lw=0)


def fig1():
    f = pd.read_csv(RES / "factor_full.csv", parse_dates=["month"], index_col="month")["factor"]
    rec = pd.read_csv(RES / "recession_months.csv", parse_dates=["month"], index_col="month")["recession"]
    lev = pd.read_csv(DATA / "raw" / "f13_monthly.csv", parse_dates=["month"], index_col="month")
    ci = 100 * np.log(lev["ci_coin"]).diff().loc[f.index.min():]
    ci3 = ci.rolling(3).mean(); ci3 = (ci3 - ci3.mean()) / ci3.std()
    fig, ax = plt.subplots(figsize=(10, 4.6))
    shade(ax, rec)
    ax.plot(f.index, f.rolling(3).mean(), color=C_DFM, lw=1.6, label="共通因子（3か月平均）")
    ax.plot(ci3.index, ci3, color=C_MEAN, lw=1.0, alpha=0.8, label="景気動向指数（一致）の前月比（3か月平均・標準化）")
    ax.axhline(0, color="#5f6368", lw=0.7)
    ax.set_ylim(-6, 3)
    ax.set_title("20の月次統計から取り出した「景気の共通の動き」と景気の後退期（灰色）", fontsize=12)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    ax.text(0.99, 0.02, "灰色：内閣府の景気基準日付の山の翌月〜谷\n2020年4月は −14 前後（図の範囲外）", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#5f6368")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "f18_factor_cycle.png"); plt.close(fig)


def fig2():
    lo = pd.read_csv(RES / "loadings_full.csv", index_col=0)["loading"]
    grp = {s[0]: s[5] for s in SERIES}; grp["GDP"] = "GDP"
    lo = lo.sort_values()
    col = [{"一致": C_DFM, "先行": C_MEAN, "GDP": C_ACT}[grp[i]] for i in lo.index]
    fig, ax = plt.subplots(figsize=(8, 6.8))
    ax.barh(range(len(lo)), lo.values, color=col)
    ax.set_yticks(range(len(lo))); ax.set_yticklabels(lo.index, fontsize=9)
    ax.axvline(0, color="#5f6368", lw=0.7)
    ax.set_title("各統計が共通因子とどれだけ一緒に動くか（因子負荷量）", fontsize=12)
    ax.set_xlabel("因子負荷量（標準化した系列に対する値）")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=C_DFM, label="一致系列"), Patch(color=C_MEAN, label="先行系列"), Patch(color=C_ACT, label="GDP（四半期）")],
              loc="lower right", fontsize=9, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "f18_loadings.png"); plt.close(fig)


def fig3():
    b = pd.read_csv(RES / "nowcast_base.csv")
    live = pd.read_csv(RES / "nowcast_2026Q3.csv")
    qs = [("2008Q4", "2008年10-12月期（リーマン・ショック）"), ("2011Q1", "2011年1-3月期（東日本大震災）"),
          ("2020Q2", "2020年4-6月期（緊急事態宣言）"), ("2025Q3", "2025年7-9月期")]
    fig, axes = plt.subplots(1, 5, figsize=(13, 3.9), sharey=False)
    for ax, (q, lab) in zip(axes, qs):
        x = b[b.q == q].set_index("vint").loc[VN]
        ax.plot(range(4), x.dfm, "-o", color=C_DFM, label="DFM")
        ax.plot(range(4), x.ar, "-o", color=C_AR, label="AR(1)", ms=4)
        ax.axhline(x.actual.iloc[0], color=C_ACT, ls="--", lw=1, label="実績（最新値）")
        ax.set_xticks(range(4)); ax.set_xticklabels(["1か月目\n末", "2か月目\n末", "3か月目\n末", "翌月\n末"], fontsize=8)
        ax.set_title(lab, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("実質GDP 前期比（%）")
    ax = axes[4]
    ax.plot([0, 1], live.DFM, "-o", color=C_DFM); ax.plot([0, 1], live.AR, "-o", color=C_AR, ms=4)
    for i, v in enumerate(live.DFM):
        ax.text(i, v + 0.03, f"{v:+.2f}%", ha="center", fontsize=8, color=C_DFM)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["7月末", "8月末"], fontsize=8); ax.set_xlim(-0.5, 1.5)
    ax.set_title("2026年7-9月期（まだ公表前）", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    lo, hi = live.DFM.min(), live.DFM.max(); ax.set_ylim(0.1, hi + 0.15)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("四半期の中で月が進むと、推定はどう更新されるか", fontsize=12)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(FIG / "f18_updates.png"); plt.close(fig)


def fig4():
    b = pd.read_csv(RES / "nowcast_base.csv")
    x = b[b.vint == "翌月"].copy()
    x["t"] = pd.PeriodIndex(x.q, freq="Q").to_timestamp(how="end")
    y1 = b[b.vint == "1か月目"].copy(); y1["t"] = pd.PeriodIndex(y1.q, freq="Q").to_timestamp(how="end")
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.bar(x.t, x.actual, width=60, color="#dadce0", label="実績（最新の公表値）")
    ax.plot(x.t, x.dfm, "-o", color=C_DFM, ms=3, lw=1.2, label="DFM（四半期の翌月末の時点）")
    ax.plot(y1.t, y1.dfm, "-", color=C_MEAN, lw=0.9, alpha=0.8, label="DFM（1か月目末の時点）")
    ax.axhline(0, color="#5f6368", lw=0.7)
    ax.set_ylim(-8.2, 5.5)
    ax.set_ylabel("実質GDP 前期比（%、対数差）")
    ax.set_title("GDP を公表前に推定する（2008〜2026年、各時点のデータだけで毎回推定し直し）", fontsize=12)
    ax.legend(fontsize=9, frameon=False, loc="upper left", ncol=3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "f18_nowcast_vs_actual.png"); plt.close(fig)


def fig5():
    acc = pd.read_csv(RES / "accuracy.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, lab, ttl in [(axes[0], "基本（20系列・因子1）", "全期間（74四半期）"), (axes[1], "基本・コロナ期を除いて評価", "2020年1-3月期〜2021年4-6月期を除く（68四半期）")]:
        a = acc[acc.設定 == lab].set_index("時点").loc[VN]
        w = 0.27; xs = np.arange(4)
        ax.bar(xs - w, a.RMSE_DFM, w, color=C_DFM, label="DFM")
        ax.bar(xs, a.RMSE_AR, w, color=C_AR, label="AR(1)")
        ax.bar(xs + w, a.RMSE_平均, w, color=C_MEAN, label="過去の平均")
        for i, (v, p) in enumerate(zip(a.RMSE_DFM, a.DM_p)):
            ax.text(i - w, v + 0.02, f"{v:.2f}" + ("*" if p < 0.05 else ""), ha="center", fontsize=8)
        ax.set_xticks(xs); ax.set_xticklabels([v + "末" for v in VN])
        ax.set_title(ttl, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("誤差の大きさ（RMSE、%ポイント）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("月が進むと DFM の誤差は小さくなる（*：AR との差が5%水準で有意、DM 検定）", fontsize=12)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(FIG / "f18_rmse.png"); plt.close(fig)


def fig6():
    acc = pd.read_csv(RES / "accuracy.csv")
    labs = acc.設定.unique().tolist()
    fig, ax = plt.subplots(figsize=(11, 4.6))
    xs = np.arange(len(labs)); w = 0.2
    cols = ["#a8c7fa", "#669df6", "#1a73e8", "#174ea6"]
    for j, v in enumerate(VN):
        r = [acc[(acc.設定 == l) & (acc.時点 == v)].比_DFM対AR.iloc[0] for l in labs]
        ax.bar(xs + (j - 1.5) * w, r, w, color=cols[j], label=v + "末")
    ax.axhline(1, color="#d93025", lw=1, ls="--")
    ax.text(len(labs) - 0.5, 1.02, "AR と同じ", color="#d93025", fontsize=8, ha="right")
    short = {"基本（20系列・因子1）": "基本\n（20系列・因子1）", "基本・コロナ期を除いて評価": "基本\n（コロナ期を除いて評価）",
             "一致系列だけ（10系列）": "一致系列だけ\n（10系列）", "金融の4系列を除く（16系列）": "金融の4系列\nを除く", "因子2つ": "因子2つ", "因子3つ": "因子3つ",
             "2020年3〜12月の月次を欠測にして推定": "2020年3〜12月を\n欠測にして推定", "2020年3〜12月の月次を欠測にして推定・コロナ期を除いて評価": "左と同じ\n（コロナ期を除いて評価）"}
    ax.set_xticks(xs); ax.set_xticklabels([short.get(l, l) for l in labs], fontsize=8)
    ax.set_ylabel("DFM の RMSE ÷ AR(1) の RMSE")
    ax.set_title("2か月目以降は、ほとんどの設定で AR より誤差が2〜4割小さい", fontsize=12)
    ax.legend(fontsize=8, frameon=False, ncol=4, loc="upper left")
    ax.set_ylim(0, 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(FIG / "f18_robustness.png"); plt.close(fig)


if __name__ == "__main__":
    import sys
    for fn in [fig1, fig2, fig3, fig4, fig5, fig6]:
        try:
            fn(); print("ok", fn.__name__)
        except Exception as e:
            print("skip", fn.__name__, e)
