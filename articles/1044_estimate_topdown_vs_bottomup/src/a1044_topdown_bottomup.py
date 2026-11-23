"""1044 全体から割合で割っていく概算と、1件ずつ積み上げる概算は、どれだけ食い違うのか？（架空のデータ）

架空のA町（12,000世帯）で、1年に自転車の修理が何件あるかを2通りで概算する。
①割っていく概算：世帯数 × 自転車を持つ世帯の割合 × 1年に修理に出す世帯の割合 × 出す世帯の1年の回数
  （世帯数のほかの3つの割合・回数は見込みで、対数で標準偏差 sigma の誤差を掛ける）
②積み上げる概算：町にある7店の1日の件数を何日か数え、営業日数（300日）を掛けて足す
正しい答え（町の世帯が1年に出す修理の件数）は作成者が置く。町の世帯が町の外の店に出す分と、
町の外の人が町の店に来る分があり、②はその分だけ違うものを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1044
SRC = "架空のA町の自転車の修理（作成者が乱数で作成、seed 1044）"
N_HH = 12_000
P_OWN = 0.55
LAM_MEAN, LAM_SHAPE = 0.9, 0.8
N_SHOP = 7
OPEN_DAYS = 300
WEEK = np.array([1, 1, 1, 1, 1.8, 1.8])      # 週6日営業、最後の2日（土日）は平日の1.8倍
SIGMA_N = 0.05
BASE = {"sigma": 0.35, "obs_days": 1, "out": 0.25, "inflow": 0.12}
N_TOWN = 200
N_TRIAL = 4000
N_TRIAL_GRID = 2000


def r(x, k=4):
    return round(float(x), k)


def make_towns(rng, n_town=N_TOWN):
    rows = []
    for t in range(n_town):
        own = rng.random(N_HH) < P_OWN
        lam = rng.gamma(LAM_SHAPE, LAM_MEAN / LAM_SHAPE, own.sum())
        k = rng.poisson(lam)
        rows.append({"town_id": t + 1, "households": N_HH, "owners": int(own.sum()),
                     "repairers": int((k > 0).sum()), "repairs": int(k.sum())})
    return pd.DataFrame(rows)


DAY_W = np.tile(WEEK, OPEN_DAYS // len(WEEK))
DAY_W = DAY_W / DAY_W.sum()


def one_trial(rng, town, sigma, obs_days, out, inflow):
    T = town["repairs"]
    f_true = np.array([town["households"], town["owners"] / town["households"],
                       town["repairers"] / town["owners"], town["repairs"] / town["repairers"]])
    err = np.r_[rng.normal(0, SIGMA_N), rng.normal(0, sigma, 3)]
    top = float(np.prod(f_true * np.exp(err)))
    # 町の店がこなす件数（1年の期待値）：町の世帯のうち町の店に出す分＋町の外から来る分
    v_in = rng.binomial(T, 1 - out) + rng.poisson(inflow * T)
    share = rng.dirichlet(np.full(N_SHOP, 2.0))
    bottom = 0.0
    for s in range(N_SHOP):
        d = rng.choice(OPEN_DAYS, obs_days, replace=False)
        cnt = rng.poisson(v_in * share[s] * DAY_W[d])
        bottom += cnt.mean() * OPEN_DAYS
    # 町の外とのやり取りの割合も見込み（対数で sigma の誤差）で割り戻す
    adj_true = 1 - out + inflow
    bottom_adj = bottom / (adj_true * np.exp(rng.normal(0, sigma)))
    return top / T, bottom / T, v_in / T, bottom_adj / T


def run(rng, towns, n, sigma, obs_days, out, inflow):
    idx = rng.integers(0, len(towns), n)
    recs = towns.to_dict("records")
    a = np.array([one_trial(rng, recs[i], sigma, obs_days, out, inflow) for i in idx])
    return pd.DataFrame(a, columns=["top", "bottom", "vin", "bottom_adj"])


def summarize(d):
    lt, lb, lba = np.log(d.top), np.log(d.bottom.clip(lower=1e-9)), np.log(d.bottom_adj.clip(lower=1e-9))
    tb = d.top / d.bottom
    return {"top_med": d.top.median(), "top_p10": d.top.quantile(.1), "top_p90": d.top.quantile(.9),
            "top_logsd": lt.std(),
            "bottom_med": d.bottom.median(), "bottom_p10": d.bottom.quantile(.1), "bottom_p90": d.bottom.quantile(.9),
            "bottom_logsd": lb.std(), "vin_med": d.vin.median(),
            "bottom_over_vin_logsd": (lb - np.log(d.vin)).std(),
            "tb_med": tb.median(), "tb_p10": tb.quantile(.1), "tb_p90": tb.quantile(.9),
            "tb_gt2": ((tb > 2) | (tb < .5)).mean(), "tb_gt15": ((tb > 1.5) | (tb < 1 / 1.5)).mean(),
            "top_gt2": ((d.top > 2) | (d.top < .5)).mean(), "bottom_gt2": ((d.bottom > 2) | (d.bottom < .5)).mean(),
            "top_within15": ((d.top <= 1.5) & (d.top >= 1 / 1.5)).mean(),
            "bottom_within15": ((d.bottom <= 1.5) & (d.bottom >= 1 / 1.5)).mean(),
            "p_bottom_closer": (np.abs(lb) < np.abs(lt)).mean(),
            "adj_med": d.bottom_adj.median(), "adj_p10": d.bottom_adj.quantile(.1), "adj_p90": d.bottom_adj.quantile(.9),
            "adj_logsd": lba.std(), "p_adj_closer": (np.abs(lba) < np.abs(lt)).mean(),
            "geo_med": np.exp((lt + lba) / 2).median(),
            "geo_within15": ((np.exp((lt + lba) / 2) <= 1.5) & (np.exp((lt + lba) / 2) >= 1 / 1.5)).mean()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    towns = make_towns(rng)
    towns.to_csv(DATA / "towns.csv", index=False)

    # 基本
    base = run(np.random.default_rng(SEED * 10), towns, N_TRIAL, **BASE)
    sb = summarize(base)
    base.round(5).to_csv(DATA / "trials_base.csv", index_label="trial")

    # 1つずつ外す：①の誤差だけ／②の数え方の振れだけ／町の外とのやり取りだけ
    def part_row(s):
        return {"tb_med": r(s["tb_med"], 2), "tb_p10": r(s["tb_p10"], 2), "tb_p90": r(s["tb_p90"], 2),
                "tb_gt15_pct": r(s["tb_gt15"] * 100, 2), "tb_gt2_pct": r(s["tb_gt2"] * 100, 2)}
    parts = {"基本": part_row(sb)}
    for name, kw in [("町の外とのやり取りなし", {**BASE, "out": 0.0, "inflow": 0.0}),
                     ("②を300日すべて数える", {**BASE, "obs_days": 300}),
                     ("①の見込みが正しい（誤差0）", {**BASE, "sigma": 0.0})]:
        d = run(np.random.default_rng(SEED * 20 + len(parts)), towns, N_TRIAL, **kw)
        s = summarize(d)
        parts[name] = part_row(s)
    pd.DataFrame(parts).T.to_csv(RES / "parts.csv", index_label="case")

    # 27通り
    rows = []
    gi = 0
    for sg in [0.2, 0.35, 0.5]:
        for od in [1, 3, 10]:
            for out in [0.0, 0.25, 0.4]:
                d = run(np.random.default_rng(SEED * 100 + gi), towns, N_TRIAL_GRID, sg, od, out, BASE["inflow"])
                s = summarize(d)
                rows.append({"sigma": sg, "obs_days": od, "out": out, "inflow": BASE["inflow"],
                             "formula_vin_ratio": r(1 - out + BASE["inflow"]),
                             **{k: r(s[k]) for k in ["tb_med", "tb_p10", "tb_p90", "tb_gt2", "tb_gt15", "top_logsd",
                                                     "bottom_logsd", "p_bottom_closer", "p_adj_closer"]}})
                gi += 1
    g = pd.DataFrame(rows)
    g.to_csv(RES / "grid.csv", index=False)

    f_top_sd = np.sqrt(SIGMA_N ** 2 + 3 * BASE["sigma"] ** 2)
    f_vin = 1 - BASE["out"] + BASE["inflow"]
    pct = lambda x: r(x * 100, 2)
    out = {
        "headline": {
            "true_repairs_mean": r(towns.repairs.mean(), 1),
            "top_p10": r(sb["top_p10"], 2), "top_p90": r(sb["top_p90"], 2), "top_med": r(sb["top_med"], 2),
            "bottom_p10": r(sb["bottom_p10"], 2), "bottom_p90": r(sb["bottom_p90"], 2), "bottom_med": r(sb["bottom_med"], 2),
            "top_over_bottom_med": r(sb["tb_med"], 2), "top_over_bottom_p10": r(sb["tb_p10"], 2),
            "top_over_bottom_p90": r(sb["tb_p90"], 2),
            "differ_2x_pct": pct(sb["tb_gt2"]), "differ_15x_pct": pct(sb["tb_gt15"]),
            "top_off_2x_pct": pct(sb["top_gt2"]), "bottom_off_2x_pct": pct(sb["bottom_gt2"]),
            "top_within15_pct": pct(sb["top_within15"]), "bottom_within15_pct": pct(sb["bottom_within15"]),
            "p_bottom_closer_pct": pct(sb["p_bottom_closer"]),
            "adj_med": r(sb["adj_med"], 2), "adj_p10": r(sb["adj_p10"], 2), "adj_p90": r(sb["adj_p90"], 2),
            "p_adj_closer_pct": pct(sb["p_adj_closer"]),
            "geo_of_top_and_adj_within15_pct": pct(sb["geo_within15"]),
            "grid_tb_med_min": r(g.tb_med.min(), 2), "grid_tb_med_max": r(g.tb_med.max(), 2),
            "grid_gt2_min_pct": pct(g.tb_gt2.min()), "grid_gt2_max_pct": pct(g.tb_gt2.max()),
            "grid_p_bottom_closer_min_pct": pct(g.p_bottom_closer.min()),
            "grid_p_bottom_closer_max_pct": pct(g.p_bottom_closer.max()),
            "grid_p_adj_closer_min_pct": pct(g.p_adj_closer.min()),
            "grid_p_adj_closer_max_pct": pct(g.p_adj_closer.max()),
            "grid_out0_gt2_min_pct": pct(g[g.out == 0].tb_gt2.min()), "grid_out0_gt2_max_pct": pct(g[g.out == 0].tb_gt2.max()),
            "grid_out04_gt2_min_pct": pct(g[g.out == 0.4].tb_gt2.min()),
            "grid_out04_gt2_max_pct": pct(g[g.out == 0.4].tb_gt2.max()),
            "grid_out0_tb_med_min": r(g[g.out == 0].tb_med.min(), 2), "grid_out0_tb_med_max": r(g[g.out == 0].tb_med.max(), 2),
            "grid_out04_tb_med_min": r(g[g.out == 0.4].tb_med.min(), 2),
            "grid_out04_tb_med_max": r(g[g.out == 0.4].tb_med.max(), 2),
            "grid_sigma02_gt2_max_pct": pct(g[g.sigma == 0.2].tb_gt2.max()),
            "grid_sigma05_gt2_min_pct": pct(g[g.sigma == 0.5].tb_gt2.min()),
        },
        "formula": {"top_logsd": r(f_top_sd), "top_logsd_sim": r(sb["top_logsd"]),
                    "top_x_div_at_1sd": r(np.exp(f_top_sd), 2), "within15_lower": r(1 / 1.5, 2),
                    "vin_ratio": r(f_vin), "vin_ratio_sim_median": r(sb["vin_med"]),
                    "top_over_bottom_if_only_flow": r(1 / f_vin, 2),
                    "flow_only_out0": r(1 / (1 + BASE["inflow"]), 2), "flow_only_out04": r(1 / (0.6 + BASE["inflow"]), 2),
                    "bottom_over_vin_logsd_sim": r(sb["bottom_over_vin_logsd"])},
        "base_summary": {k: r(v) for k, v in sb.items()},
        "parts": parts,
        "constants": {"households": N_HH, "p_own": P_OWN, "lam_mean": LAM_MEAN, "lam_shape": LAM_SHAPE,
                      "n_shop": N_SHOP, "open_days": OPEN_DAYS, "weekend_factor": 1.8, "sigma_households": SIGMA_N,
                      **BASE, "n_town": N_TOWN, "n_trial": N_TRIAL, "n_trial_grid": N_TRIAL_GRID},
        "grid_n": int(len(g)),
    }
    json.dump(out, open(RES / "a1044_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：2つの概算の当たり（正しい件数の何倍か）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.exp(np.linspace(np.log(0.2), np.log(5), 60))
    ax.hist(base.top, bins=bins, color=ORANGE, alpha=.6, label="①割っていく（世帯数×割合×割合×回数）")
    ax.hist(base.bottom, bins=bins, color=BLUE, alpha=.6, label="②積み上げる（7店×1日の件数×300日）")
    ax.set_xscale("log"); ax.set_xticks([0.25, 0.5, 1, 2, 4]); ax.set_xticklabels(["0.25倍", "0.5倍", "1倍", "2倍", "4倍"])
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.axvline(1, color=INK, lw=1); ax.axvline(f_vin, color=BLUE, lw=1, ls="--")
    ax.annotate(f"町の店がこなす件数\n（{f_vin:.2f}倍）", xy=(f_vin, ax.get_ylim()[1] * 0.75), xytext=(0.3, ax.get_ylim()[1] * 0.75),
                color=BLUE, fontsize=8.5, ha="center", va="center", arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 0.8})
    ax.set_xlabel("概算 ÷ 正しい件数（町の世帯が1年に出す修理、対数の目盛り）"); ax.set_ylabel("回数（4,000回のうち）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("①は広く外れ、②は幅が狭いが町の店の件数のほうに寄る（基本の置き方）")
    save(fig, "a1044_two_estimates.png", SRC)

    # 図2：食い違い（①÷②が2倍以上離れた回）を、しくみを1つずつ外して
    p = pd.DataFrame(parts).T
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    names = list(p.index)[::-1]
    vals = p.loc[names, "tb_gt2_pct"].values
    vals15 = p.loc[names, "tb_gt15_pct"].values
    y = np.arange(len(names))
    ax.barh(y + 0.2, vals15, height=0.38, color=LIGHT, label="1.5倍以上離れた回")
    ax.barh(y - 0.2, vals, height=0.38, color=BLUE, label="2倍以上離れた回")
    for i, (v, w) in enumerate(zip(vals, vals15)):
        ax.text(v + 1, i - 0.2, f"{v:.1f}%", va="center", fontsize=8.5)
        ax.text(w + 1, i + 0.2, f"{w:.1f}%", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(names); ax.set_xlim(0, 100)
    ax.set_xlabel("①÷②が離れた回の割合（%、4,000回）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("食い違いの多くは①の見込みの誤差から来る")
    save(fig, "a1044_parts.png", SRC)

    # 図3：27通りの「2倍以上食い違う回」
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cols = {0.0: GRAY, 0.25: BLUE, 0.4: ORANGE}
    xlab = []
    for j, (sg, od) in enumerate([(sg, od) for sg in [0.2, 0.35, 0.5] for od in [1, 3, 10]]):
        xlab.append(f"{sg}\n{od}日")
        for k, out_ in enumerate([0.0, 0.25, 0.4]):
            v = g[(g.sigma == sg) & (g.obs_days == od) & (g.out == out_)].tb_gt2.iloc[0] * 100
            ax.bar(j + (k - 1) * 0.27, v, width=0.27, color=cols[out_],
                   label=f"町の外の店に出す割合 {int(out_*100)}%" if j == 0 else None)
    ax.set_xticks(range(9)); ax.set_xticklabels(xlab, fontsize=8.5); ax.set_ylim(0, 100)
    ax.set_xlabel("①の見込みの誤差（対数の標準偏差）と、②で数えた日数")
    ax.set_ylabel("2倍以上食い違った回（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("27通り：見込みの誤差が大きいほど、2つの概算は食い違う")
    save(fig, "a1044_grid.png", SRC, y=-0.06)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1), json.dumps(out["formula"], ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
