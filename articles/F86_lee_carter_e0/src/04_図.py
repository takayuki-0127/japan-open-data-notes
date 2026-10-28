"""図を作る"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, SEXES, COL


def main():
    long = pd.read_csv(DATA / "mx_long.csv")
    obs = pd.read_csv(DATA / "e0_jmd.csv")
    ipss = pd.read_csv(DATA / "ipss_e0.csv")
    par = pd.read_csv(RES / "lc_params.csv")
    kt = pd.read_csv(RES / "lc_kt.csv")
    fc = pd.read_csv(RES / "forecast_e0.csv")
    bt = pd.read_csv(RES / "backtest.csv")
    rob = pd.read_csv(RES / "robustness.csv")
    bp = pd.read_csv(RES / "b_by_period.csv")

    # 1 年齢別死亡率
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    years = [1950, 1970, 1990, 2010, 2024]
    cmap = plt.get_cmap("viridis")
    for ax, sex in zip(axes, SEXES):
        for i, y in enumerate(years):
            d = long[(long.sex == sex) & (long.year == y) & (long.age <= 99)]
            ax.plot(d.age, d.mx, color=cmap(i / (len(years) - 1)), lw=1.4, label=f"{y}年")
        ax.set_yscale("log"); ax.set_title(f"{sex}：年齢別の死亡率（対数目盛）")
        ax.set_xlabel("年齢"); ax.grid(alpha=0.3)
    axes[0].set_ylabel("死亡率（1年間に亡くなる割合）"); axes[1].legend(fontsize=9)
    fig.text(0.01, 0.01, "出典：国立社会保障・人口問題研究所「日本版死亡データベース（JMD）」を加工して作成", fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "f86_mx.png"); plt.close(fig)

    # 2 パラメータ
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for sex in SEXES:
        p = par[par.sex == sex]
        axes[0].plot(p.age, p.a, color=COL[sex], label=sex)
        axes[1].plot(p.age, p.b, color=COL[sex], label=sex)
        k = kt[kt.sex == sex]
        axes[2].plot(k.year, k.k, color=COL[sex], label=sex)
    axes[0].set_title("a(x)：年齢ごとの死亡率の平均的な高さ"); axes[0].set_xlabel("年齢")
    axes[1].set_title("b(x)：k が動いたときの各年齢の反応"); axes[1].set_xlabel("年齢")
    axes[2].set_title("k(t)：死亡率全体の水準（1970〜2024年）"); axes[2].set_xlabel("年")
    for ax in axes: ax.grid(alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "f86_params.png"); plt.close(fig)

    # 3 予測
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=False)
    for ax, sex in zip(axes, SEXES):
        o = obs[obs.year >= 1950]
        ax.plot(o.year, o[sex], color="black", lw=1.4, label="実績（JMD）")
        f = fc[fc.sex == sex]
        ax.fill_between(f.year, f.p025, f.p975, color=COL[sex], alpha=0.15, label="95%区間")
        ax.fill_between(f.year, f.p10, f.p90, color=COL[sex], alpha=0.30, label="80%区間")
        ax.plot(f.year, f.center, color=COL[sex], lw=2, label="Lee–Carter の予測（中心）")
        ip = ipss[ipss.source != "生命表"]
        ax.scatter(ip.year, ip[f"e0_{sex}"], marker="D", color="orange", zorder=5, label="社人研 令和5年推計（中位）")
        for _, r in ip.iterrows():
            ax.annotate(f"{r[f'e0_{sex}']:.1f}", (r.year, r[f"e0_{sex}"]), textcoords="offset points", xytext=(-14, 8), fontsize=8, color="darkorange")
        ax.set_title(f"{sex}：平均寿命の実績と予測"); ax.set_xlabel("年"); ax.set_ylabel("平均寿命（年）")
        ax.grid(alpha=0.3); ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(FIG / "f86_forecast.png"); plt.close(fig)

    # 4 バックテスト
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    cm = plt.get_cmap("plasma")
    ends = sorted(bt.fit_end.unique())
    for ax, sex in zip(axes, SEXES):
        for i, e in enumerate(ends):
            s = bt[(bt.sex == sex) & (bt.fit_end == e)]
            ax.plot(s.year, s.err, color=cm(i / len(ends)), marker="o", ms=2.5, lw=1.2, label=f"{e}年まで")
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_title(f"{sex}：過去の予測と実際の平均寿命の差（実際−予測）")
        ax.set_xlabel("年"); ax.grid(alpha=0.3)
    axes[0].set_ylabel("年（プラス＝実際のほうが長い）"); axes[1].legend(fontsize=8, title="当てはめの期間（1970年〜）", title_fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "f86_backtest.png"); plt.close(fig)

    # 5 頑健性
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    names = list(dict.fromkeys(rob.setting))
    for ax, sex in zip(axes, SEXES):
        s = rob[rob.sex == sex].set_index("setting").loc[names]
        y = np.arange(len(names))[::-1]
        ax.errorbar(s.e0_2070, y, xerr=[s.e0_2070 - s.e0_2070_p025, s.e0_2070_p975 - s.e0_2070], fmt="o", color=COL[sex], capsize=3)
        ipv = float(ipss.loc[ipss.year == 2070, f"e0_{sex}"].iloc[0])
        ax.axvline(ipv, color="orange", ls="--", label=f"社人研 中位 {ipv:.2f}")
        ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8)
        ax.set_title(f"{sex}：2070年の平均寿命（中心と95%区間）"); ax.set_xlabel("年"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "f86_robust.png"); plt.close(fig)

    # 6 b(x) の時期による違い
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, sex in zip(axes, SEXES):
        for per, ls in [("1970-1994", "--"), ("1995-2019", "-")]:
            s = bp[(bp.sex == sex) & (bp.period == per)]
            ax.plot(s.age, s.b, ls=ls, color=COL[sex], label=per.replace("-", "〜") + "年")
        ax.set_title(f"{sex}：b(x) を前半と後半で別に当てはめた場合"); ax.set_xlabel("年齢"); ax.grid(alpha=0.3); ax.legend(fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "f86_bshift.png"); plt.close(fig)
    print("figs done")


if __name__ == "__main__":
    main()
