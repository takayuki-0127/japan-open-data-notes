"""1052 概算が「当たった」と言えるのは、実際の値の何倍以内なのか？（架空のデータ）

架空の町の架空のサービスの件数を当てる、架空の概算の問い。本当の件数は10〜100万件（対数で一様）。
概算する人の答え＝本当の件数×癖×exp(σ×z)。σ（外れやすさ）と癖は作成者が置く。
「k 倍以内なら当たり」の物差しを変えて、当たりの割合・人の見分けやすさを数える。
"""
import json
from math import erf, log, sqrt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, NullLocator
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1052
SRC = "架空の概算の問いと答え（作成者が乱数で作成、seed 1052）"
LO, HI = 1e1, 1e6
KS = [1.25, 1.5, 2, 3, 5, 10]
PEOPLE = [("よく知っている人（σ0.3）", 0.3, 1.0), ("要素に分けて概算する人（σ0.6）", 0.6, 1.0),
          ("ざっくり言う人（σ1.0）", 1.0, 1.0), ("あまり知らない人（σ1.5）", 1.5, 1.0),
          ("低めに言う癖のある人（σ0.6・0.85倍）", 0.6, 0.85)]
N_Q = 400000


def Phi(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def within_k_formula(sig, k, bias=1.0):
    mu = log(bias)
    return Phi((log(k) - mu) / sig) - Phi((-log(k) - mu) / sig)


def answers(rng, n, sig, bias):
    truth = np.exp(rng.uniform(np.log(LO), np.log(HI), n))
    return truth, truth * bias * np.exp(sig * rng.standard_normal(n))


def hit_table(rng):
    rows = []
    truth = np.exp(rng.uniform(np.log(LO), np.log(HI), N_Q))
    base_guess = np.sqrt(LO * HI)          # どの問いにも範囲の真ん中（約3,162件）を言う
    for name, sig, bias in PEOPLE + [("どの問いにも範囲の真ん中を言う", None, None)]:
        if sig is None:
            est = np.full(N_Q, base_guess)
        else:
            est = truth * bias * np.exp(sig * rng.standard_normal(N_Q))
        r = est / truth
        row = {"person": name, "sigma": sig, "bias": bias}
        for k in KS:
            row[f"within_{k}x_pct"] = round(float(((r <= k) & (r >= 1 / k)).mean()) * 100, 2)
            if sig is not None:
                row[f"within_{k}x_formula_pct"] = round(within_k_formula(sig, k, bias) * 100, 2)
            else:
                row[f"within_{k}x_formula_pct"] = round(2 * log(k) / log(HI / LO) * 100, 2)
        for p in [0.25, 0.5, 1.0]:
            row[f"within_pm{int(p*100)}pct_pct"] = round(float((np.abs(r - 1) <= p).mean()) * 100, 2)
        row["median_miss_times"] = round(float(np.exp(np.median(np.abs(np.log(r))))), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def discriminate(rng, sig_a, sig_b, n_q, reps=20000):
    """σ の小さい人 A と大きい人 B が同じ n_q 問に答えたとき、A のほうが良いと出る割合（同点は半分と数える）"""
    za = sig_a * rng.standard_normal((reps, n_q)); zb = sig_b * rng.standard_normal((reps, n_q))
    out = {}
    for k in KS:
        ha = (np.abs(za) <= log(k)).sum(1); hb = (np.abs(zb) <= log(k)).sum(1)
        out[f"hits_{k}x"] = round(float((ha > hb).mean() + 0.5 * (ha == hb).mean()) * 100, 2)
    ma = np.abs(za).mean(1); mb = np.abs(zb).mean(1)
    out["mean_abs_log"] = round(float((ma < mb).mean() + 0.5 * (ma == mb).mean()) * 100, 2)
    return out


def main():
    rng = np.random.default_rng(SEED)
    tab = hit_table(rng)
    tab.to_csv(RES / "hit_rates.csv", index=False)
    maxdiff = 0.0
    for _, r in tab.iterrows():
        for k in KS:
            maxdiff = max(maxdiff, abs(r[f"within_{k}x_pct"] - r[f"within_{k}x_formula_pct"]))

    # data：要素に分けて概算する人の40問の答え（1回分）
    t, e = answers(np.random.default_rng(SEED + 1), 40, 0.6, 1.0)
    pd.DataFrame({"question": np.arange(1, 41), "true_count": np.round(t, 1), "estimate": np.round(e, 1),
                  "ratio": np.round(e / t, 4)}).to_csv(DATA / "answers_40.csv", index=False)

    # 見分けやすさ：問いの数 × 比べる2人（36通り）
    disc = []
    for n_q in [5, 10, 20, 40]:
        for a, b in [(0.3, 0.6), (0.6, 1.0), (1.0, 1.5)]:
            d = discriminate(np.random.default_rng(SEED * 100 + len(disc)), a, b, n_q)
            best_k = max(KS, key=lambda k: d[f"hits_{k}x"])
            disc.append({"n_questions": n_q, "sigma_a": a, "sigma_b": b, **d, "best_k": best_k})
    disc = pd.DataFrame(disc)
    disc.to_csv(RES / "discrimination.csv", index=False)
    hits_cols = [f"hits_{k}x" for k in KS]
    disc["best_hits"] = disc[hits_cols].max(1)
    summary_disc = {
        "best_k_by_pair": {f"{a}対{b}": sorted(set(disc[(disc.sigma_a == a) & (disc.sigma_b == b)].best_k.tolist()))
                           for a, b in [(0.3, 0.6), (0.6, 1.0), (1.0, 1.5)]},
        "mean_abs_beats_best_hits": int((disc.mean_abs_log >= disc.best_hits).sum()), "n_settings": int(len(disc)),
        "k10_range_pct": [float(disc["hits_10x"].min()), float(disc["hits_10x"].max())],
        "k2_range_pct": [float(disc["hits_2x"].min()), float(disc["hits_2x"].max())],
    }

    # 確かめ：癖（何倍に言うか）を変えると、物差しごとの当たりはどう動くか（σ0.6）
    bias_rows = []
    for bias in [0.6, 0.7, 0.8, 0.85, 0.9, 1.0, 1.1, 1.25, 1.5]:
        tt, ee = answers(np.random.default_rng(SEED * 10 + len(bias_rows)), 200000, 0.6, bias)
        r = ee / tt
        bias_rows.append({"bias": bias, "within_pm50pct_pct": round(float((np.abs(r - 1) <= .5).mean()) * 100, 2),
                          "within_pm100pct_pct": round(float((np.abs(r - 1) <= 1).mean()) * 100, 2),
                          "within_1.5x_pct": round(float(((r <= 1.5) & (r >= 1 / 1.5)).mean()) * 100, 2),
                          "within_2x_pct": round(float(((r <= 2) & (r >= .5)).mean()) * 100, 2)})
    bias_tab = pd.DataFrame(bias_rows)
    bias_tab.to_csv(RES / "by_bias.csv", index=False)

    # 確かめ：問いの範囲（桁の幅）を変えると、範囲の真ん中を言うだけの当たりはどう動くか（式どおり）
    widths = []
    for dec in [2, 3, 5, 7]:
        widths.append({"decades": dec, **{f"within_{k}x_pct": round(min(1.0, 2 * log(k) / log(10 ** dec)) * 100, 2) for k in KS}})
    widths = pd.DataFrame(widths)
    widths.to_csv(RES / "midpoint_by_range.csv", index=False)

    out = {"settings": {"true_range": [LO, HI], "questions": N_Q, "people": [p[0] for p in PEOPLE]},
           "hit_rates": tab.to_dict("records"), "max_abs_sim_minus_formula_pt": round(maxdiff, 3),
           "discrimination": disc.drop(columns="best_hits").to_dict("records"), "discrimination_summary": summary_disc,
           "midpoint_by_range": widths.to_dict("records"), "by_bias_sigma06": bias_tab.to_dict("records")}
    json.dump(out, open(RES / "a1052_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：物差し k ごとの当たりの割合
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = [GREEN, BLUE, LIGHT, GRAY, ORANGE, INK]
    for (_, r), c in zip(tab.iterrows(), cols):
        ls = ":" if "真ん中" in r.person else ("--" if "低め" in r.person else "-")
        ax.plot(KS, [r[f"within_{k}x_pct"] for k in KS], marker="o", ls=ls, color=c, label=r.person, ms=4)
    ax.set_xscale("log"); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(KS); ax.set_xticklabels([f"{k:g}倍" for k in KS])
    ax.set_ylim(0, 100); ax.set_xlabel("「当たり」とする幅（実際の値の何倍以内か、対数の目盛り）")
    ax.set_ylabel("当たりの割合（%）")
    ax.legend(frameon=False, fontsize=8, loc="center left", bbox_to_anchor=(1.01, 0.5))
    ax.set_title("10倍以内なら、範囲の真ん中を言うだけでも40%が「当たり」")
    save(fig, "a1052_hit_rates.png", SRC)

    # 図2：癖（何倍に言うか）と、物差しごとの当たり（σ0.6）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for col, c, ls, lab in [("within_pm100pct_pct", ORANGE, "--", "±100%以内（0〜2倍）"), ("within_pm50pct_pct", ORANGE, ":", "±50%以内（0.5〜1.5倍）"),
                            ("within_2x_pct", BLUE, "-", "2倍以内（0.5〜2倍）"), ("within_1.5x_pct", BLUE, "-.", "1.5倍以内（0.67〜1.5倍）")]:
        ax.plot(bias_tab.bias, bias_tab[col], marker="o", ms=4, color=c, ls=ls, label=lab)
    ax.axvline(1, color=GRAY, lw=.8)
    ax.set_xscale("log"); ax.xaxis.set_minor_locator(NullLocator()); ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks(bias_tab.bias); ax.set_xticklabels([f"{b:g}" for b in bias_tab.bias])
    ax.set_ylim(0, 100); ax.set_xlabel("癖（いつも実際の何倍に言うか、対数の目盛り。外れやすさσ0.6）")
    ax.set_ylabel("当たりの割合（%）"); ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("「±何%以内」で数えると、低めに言う人ほど当たって見える")
    save(fig, "a1052_bias.png", SRC)

    # 図3：10問で σ0.6 と σ1.0 を見分ける（物差しごと）
    d10 = disc[(disc.n_questions == 10) & (disc.sigma_a == 0.6)].iloc[0]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    names = [f"{k:g}倍以内\nの数" for k in KS] + ["外れの大きさ\nの平均"]
    vals = [d10[f"hits_{k}x"] for k in KS] + [d10["mean_abs_log"]]
    ax.bar(names, vals, color=[LIGHT] * len(KS) + [BLUE])
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=8.5)
    ax.axhline(50, color=GRAY, lw=.8, ls="--"); ax.text(-0.45, 51, "五分五分（50%）", color=GRAY, fontsize=8, ha="left", va="bottom")
    ax.set_ylim(0, 100); ax.tick_params(axis="x", labelsize=8.5)
    ax.set_ylabel("σ0.6の人のほうが良いと出る割合（%）", fontsize=10)
    ax.set_title("σ0.6の人とσ1.0の人を10問で比べると、当たりの数より\n外れの大きさの平均のほうが見分ける（2万回）", fontsize=12)
    save(fig, "a1052_discriminate.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
