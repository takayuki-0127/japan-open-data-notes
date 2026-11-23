"""1109 効き目が試す場所によって違うとき、1か所の結果はどこまで当てはまるのか？（架空のデータ）

架空の印刷会社の工場12か所で、新しい乾かし方が「印刷のにじみの幅」をどれだけ減らすか（効き目）を試す。
効き目は工場の湿度で変わり（湿度が高いほど大きい）、さらに工場ごとの説明できない違いがある、と作成者が置く。
1か所（本社工場、または でたらめに選んだ1か所）で試した結果と、同じ枚数を4か所に分けて試した結果が、
ほかの工場の効き目や12工場の平均の効き目にどこまで当てはまるかを、2,000回数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1109
SRC = "架空の印刷会社の工場12か所の試し刷り（作成者が置いた効き目とばらつきからの乱数、seed 1109）"
HUM = np.array([45, 48, 51, 54, 57, 59, 61, 63, 66, 69, 72, 75], float)  # 工場ごとの湿度（%）、平均60
NAMES = [f"工場{chr(65 + i)}" for i in range(12)]
HQ = 10                      # 本社工場（湿度72%）
BASE = {"mu": 10.0, "slope": 0.5, "site_sd": 2.0, "sheet_sd": 6.0, "n_per_arm": 20}
WORLDS = 2000
T3 = 3.182446                # 自由度3の t 分布の 97.5% 点（4か所の散らばりから幅を出すとき）
Z = 1.959964


def r(x, d=4):
    return round(float(x), d)


def true_effects(rng, worlds, mu, slope, site_sd):
    return mu + slope * (HUM - HUM.mean())[None, :] + rng.normal(0, site_sd, (worlds, 12))


def site_estimate(rng, tau_site, n, sheet_sd):
    """1か所で、今の乾かし方 n 枚・新しい乾かし方 n 枚を刷る。効き目＝今のにじみ平均−新しいにじみ平均"""
    se = sheet_sd * np.sqrt(2 / n)
    # 平均どうしの差は、正規分布の差になる（1枚ずつ引いて平均するのと同じ分布）
    return tau_site + rng.normal(0, se, tau_site.shape), se


def evaluate(rng, tau, n, sheet_sd, design):
    W = tau.shape[0]
    avg = tau.mean(1)
    if design in ("hq", "random1"):
        s = np.full(W, HQ) if design == "hq" else rng.integers(0, 12, W)
        est, se = site_estimate(rng, tau[np.arange(W), s], n, sheet_sd)
        lo, hi = est - Z * se, est + Z * se
        own = (lo <= tau[np.arange(W), s]) & (tau[np.arange(W), s] <= hi)
        mask = np.ones((W, 12), bool)
        mask[np.arange(W), s] = False
        other = ((lo[:, None] <= tau) & (tau <= hi[:, None]))[mask].mean()
        cov_avg = ((lo <= avg) & (avg <= hi)).mean()
        return {"est_minus_avg_mean": r((est - avg).mean(), 3), "est_minus_avg_abs_mean": r(np.abs(est - avg).mean(), 3),
                "half_width": r(Z * se, 3), "cover_own_site": r(own.mean()), "cover_other_sites": r(other),
                "cover_12_average": r(cov_avg)}
    # 4か所に分ける（同じ枚数：1か所あたり n/4 枚ずつ）
    k = 4
    s = np.argsort(rng.random((W, 12)), 1)[:, :k]
    ts = np.take_along_axis(tau, s, 1)
    est_s, se_s = site_estimate(rng, ts, n / k, sheet_sd)
    est = est_s.mean(1)
    se_sheet = se_s / np.sqrt(k)  # 1枚ごとのばらつきだけから出した幅
    se_site = est_s.std(1, ddof=1) / np.sqrt(k)  # 4か所の見積もりの散らばりから出した幅
    out = {"est_minus_avg_mean": r((est - avg).mean(), 3), "est_minus_avg_abs_mean": r(np.abs(est - avg).mean(), 3)}
    for nm, lo, hi in [("sheet", est - Z * se_sheet, est + Z * se_sheet), ("site", est - T3 * se_site, est + T3 * se_site)]:
        out[f"half_width_{nm}"] = r(((hi - lo) / 2).mean(), 3)
        out[f"cover_12_average_{nm}"] = r(((lo <= avg) & (avg <= hi)).mean())
        out[f"cover_other_sites_{nm}"] = r(((lo[:, None] <= tau) & (tau <= hi[:, None])).mean())
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setup": {**BASE, "humidity": HUM.tolist(), "hq_factory": NAMES[HQ], "hq_humidity": float(HUM[HQ]),
                     "worlds": WORLDS, "t_3_975": T3, "z_975": r(Z, 6)}}
    tau = true_effects(rng, WORLDS, BASE["mu"], BASE["slope"], BASE["site_sd"])
    out["true_effects"] = {"hq_mean": r(tau[:, HQ].mean(), 3), "average_mean": r(tau.mean(1).mean(), 3),
                           "site_min_mean": r(tau.min(1).mean(), 3), "site_max_mean": r(tau.max(1).mean(), 3),
                           "share_sites_below_half_of_hq": r((tau < 0.5 * tau[:, [HQ]]).mean()),
                           "by_factory_mean": {NAMES[i]: r(tau[:, i].mean(), 3) for i in range(12)}}

    # 1) 基本：1か所あたりの枚数 20・80・320枚ずつ（4か所に分けるときは合計が同じ）
    rows = []
    for n in [20, 80, 320]:
        for design in ["hq", "random1", "four"]:
            res = evaluate(np.random.default_rng(SEED * 10 + n + len(rows)), tau, n, BASE["sheet_sd"], design)
            rows.append({"n_per_arm_total": n, "design": design, **res})
    base_df = pd.DataFrame(rows)
    base_df.to_csv(RES / "coverage_by_sheets.csv", index=False)
    out["coverage_by_sheets"] = rows

    # 2) 確かめ：工場ごとの説明できない違い（0・1・2・4）×湿度での変わり方（0・0.25・0.5・1）の16通り、20枚ずつ
    grid = []
    for sd in [0.0, 1.0, 2.0, 4.0]:
        for sl in [0.0, 0.25, 0.5, 1.0]:
            rg = np.random.default_rng(SEED * 100 + int(sd * 10) * 10 + int(sl * 100))
            tg = true_effects(rg, WORLDS, BASE["mu"], sl, sd)
            for design in ["hq", "random1", "four"]:
                res = evaluate(rg, tg, BASE["n_per_arm"], BASE["sheet_sd"], design)
                grid.append({"site_sd": sd, "slope": sl, "design": design, **res})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    gh = g[g.design == "hq"]
    gr = g[g.design == "random1"]
    gf = g[g.design == "four"]
    out["grid_ranges"] = {
        "hq_cover_12_average": [r(gh.cover_12_average.min()), r(gh.cover_12_average.max())],
        "hq_cover_other_sites": [r(gh.cover_other_sites.min()), r(gh.cover_other_sites.max())],
        "random1_cover_12_average": [r(gr.cover_12_average.min()), r(gr.cover_12_average.max())],
        "four_cover_12_average_site": [r(gf.cover_12_average_site.min()), r(gf.cover_12_average_site.max())],
        "four_cover_12_average_sheet": [r(gf.cover_12_average_sheet.min()), r(gf.cover_12_average_sheet.max())],
        "hq_no_variation_cover_12_average": r(gh[(gh.site_sd == 0) & (gh.slope == 0)].cover_12_average.iloc[0]),
        "settings": int(len(gh))}

    # data：1回目の世界の工場ごとの本当の効き目と、本社工場で20枚ずつ刷った1回の記録
    rd = np.random.default_rng(SEED + 5)
    pd.DataFrame({"factory": NAMES, "humidity": HUM, "true_effect_world1": tau[0].round(3),
                  "true_effect_mean_2000": tau.mean(0).round(3)}).to_csv(DATA / "factories.csv", index=False)
    base_level = 40.0  # 今の乾かし方のにじみの幅の平均（µm）。効き目の見積もりには効かない
    sheets = []
    for arm, shift in [("今の乾かし方", 0.0), ("新しい乾かし方", -tau[0, HQ])]:
        v = base_level + shift + rd.normal(0, BASE["sheet_sd"], BASE["n_per_arm"])
        sheets += [{"factory": NAMES[HQ], "method": arm, "sheet": i + 1, "bleed_um": round(float(x), 2)} for i, x in enumerate(v)]
    sh = pd.DataFrame(sheets)
    sh.to_csv(DATA / "hq_sheets_world1.csv", index=False)
    e1 = sh[sh.method == "今の乾かし方"].bleed_um.mean() - sh[sh.method == "新しい乾かし方"].bleed_um.mean()
    se1 = BASE["sheet_sd"] * np.sqrt(2 / BASE["n_per_arm"])
    out["world1_example"] = {"hq_estimate": r(e1, 3), "hq_low": r(e1 - Z * se1, 3), "hq_high": r(e1 + Z * se1, 3),
                             "hq_true": r(tau[0, HQ], 3), "average_true": r(tau[0].mean(), 3),
                             "sites_inside_interval": int(((tau[0] >= e1 - Z * se1) & (tau[0] <= e1 + Z * se1)).sum())}
    json.dump(out, open(RES / "a1109_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回目の世界の工場ごとの効き目と、本社工場の1回の95%の幅
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    x = np.arange(12)
    cols = [ORANGE if i == HQ else BLUE for i in range(12)]
    ax.bar(x, tau[0], color=cols, width=0.65)
    ax.axhspan(e1 - Z * se1, e1 + Z * se1, color=ORANGE, alpha=0.15, lw=0)
    ax.axhline(tau[0].mean(), color=INK, lw=1, ls="--")
    ax.text(-0.4, tau[0].mean() + 0.3, f"12工場の平均 {tau[0].mean():.3f}", fontsize=9, color=INK)
    ax.text(-0.4, e1 + Z * se1 + 0.3, f"本社工場で20枚ずつ刷った95%の幅 {e1 - Z * se1:.3f}〜{e1 + Z * se1:.3f}", fontsize=9, color=ORANGE)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\n{int(h)}%" for n, h in zip(NAMES, HUM)], fontsize=8)
    ax.set_ylabel("本当の効き目（にじみの幅の減り、µm）")
    ax.set_xlabel("工場（下は湿度。橙が本社工場）")
    ax.set_ylim(0, max(tau[0].max(), e1 + Z * se1) + 3)
    ax.set_title("1回目の世界の工場ごとの効き目（置いた値）")
    save(fig, "a1109_sites.png", SRC, y=-0.04)

    # 図2：枚数を増やしたとき、幅に入る割合
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
    ns = [20, 80, 320]
    for d, c, lab in [("hq", ORANGE, "本社工場1か所"), ("random1", BLUE, "でたらめな1か所")]:
        sub = base_df[base_df.design == d]
        axes[0].plot(ns, sub.cover_12_average * 100, "o-", color=c, label=lab)
        axes[1].plot(ns, sub.cover_other_sites * 100, "o-", color=c, label=lab)
    sub = base_df[base_df.design == "four"]
    axes[0].plot(ns, sub.cover_12_average_site * 100, "o-", color=GREEN, label="4か所に分け、4か所の散らばりから幅")
    axes[0].plot(ns, sub.cover_12_average_sheet * 100, "o--", color=GRAY, label="4か所に分け、1枚ごとのばらつきだけで幅")
    axes[1].plot(ns, sub.cover_other_sites_site * 100, "o-", color=GREEN)
    axes[1].plot(ns, sub.cover_other_sites_sheet * 100, "o--", color=GRAY)
    for ax, ttl in [(axes[0], "12工場の平均の効き目が95%の幅に入った割合"), (axes[1], "ほかの工場の効き目が95%の幅に入った割合")]:
        ax.set_xscale("log")
        ax.minorticks_off()
        ax.set_xticks(ns)
        ax.set_xticklabels([str(v) for v in ns])
        ax.set_xlabel("1つの乾かし方あたりの枚数（合計、4か所なら4等分）")
        ax.set_title(ttl, fontsize=11)
        ax.set_ylim(0, 100)
        ax.axhline(95, color=GRAY, lw=0.8, ls=":")
    axes[0].set_ylabel("入った割合（%、2,000回）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8.5, loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.0))
    save(fig, "a1109_coverage.png", SRC, y=-0.11)

    # 図3：確かめ（16通り）：12工場の平均が幅に入った割合
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.9), sharey=True)
    for ax, sd in zip(axes, [0.0, 1.0, 2.0, 4.0]):
        for d, colname, c, lab in [("hq", "cover_12_average", ORANGE, "本社工場1か所"), ("random1", "cover_12_average", BLUE, "でたらめな1か所"),
                                   ("four", "cover_12_average_site", GREEN, "4か所（散らばりから幅）")]:
            sub = g[(g.design == d) & (g.site_sd == sd)]
            ax.plot(sub.slope, sub[colname] * 100, "o-", color=c, label=lab)
        ax.set_title(f"工場ごとの説明できない違い {sd:g}µm", fontsize=10)
        ax.set_xlabel("湿度1%あたりの効き目の変わり方（µm）", fontsize=9.5)
        ax.set_ylim(0, 100)
        ax.set_xticks([0, 0.25, 0.5, 1.0])
        ax.axhline(95, color=GRAY, lw=0.8, ls=":")
    axes[0].set_ylabel("12工場の平均が95%の幅に入った割合（%）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=9, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("12工場の平均の効き目が、20枚ずつで試した95%の幅に入った割合（16通り、各2,000回）", y=1.03)
    save(fig, "a1109_robust.png", SRC, y=-0.13)

    print(json.dumps({k: out[k] for k in ["true_effects", "coverage_by_sheets", "grid_ranges", "world1_example"]}, ensure_ascii=False, indent=1))
    print(g.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
