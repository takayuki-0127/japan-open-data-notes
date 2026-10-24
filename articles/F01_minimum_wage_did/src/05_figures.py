"""図5枚と異質性の集計 → figures/*.png, results/heterogeneity.csv, results/card_scatter.csv"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import panel, fe_ols, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

df = panel()
b = df.drop_duplicates("pref").set_index("pref")


def fig1():
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    w = df.pivot(index="year", columns="pref", values="mw_fy")
    for p in w.columns:
        ax[0].plot(w.index, w[p], color=LIGHT, lw=0.8, alpha=0.7)
    for grp, c, lab in [(1, ORANGE, "bite 上位半分（24県）"), (0, BLUE, "bite 下位半分（23県）")]:
        ax[0].plot(w.index, w[b.index[b.high_bite == grp]].mean(axis=1), color=c, lw=2.4, label=lab)
    ax[0].axvline(2015.5, color=GRAY, ls=":", lw=1)
    ax[0].set_title("地域別最低賃金（円）：2グループの平均はほぼ重なる"); ax[0].legend(frameon=False, loc="upper left")
    ax[0].set_xticks(range(2008, 2026, 2))
    ax[0].set_xlabel("年度")
    g = (w.loc[2025] / w.loc[2015] - 1) * 100
    ax[1].scatter(b.bite * 100, g[b.index], c=[ORANGE if h else BLUE for h in b.high_bite], s=30)
    for p in ["東京", "神奈川", "大阪", "青森", "北海道", "徳島", "鳥取", "沖縄"]:
        ax[1].annotate(p, (b.bite[p] * 100, g[p]), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax[1].set_xlabel("bite＝最低賃金÷短時間労働者の平均時給（2015年、%）")
    ax[1].set_ylabel("最低賃金の上昇率 2015→2025年度（%）")
    ax[1].set_title(f"上昇率は bite とほぼ無関係（相関 {np.corrcoef(b.bite, g[b.index])[0, 1]:+.2f}）")
    fig.tight_layout(); save(fig, "f01_bite_mw.png")


def fig2():
    es = pd.read_csv(RES / "event_study.csv")
    es = es[es.treat == "上位半分ダミー"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    for a, (y, lab) in zip(ax, [("emp_rate", "就業率（%pt）"), ("unemp_rate", "完全失業率（%pt）")]):
        e = es[es.outcome == y].sort_values("year")
        a.axvspan(2019.5, 2022.5, color="#eeeeee", zorder=0)
        a.axhline(0, color=INK, lw=0.8); a.axvline(2015.5, color=GRAY, ls=":", lw=1)
        a.fill_between(e.year, e.lo95, e.hi95, color=LIGHT, alpha=0.6, label="95%信頼区間")
        a.plot(e.year, e.beta, "o-", color=BLUE, lw=1.8, ms=4, label="係数（2015年＝0）")
        a.set_title(f"bite上位半分の県 − 下位半分の県：{lab}")
        a.set_xticks(range(2008, 2026, 2))
        a.text(2021, a.get_ylim()[1] * 0.92, "コロナ期", ha="center", fontsize=8, color=GRAY)
    ax[0].legend(frameon=False, loc="lower right", fontsize=9)
    fig.tight_layout(); save(fig, "f02_event_study.png")


def fig3():
    r = pd.read_csv(RES / "robustness.csv")
    checks = list(dict.fromkeys(r.check))
    fig, ax = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for a, (y, lab) in zip(ax, [("emp_rate", "就業率（%pt）"), ("unemp_rate", "完全失業率（%pt）")]):
        d = r[r.outcome == y].set_index("check").loc[checks]
        yy = np.arange(len(checks))[::-1]
        cols = [GRAY if "プラセボ" in c else (ORANGE if "連続" in c else BLUE) for c in checks]
        a.errorbar(d.delta, yy, xerr=[d.delta - d.lo95, d.hi95 - d.delta], fmt="none", ecolor=cols, elinewidth=2)
        a.scatter(d.delta, yy, c=cols, s=40, zorder=3)
        a.axvline(0, color=INK, lw=0.8)
        a.set_title(f"差の差の推定値：{lab}")
        a.set_yticks(yy); a.set_yticklabels(checks, fontsize=9)
    ax[0].set_xlabel("上位半分の県が下位半分より、2016年以降にどれだけ変わったか")
    fig.tight_layout(); save(fig, "f03_forest.png")


def heterogeneity():
    d = df.copy()
    d["terc"] = pd.qcut(d.bite.rank(method="first"), 3, labels=["低", "中", "高"]).astype(str)
    periods = [("2016–19", 2016, 2019), ("2020–22", 2020, 2022), ("2023–25", 2023, 2025)]
    regs = []
    for t in ["中", "高"]:
        for name, a, z in periods:
            c = f"{t}_{name}"; d[c] = ((d.terc == t) & d.year.between(a, z)).astype(int); regs.append(c)
    rows = []
    for y in ["emp_rate", "unemp_rate"]:
        m, _, _ = fe_ols(d, y, regs)
        ci = m.conf_int()
        for c in regs:
            t, name = c.split("_")
            rows.append({"outcome": y, "tercile": t, "period": name, "delta": m.params[c], "lo95": ci.loc[c, 0], "hi95": ci.loc[c, 1], "p": m.pvalues[c]})
    h = pd.DataFrame(rows); h.round(4).to_csv(RES / "heterogeneity.csv", index=False)
    # Card 型の散布図：bite と 2015→2019年の就業率の変化
    w = df.pivot(index="pref", columns="year", values="emp_rate")
    cs = pd.DataFrame({"bite": b.bite, "d_emp_2015_2019": w[2019] - w[2015], "d_emp_2015_2025": w[2025] - w[2015]})
    k = np.polyfit(cs.bite * 100, cs.d_emp_2015_2019, 1)
    cs.round(4).to_csv(RES / "card_scatter.csv")
    pd.DataFrame([{"slope_pp_per_1pt_bite_2015_2019": k[0], "corr_2015_2019": cs.bite.corr(cs.d_emp_2015_2019),
                   "corr_2015_2025": cs.bite.corr(cs.d_emp_2015_2025)}]).round(4).to_csv(RES / "card_scatter_summary.csv", index=False)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
    ax[0].scatter(cs.bite * 100, cs.d_emp_2015_2019, color=BLUE, s=28)
    xs = np.linspace(cs.bite.min() * 100, cs.bite.max() * 100, 10)
    ax[0].plot(xs, np.polyval(k, xs), color=ORANGE, lw=1.6)
    for p in ["東京", "青森", "北海道", "徳島", "沖縄", "鳥取"]:
        ax[0].annotate(p, (cs.bite[p] * 100, cs.d_emp_2015_2019[p]), fontsize=8, xytext=(3, 3), textcoords="offset points")
    ax[0].axhline(0, color=INK, lw=0.6)
    ax[0].set_xlabel("bite（2015年、%）"); ax[0].set_ylabel("就業率の変化 2015→2019年（%pt）")
    ax[0].set_title("県ごとの bite と就業率の変化")
    hh = h[h.outcome == "emp_rate"]
    x = np.arange(3)
    for i, (t, c) in enumerate([("中", GREEN), ("高", ORANGE)]):
        q = hh[hh.tercile == t]
        ax[1].errorbar(x + (i - 0.5) * 0.25, q.delta, yerr=[q.delta - q.lo95, q.hi95 - q.delta], fmt="o", color=c, capsize=3, label=f"bite {t}位の県（16県前後）")
    ax[1].axhline(0, color=INK, lw=0.8)
    ax[1].set_xticks(x); ax[1].set_xticklabels([p[0] for p in periods])
    ax[1].set_title("就業率：bite 低位の県との差（2008–15年比）"); ax[1].set_ylabel("%pt")
    ax[1].legend(frameon=False, fontsize=9)
    fig.tight_layout(); save(fig, "f04_heterogeneity.png")


def fig5():
    pm = pd.read_csv(RES / "permutation.csv"); s = pd.read_csv(RES / "permutation_summary.csv").set_index("outcome")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for a, (y, lab) in zip(ax, [("emp_rate", "就業率（%pt）"), ("unemp_rate", "完全失業率（%pt）")]):
        a.hist(pm[y], bins=40, color=LIGHT, edgecolor="white")
        a.axvline(s.loc[y, "observed"], color=ORANGE, lw=2.2)
        a.set_title(f"県の組み分けをランダムにした2,000回：{lab}")
        a.text(s.loc[y, "observed"], a.get_ylim()[1] * 0.9, f"  実際の値 {s.loc[y, 'observed']:+.2f}\n  p={s.loc[y, 'perm_p_two_sided']:.2f}", color=ORANGE, fontsize=9, va="top")
        a.set_xlabel("差の差の推定値")
    fig.tight_layout(); save(fig, "f05_placebo.png")


if __name__ == "__main__":
    fig1(); fig2(); heterogeneity()
    if (RES / "robustness.csv").exists():
        fig3()
    if (RES / "permutation.csv").exists():
        fig5()
    print(pd.read_csv(RES / "heterogeneity.csv").round(3).to_string()); print(pd.read_csv(RES / "card_scatter_summary.csv"))
