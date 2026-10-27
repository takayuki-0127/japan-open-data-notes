"""図を作る。"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

C1, C3, CO = "#2b6cb0", "#c05621", "#4a5568"


def week_labels():
    w = [(36 + i - 1) % 52 + 1 for i in range(53)]
    return w


def fig_curves():
    obs = pd.read_csv(RES / "observed_curves.csv")
    cur = pd.read_csv(RES / "fitted_curves.csv")
    seasons = obs.columns.tolist()
    fig, axes = plt.subplots(3, 4, figsize=(13, 8), sharex=True)
    x = np.arange(53)
    for ax, s in zip(axes.flat, seasons):
        ax.plot(x, obs[s], "o", ms=2.5, color=CO, label="実際")
        ax.plot(x, cur[f"{s}|M1"], color=C1, lw=1.6, label="SIR 1つ")
        ax.plot(x, cur[f"{s}|M3"], color=C3, lw=1.6, ls="--", label="SIR 2つ＋年末年始")
        ax.set_title(s, fontsize=10)
        ax.set_xlim(5, 40)
        ax.set_xticks([7, 16, 20, 25, 33])
        ax.set_xticklabels(["10月", "12月末", "1月末", "3月", "5月"], fontsize=8)
        ax.grid(alpha=.3)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("インフルエンザの定点当たり報告数（全国・週）と SIR の当てはめ", fontsize=13)
    fig.supylabel("定点当たり報告数")
    fig.tight_layout()
    fig.savefig(FIG / "f57_curves.png", dpi=130)


def fig_reff():
    r = pd.read_csv(RES / "season_fits.csv")
    x = np.arange(len(r))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.plot(x, r["M1_R"], "o-", color=C1, label="SIR 1つの Reff0")
    ax.plot(x, r["M3_R"], "s--", color=C3, label="SIR 2つ：主な山の Reff0")
    ax.plot(x, r["rt_growth_max"], "^:", color=CO, label="立ち上がりの増加率から出した R（3週平均の最大）")
    ax.axhline(1, color="gray", lw=.8)
    ax.axvline(7.5, color="gray", ls=":", lw=1)
    ax.text(7.6, ax.get_ylim()[1] * 0.97 if ax.get_ylim()[1] > 1 else 1.5, "コロナ後", fontsize=9, va="top")
    ax.set_xticks(x); ax.set_xticklabels(r["season"], rotation=45, fontsize=9)
    ax.set_ylabel("再生産数")
    ax.set_title("シーズン初めの実効再生産数（SIR の推定と、増加率からの推定）")
    ax.legend(fontsize=9); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "f57_reff.png", dpi=130)


def fig_peak():
    r = pd.read_csv(RES / "season_fits.csv")
    x = np.arange(len(r)); w = 0.38
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    ax = axes[0]
    ax.bar(x - w / 2, r["M1_peak"] / r["peak_obs"], w, color=C1, label="SIR 1つ")
    ax.bar(x + w / 2, r["M3_peak"] / r["peak_obs"], w, color=C3, label="SIR 2つ＋年末年始")
    ax.axhline(1, color="k", lw=.8)
    ax.set_xticks(x); ax.set_xticklabels(r["season"], rotation=45, fontsize=8)
    ax.set_title("山の高さ（モデル÷実際）"); ax.legend(fontsize=9); ax.grid(alpha=.3, axis="y")
    ax = axes[1]
    ax.bar(x - w / 2, r["M1_rmse"], w, color=C1, label="SIR 1つ")
    ax.bar(x + w / 2, r["M3_rmse"], w, color=C3, label="SIR 2つ＋年末年始")
    ax.set_xticks(x); ax.set_xticklabels(r["season"], rotation=45, fontsize=8)
    ax.set_title("当てはまりのずれ（log の RMSE）"); ax.legend(fontsize=9); ax.grid(alpha=.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "f57_peak.png", dpi=130)


def fig_forecast():
    fc = pd.read_csv(RES / "peak_forecast.csv")
    fc["ok_w"] = fc.week_err.abs() <= 1
    fc["ok_h"] = fc.height_ratio.between(2 / 3, 1.5)
    leads = [6, 4, 2, 0]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for ax, col, ttl in [(axes[0], "ok_w", "山の週を ±1週以内で当てた割合"),
                         (axes[1], "ok_h", "山の高さを 2/3〜1.5倍で当てた割合")]:
        for m, c, lab, mk in [("M1", C1, "SIR 1つ", "o-"), ("M3", C3, "SIR 2つ＋年末年始", "s--")]:
            g = fc[fc.model == m].groupby("lead")[col].mean().reindex(leads)
            ax.plot(range(4), g.values * 100, mk, color=c, label=lab, lw=2)
        ax.set_xticks(range(4)); ax.set_xticklabels(["山の6週前", "4週前", "2週前", "山の週"])
        ax.set_ylim(-3, 103); ax.set_ylabel("%（12シーズン中）")
        ax.set_title(ttl); ax.grid(alpha=.3)
    axes[0].legend(fontsize=9)
    fig.suptitle("その時点までのデータだけで当てはめたとき、山を予測できたか", fontsize=12)
    fig.tight_layout(); fig.savefig(FIG / "f57_forecast.png", dpi=130)


def fig_robust():
    rb = pd.read_csv(RES / "robustness.csv")
    a = rb[rb.M1_R.notna()].groupby("setting")[["M1_R", "M3_R", "M1_peak_ratio"]].median()
    b = rb[rb.rt_max.notna()].groupby("setting")[["rt_max", "rt_med"]].median()
    order = ["基本 D=3日", "D=2日", "D=4日", "SEIR 潜伏1.5日", "log の足し算 0.1", "log の足し算 1.0"]
    a = a.loc[[o for o in order if o in a.index]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    y = np.arange(len(a))
    axes[0].barh(y - 0.2, a["M1_R"], 0.4, color=C1, label="SIR 1つ")
    axes[0].barh(y + 0.2, a["M3_R"], 0.4, color=C3, label="SIR 2つ：主な山")
    axes[0].set_yticks(y); axes[0].set_yticklabels(a.index); axes[0].invert_yaxis()
    axes[0].set_xlim(1.0, max(a.max().max(), 1.6) * 1.05)
    axes[0].set_title("Reff0（12シーズンの中央値）"); axes[0].legend(fontsize=9); axes[0].grid(alpha=.3, axis="x")
    y2 = np.arange(len(b))
    axes[1].barh(y2 - 0.2, b["rt_max"], 0.4, color=CO, label="3週平均の最大")
    axes[1].barh(y2 + 0.2, b["rt_med"], 0.4, color="#a0aec0", label="立ち上がりの中央値")
    axes[1].set_yticks(y2); axes[1].set_yticklabels(b.index); axes[1].invert_yaxis()
    axes[1].set_xlim(1.0, b.max().max() * 1.05)
    axes[1].set_title("増加率から出した R（12シーズンの中央値）"); axes[1].legend(fontsize=9); axes[1].grid(alpha=.3, axis="x")
    fig.tight_layout(); fig.savefig(FIG / "f57_robust.png", dpi=130)


def fig_pref():
    pr = pd.read_csv(RES / "pref_fits.csv")
    seasons = sorted(pr.season.unique())
    fig, ax = plt.subplots(figsize=(10, 4.4))
    data = [pr[pr.season == s]["R"].values for s in seasons]
    ax.boxplot(data, tick_labels=seasons, patch_artist=True)
    ax.set_ylabel("Reff0（SIR 1つ）")
    ax.set_ylim(0.95, 1.5)
    ax.text(0.99, 0.02, "推定が上限（4.0）に張りついた2件は図の外", transform=ax.transAxes, ha="right", fontsize=8, color="gray")
    ax.set_title("都道府県ごとに当てはめた Reff0 のばらつき（コロナ前8シーズン、47都道府県）")
    ax.grid(alpha=.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG / "f57_pref.png", dpi=130)


if __name__ == "__main__":
    for f in [fig_curves, fig_reff, fig_peak, fig_forecast, fig_robust, fig_pref]:
        try:
            f(); print("ok", f.__name__)
        except Exception as e:
            print("skip", f.__name__, e)
