"""1209 見つけた鳥の数が去年より減ったのは、鳥が減ったからか、見つけにくくなったからか？（架空のデータ）

架空の森の観察地点40か所。地点ごとの本当の鳥の数（作成者が置いた）と、1回の見回りで1羽を見つける確率（作成者が置いた）から、
年に3回の見回りで見つけた数を乱数で作る。2年目は「本当の数が変わる」「見つける確率が下がる」を置き分けて、
見つけた数の合計・地点ごとの最大・見回りどうしの数のばらつきから見つける確率を数え直した数、の3つで増減を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1209
SRC = "架空の森の観察地点の鳥（作成者が乱数で作成、seed 1209）"
SITES, LAM, P1 = 40, 8.0, 0.5
REPS = 2000


def year_counts(rng, reps, sites, lam, p, visits, het):
    """本当の数 N（reps×sites）と見つけた数（reps×sites×visits）"""
    N = rng.poisson(lam, size=(reps, sites))
    flat = N.ravel()
    sid = np.repeat(np.arange(flat.size), flat)
    if het > 0:  # 1羽ごとに見つけやすさが違う（平均 p、集中度 het）
        pi = rng.beta(p * het, (1 - p) * het, size=sid.size)
    else:
        pi = np.full(sid.size, p)
    det = rng.random((sid.size, visits)) < pi[:, None]
    cnt = np.zeros((flat.size, visits))
    for v in range(visits):
        cnt[:, v] = np.bincount(sid, weights=det[:, v], minlength=flat.size)
    return N, cnt.reshape(reps, sites, visits)


def estimate(cnt):
    """見つけた数の合計・地点ごとの最大の合計・数え直した数（reps）"""
    tot = cnt.sum(axis=(1, 2))
    mx = cnt.max(axis=2).sum(axis=1)
    mean = cnt.mean(axis=2)
    var = cnt.var(axis=2, ddof=1)
    phat = 1 - var.sum(axis=1) / np.maximum(mean.sum(axis=1), 1e-9)
    phat = np.clip(phat, 0.05, 1.0)
    nhat = mean.sum(axis=1) / phat
    return tot, mx, nhat, phat


def sim(rng, r, p2, visits=3, het=0.0, reps=REPS, sites=SITES):
    N1, c1 = year_counts(rng, reps, sites, LAM, P1, visits, het)
    N2, c2 = year_counts(rng, reps, sites, LAM * (1 + r), p2, visits, het)
    t1, m1, n1, ph1 = estimate(c1)
    t2, m2, n2, ph2 = estimate(c2)
    true = N2.sum(1) / N1.sum(1) - 1
    return dict(true=true, count=t2 / t1 - 1, max=m2 / m1 - 1, corr=n2 / n1 - 1, ph1=ph1, ph2=ph2,
                N1=N1, N2=N2, c1=c1, c2=c2)


def summ(d):
    out = {}
    for k in ["true", "count", "max", "corr"]:
        x = d[k] * 100
        out[k] = dict(mean=round(float(x.mean()), 2), median=round(float(np.median(x)), 2), q05=round(float(np.quantile(x, .05)), 2),
                      q95=round(float(np.quantile(x, .95)), 2),
                      share_down10=round(float((x <= -10).mean() * 100), 2))
    out["phat_year1_mean"] = round(float(d["ph1"].mean()), 4)
    out["phat_year2_mean"] = round(float(d["ph2"].mean()), 4)
    return out


def main():
    rng = np.random.default_rng(SEED)
    scen = {
        "A_same_birds_harder_to_see": dict(r=0.0, p2=0.4),
        "B_fewer_birds_same_seeing": dict(r=-0.2, p2=0.5),
        "C_both": dict(r=-0.2, p2=0.4),
        "D_nothing_changes": dict(r=0.0, p2=0.5),
    }
    res, raw = {}, {}
    for k, v in scen.items():
        d = sim(rng, **v)
        res[k] = dict(setting=dict(true_change_pct=v["r"] * 100, p_year1=P1, p_year2=v["p2"]), **summ(d))
        raw[k] = d

    # 例の1回（A）：地点ごと
    d = raw["A_same_birds_harder_to_see"]
    ex = pd.DataFrame({"site": np.arange(1, SITES + 1),
                       "true_year1": d["N1"][0], "true_year2": d["N2"][0]})
    for y, c in [(1, d["c1"][0]), (2, d["c2"][0])]:
        for v in range(3):
            ex[f"seen_year{y}_visit{v + 1}"] = c[:, v].astype(int)
    ex.to_csv(DATA / "example_sites.csv", index=False)
    exs = dict(true_year1=int(ex.true_year1.sum()), true_year2=int(ex.true_year2.sum()),
               seen_year1=int(d["c1"][0].sum()), seen_year2=int(d["c2"][0].sum()),
               count_change_pct=round(float(d["count"][0] * 100), 2),
               true_change_pct=round(float(d["true"][0] * 100), 2),
               corr_change_pct=round(float(d["corr"][0] * 100), 2),
               phat_year1=round(float(d["ph1"][0]), 4), phat_year2=round(float(d["ph2"][0]), 4))

    # 見回りの回数・地点の数を変えると（A の場面、数え直した数のぶれ）
    rows = []
    for visits in [3, 6, 10]:
        for sites in [40, 120]:
            dd = sim(rng, 0.0, 0.4, visits=visits, sites=sites, reps=1000)
            s = summ(dd)
            rows.append(dict(visits=visits, sites=sites, count_mean=s["count"]["mean"],
                             corr_mean=s["corr"]["mean"], corr_median=s["corr"]["median"], corr_q05=s["corr"]["q05"], corr_q95=s["corr"]["q95"],
                             corr_share_down10=s["corr"]["share_down10"]))
    vis = pd.DataFrame(rows)
    vis.to_csv(RES / "visits_sites.csv", index=False)

    # 確かめ：36通り
    rows = []
    for r in [-0.2, 0.0, 0.2]:
        for drop in [0.0, 0.2, 0.4]:
            for visits in [3, 6]:
                for het in [0.0, 2.0]:
                    dd = sim(rng, r, P1 * (1 - drop), visits=visits, het=het, reps=300)
                    s = summ(dd)
                    rows.append(dict(true_change_pct=r * 100, seeing_drop_pct=drop * 100, visits=visits,
                                     birds_differ=("あり" if het else "なし"),
                                     true_mean=s["true"]["mean"], count_mean=s["count"]["mean"],
                                     max_mean=s["max"]["mean"], corr_mean=s["corr"]["mean"],
                                     corr_q05=s["corr"]["q05"], corr_q95=s["corr"]["q95"],
                                     count_bias=round(s["count"]["mean"] - s["true"]["mean"], 2),
                                     corr_bias=round(s["corr"]["mean"] - s["true"]["mean"], 2),
                                     phat_year1=s["phat_year1_mean"]))
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    out = dict(
        scenarios=res, example_A=exs,
        grid_summary=dict(
            count_bias_range=[float(g.count_bias.min()), float(g.count_bias.max())],
            corr_bias_range=[float(g.corr_bias.min()), float(g.corr_bias.max())],
            corr_bias_range_birds_same=[float(g[g.birds_differ == "なし"].corr_bias.min()),
                                        float(g[g.birds_differ == "なし"].corr_bias.max())],
            corr_bias_range_birds_differ=[float(g[g.birds_differ == "あり"].corr_bias.min()),
                                          float(g[g.birds_differ == "あり"].corr_bias.max())],
            count_bias_drop20=[float(g[g.seeing_drop_pct == 20].count_bias.min()),
                               float(g[g.seeing_drop_pct == 20].count_bias.max())],
            count_bias_drop40=[float(g[g.seeing_drop_pct == 40].count_bias.min()),
                               float(g[g.seeing_drop_pct == 40].count_bias.max())],
            phat_year1_birds_differ_mean=round(float(g[g.birds_differ == "あり"].phat_year1.mean()), 4),
            phat_year1_birds_same_mean=round(float(g[g.birds_differ == "なし"].phat_year1.mean()), 4)),
    )
    json.dump(out, open(RES / "a1209_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：4つの場面
    names = ["本当の数は同じ\n見つける確率\n0.5→0.4", "本当の数が2割減\n見つける確率\nは同じ",
             "本当の数が2割減\nかつ見つける確率\n0.5→0.4", "どちらも\n変わらない"]
    keys = list(scen)
    fig, ax = plt.subplots(figsize=(8.0, 4.4))
    x = np.arange(4)
    for j, (m, lab, col) in enumerate([("count", "見つけた数の合計", BLUE), ("max", "地点ごとの最大の合計", LIGHT),
                                       ("corr", "見つける確率を数え直した数", ORANGE)]):
        vals = [res[k][m]["mean"] for k in keys]
        ax.bar(x + (j - 1) * 0.25, vals, width=0.25, color=col, label=lab)
        for i, v in enumerate(vals):
            ax.text(x[i] + (j - 1) * 0.25, v - 1.2 if v < 0 else v + 0.4, f"{v:g}", ha="center",
                    va="top" if v < 0 else "bottom", fontsize=7.5, zorder=6,
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.4, alpha=0.85))
    tv = [res[k]["true"]["mean"] for k in keys]
    ax.scatter(x, tv, marker="_", s=900, color=INK, zorder=5, label="本当の数の増減")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=8.5)
    ax.set_ylim(-45, 16); ax.set_ylabel("2年目の増減（%、2,000回の平均）")
    ax.legend(frameon=False, fontsize=8, loc="lower right", markerscale=0.45)
    ax.set_title("見つけた数の合計では、「鳥が減った」と「見つけにくくなった」が同じに見えた")
    save(fig, "a1209_scenarios.png", SRC)

    # 図2：見回りの回数と、数え直した数のぶれ
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    for sites, col, off in [(40, BLUE, -0.12), (120, ORANGE, 0.12)]:
        s = vis[vis.sites == sites]
        xx = np.arange(len(s)) + off
        ax.errorbar(xx, s.corr_mean, yerr=[s.corr_mean - s.corr_q05, s.corr_q95 - s.corr_mean], fmt="o",
                    color=col, capsize=4, label=f"{sites}地点")
    ax.axhline(0, color=INK, lw=0.8, label="本当の数の増減（0%）")
    ax.axhline(res["A_same_birds_harder_to_see"]["count"]["mean"], color=GRAY, lw=1, ls="--",
               label="見つけた数の合計（3回・40地点の平均）")
    ax.set_xticks(range(3)); ax.set_xticklabels(["年3回", "年6回", "年10回"])
    ax.set_ylabel("数え直した数の増減（%）\n点は平均、線は5〜95%", linespacing=1.6)
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=2)
    ax.set_ylim(-60, 100)
    ax.set_title("本当の数は同じ・見つける確率0.5→0.4のとき、数え直した数は\n見回りが少ないほど幅が広く、平均は上に寄った")
    save(fig, "a1209_visits.png", SRC)

    # 図3：36通りのずれ
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    xx = np.arange(len(g))
    ax.bar(xx - 0.2, g.count_bias, width=0.4, color=BLUE, label="見つけた数の合計")
    ax.bar(xx + 0.2, g.corr_bias, width=0.4, color=ORANGE, label="見つける確率を数え直した数")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks([]); ax.set_xlabel("置き方の36通り\n（本当の増減 × 見つける確率の下がり × 見回りの回数 × 鳥ごとの見つけやすさの違い）")
    ax.set_ylabel("本当の増減とのずれ（ポイント）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("見つけた数の合計のずれは、見つける確率の下がり方でほぼ決まった\n（36通り、各300回の平均）")
    save(fig, "a1209_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
