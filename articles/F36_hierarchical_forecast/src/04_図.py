"""04 集計と図：段ごとの MASE、整合なしの「足し算のずれ」、県ごとの変化、コロナ後、頑健性"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import (RES, DATA, FIG, METHODS, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, PREFS)

ORDER = ["base", "bu", "td", "ols", "wlsv", "mint"]
LEVELS = ["全国", "地方", "都道府県", "全体"]
COL = {"base": GRAY, "bu": LIGHT, "td": ORANGE, "ols": PURPLE, "wlsv": GREEN, "mint": BLUE}


def load_err(tag):
    df = pd.read_csv(RES / f"errors_{tag}.csv.gz")
    return df.assign(ase=df.abs_err / df.scale)


def mase_table(df, hmax=12):
    d = df[df.h <= hmax]
    s = d.groupby(["level", "method"]).ase.mean().unstack()
    s.loc["全体"] = d.groupby("method").ase.mean()
    return s.reindex(index=LEVELS, columns=ORDER)


def rel(df, hs=None):
    d = df if hs is None else df[df.h.isin(hs)]
    t = mase_table(d, 12)
    return t.div(t["base"], axis=0)


if __name__ == "__main__":
    main = load_err("main")
    T = mase_table(main)
    T.round(4).rename(columns=METHODS).to_csv(RES / "mase_main.csv")
    rel(main).round(4).rename(columns=METHODS).to_csv(RES / "mase_main_relative.csv")
    # 予測の長さ別
    hz = []
    for hs, lab in [([1], "1か月先"), ([3], "3か月先"), ([12], "12か月先"), (list(range(1, 13)), "1〜12か月先の平均")]:
        r = mase_table(main[main.h.isin(hs)])
        for lv in LEVELS:
            hz.append([lab, lv] + list(r.loc[lv].values))
    pd.DataFrame(hz, columns=["予測の長さ", "段"] + [METHODS[m] for m in ORDER]).round(4).to_csv(RES / "mase_by_horizon.csv", index=False)
    # 起点ごとに MinT が整合なしより良かった割合（段別）
    wo = main.groupby(["origin", "level", "method"]).ase.mean().unstack()
    win = (wo["mint"] < wo["base"]).groupby(level="level").mean()
    win.to_csv(RES / "mint_win_rate_by_origin.csv")
    # 季節ナイーブ（参考）
    sn = mase_table(load_err("snaive"))["base"]
    sn.to_csv(RES / "mase_snaive.csv")

    # ---- 図1：系列の例と階層 ----
    Y = pd.read_csv(DATA / "series58_total.csv", index_col=0, parse_dates=True)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for c, col, lab in [("全国", INK, "全国（1系列）"), ("関東", BLUE, "地方の例：関東（10系列）"), ("東京", ORANGE, "都道府県の例：東京（47系列）"),
                        ("沖縄", GREEN, "都道府県の例：沖縄")]:
        ax.plot(Y.index, Y[c] / 1e6, color=col, lw=1.3, label=lab)
    ax.set_yscale("log"); ax.set_ylabel("延べ宿泊者数（百万人泊、対数目盛）")
    ax.axvspan(pd.Timestamp("2020-02-01"), pd.Timestamp("2022-12-01"), color=GRAY, alpha=0.15, lw=0)
    ax.text(pd.Timestamp("2021-06-01"), ax.get_ylim()[1] * 0.6, "コロナ期", ha="center", color=GRAY, fontsize=9)
    ax.set_title("全国＝10地方の合計＝47都道府県の合計。58系列を予測し、足し算が合うようにそろえる", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=2)
    save(fig, "a36_series.png")

    # ---- 図2：整合なしの足し算のずれ ----
    g = pd.read_csv(RES / "gap_main.csv")
    g["gap"] = (g.sum_pref_fc / g.national_fc - 1) * 100
    fig, ax = plt.subplots(figsize=(9, 4.2))
    data = [g[g.h == h].gap.values for h in range(1, 13)]
    ax.boxplot(data, positions=range(1, 13), widths=0.55, patch_artist=True,
               boxprops=dict(facecolor=LIGHT, color=BLUE), medianprops=dict(color=INK), whiskerprops=dict(color=BLUE),
               capprops=dict(color=BLUE), flierprops=dict(markeredgecolor=GRAY))
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("何か月先の予測か"); ax.set_ylabel("47都道府県の予測の合計 ÷ 全国の予測 − 1（%）")
    ax.set_title("別々に予測すると、47都道府県の合計は全国の予測と合わない（起点13回）", fontsize=12)
    save(fig, "a36_gap.png")
    g.groupby("h").gap.agg(["mean", "min", "max"]).round(3).to_csv(RES / "gap_by_horizon.csv")

    # ---- 図3：段別・手法別の MASE ----
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    x = np.arange(len(LEVELS)); w = 0.13
    for i, m in enumerate(ORDER):
        ax.bar(x + (i - 2.5) * w, T[m].values, w, color=COL[m], label=METHODS[m], edgecolor="white")
    for j, lv in enumerate(LEVELS):
        ax.plot([j - 3 * w, j + 3 * w], [sn[lv]] * 2, color=INK, ls="--", lw=1)
    ax.plot([], [], color=INK, ls="--", lw=1, label="参考：季節ナイーブ")
    ax.set_xticks(x); ax.set_xticklabels(LEVELS)
    ax.set_ylabel("MASE（小さいほど良い）")
    ax.set_title("2018〜19年の予測（1〜12か月先の平均）：段ごとの精度", fontsize=12)
    ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper right")
    ax.set_ylim(0, max(T.max().max(), sn.max()) * 1.25)
    save(fig, "a36_mase.png")

    # ---- 図4：都道府県ごとの変化（MinT ÷ 整合なし） ----
    pref = main[main.level == "都道府県"].groupby(["series", "method"]).ase.mean().unstack()
    ch = (pref["mint"] / pref["base"] - 1) * 100
    ch.round(3).sort_values().to_csv(RES / "pref_change_mint_vs_base.csv")
    chb = (pref["bu"] / pref["base"] - 1) * 100
    ch = ch.sort_values()
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(range(len(ch)), ch.values, color=[BLUE if v < 0 else ORANGE for v in ch.values])
    ax.set_xticks(range(len(ch))); ax.set_xticklabels(ch.index, rotation=90, fontsize=8)
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_ylabel("MinT で MASE が何%変わったか")
    ax.set_title(f"都道府県ごとの変化：良くなった県 {int((ch<0).sum())}、悪くなった県 {int((ch>0).sum())}（中央値 {ch.median():+.1f}%）", fontsize=12)
    save(fig, "a36_pref.png")

    # ---- 図5：コロナ後の比較 ----
    post = load_err("post")
    P = mase_table(post)
    P.round(4).rename(columns=METHODS).to_csv(RES / "mase_post.csv")
    rel(post).round(4).rename(columns=METHODS).to_csv(RES / "mase_post_relative.csv")
    covid = load_err("covid")
    C = mase_table(covid)
    C.round(4).rename(columns=METHODS).to_csv(RES / "mase_covid2020.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=False)
    for ax, (tab, title) in zip(axes, [(rel(main), "コロナ前（2018〜19年）"), (rel(post), "コロナ後（2025年）")]):
        for i, m in enumerate(ORDER[1:]):
            ax.bar(x + (i - 2) * 0.16, (tab[m].values - 1) * 100, 0.16, color=COL[m], label=METHODS[m])
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels(LEVELS); ax.set_title(title, fontsize=12)
    axes[0].set_ylabel("整合なしと比べた MASE の変化（%）")
    axes[1].legend(frameon=False, fontsize=9, loc="best")
    fig.suptitle("整合で精度はどう変わったか（マイナスほど良くなった）", fontsize=13, y=1.02)
    save(fig, "a36_post.png")

    # ---- 頑健性 ----
    rows = []
    for tag, lab in [("main", "基本（総数・ETS・2011年から学習）"), ("start2014", "学習を2014年から"), ("japanese", "日本人のみ"),
                     ("foreign", "外国人のみ"), ("arima", "基本の予測を ARIMA に"), ("post", "コロナ後（2023年から学習）")]:
        try:
            df = load_err(tag)
        except FileNotFoundError:
            continue
        for hs, hl in [(None, "1〜12"), ([1], "1"), ([3], "3"), ([12], "12")]:
            r = rel(df, hs)
            for lv in LEVELS:
                rows.append([lab, hl, lv] + [round(r.loc[lv, m], 4) for m in ORDER[1:]] + [round(mase_table(df if hs is None else df[df.h.isin(hs)]).loc[lv, "base"], 4)])
    R = pd.DataFrame(rows, columns=["設定", "何か月先", "段"] + [METHODS[m] for m in ORDER[1:]] + ["整合なしの MASE"])
    R.to_csv(RES / "robustness_relative_mase.csv", index=False)
    rr = R[(R["何か月先"] == "1〜12") & (R["段"] == "全体")].set_index("設定")
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    xx = np.arange(len(rr))
    for i, m in enumerate(ORDER[1:]):
        ax.bar(xx + (i - 2) * 0.16, (rr[METHODS[m]].values - 1) * 100, 0.16, color=COL[m], label=METHODS[m])
    ax.axhline(0, color=GRAY, lw=0.8)
    ax.set_xticks(xx); ax.set_xticklabels([s.replace("（", "\n（") for s in rr.index], fontsize=8)
    ax.set_ylabel("整合なしと比べた MASE の変化（%、58系列全体）")
    ax.set_title("設定を変えても、MinT・WLS・ボトムアップは全体で±3%以内。トップダウンと OLS は悪くなる", fontsize=12)
    ax.legend(frameon=False, fontsize=9, ncol=5, loc="upper left")
    save(fig, "a36_robust.png")
    print(T.round(3)); print(rel(main).round(3)); print(P.round(3)); print(rel(post).round(3)); print(C.round(2))
    print(win); print(sn.round(3)); print(ch.describe().round(2))
    print(R[R["段"] == "全体"].to_string())
