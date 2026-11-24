"""1196 返事が遅いほど満足度が低く見えるのは、遅さのせいか、難しい問い合わせほど遅く満足も低いからか？（架空のデータ）

架空の会社の問い合わせ窓口。問い合わせごとに「難しさ」を作成者が置き、
 ・返事までの時間は、難しいほど長く、その日の混み具合でも長くなる
 ・満足度（10点満点のアンケート）は、難しいほど低く、返事が1時間遅れるごとに b 点下がる（b は作成者が置いた本当の遅さの効き目）
とした。記録に残るのは、問い合わせの種類（4つ）、返事までの時間、アンケートに答えた人の満足度だけで、難しさそのものは残らない。
「返事が1時間遅いと満足度が何点下がるか」を次の数え方で出し、置いた b とのずれを数える。
 ① 返事までの時間と満足度の傾き
 ② ①に問い合わせの種類もいっしょに入れたときの傾き
 ③ ①に本当の難しさもいっしょに入れたときの傾き（記録には無い。作りの確かめ）
 ④ 日ごとの平均どうしの傾き（混んだ日と空いた日の差だけを使う）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1196
SRC = "架空の会社の問い合わせ窓口とアンケート（作成者が置いた難しさ・混み具合・満足度の決まり方からの乱数、seed 1196）"
BASE = {"days": 200, "per_day": 60, "answer_rate": 0.3,
        "median_h": 6.0, "k_diff": 0.5, "sigma_day": 0.4, "sigma_e": 0.5,
        "R_cat": 0.5, "gamma_day": 0.0,
        "s0": 7.0, "a_diff": 1.0, "sigma_s": 1.5}
B_MAIN = [0.0, 0.05]
REPS = 300
GRID_B = [0.0, 0.05, 0.1]
GRID_K = [0.25, 0.5, 0.75]       # 難しさが返事までの時間を延ばす強さ
GRID_R = [0.2, 0.5, 0.8]         # 問い合わせの種類で難しさがどれだけ分かるか（分散の割合）
GRID_G = [0.0, 0.3]              # 混んだ日ほど難しい問い合わせが多い強さ
GRID_REPS = 100
CAT_LEVELS = np.array([-1.5, -0.5, 0.5, 1.5]) / np.sqrt(1.25)   # 平均0・分散1
METHODS = ["m1_simple", "m2_with_type", "m3_with_true_difficulty", "m4_day_means"]
MLAB = {"m1_simple": "① 時間と満足度の傾き", "m2_with_type": "② ①＋問い合わせの種類",
        "m3_with_true_difficulty": "③ ①＋本当の難しさ（記録に無い）", "m4_day_means": "④ 日ごとの平均どうし"}
BANDS = [(0, 2), (2, 6), (6, 12), (12, 24), (24, 1e9)]
BLAB = ["2時間未満", "2〜6時間", "6〜12時間", "12〜24時間", "24時間以上"]


def r(x, d=4):
    return round(float(x), d)


def make(rng, b, P=BASE):
    D, m = P["days"], P["per_day"]
    n = D * m
    day = np.repeat(np.arange(D), m)
    c_day = rng.normal(0, P["sigma_day"], D)
    cat = rng.integers(0, 4, n)
    zc = CAT_LEVELS[cat]
    d = np.sqrt(P["R_cat"]) * zc + np.sqrt(1 - P["R_cat"]) * rng.normal(0, 1, n)
    d = d + P["gamma_day"] * c_day[day] / P["sigma_day"]       # 混んだ日ほど難しい（γ=0 なら無し）
    T = np.exp(np.log(P["median_h"]) + P["k_diff"] * d + c_day[day] + rng.normal(0, P["sigma_e"], n))
    S = P["s0"] - P["a_diff"] * d - b * T + rng.normal(0, P["sigma_s"], n)
    ans = rng.random(n) < P["answer_rate"]
    return pd.DataFrame({"day": day, "type": cat, "difficulty": d, "reply_h": T, "satisfaction": S, "answered": ans})


def ols_slope(y, X):
    X = np.column_stack([np.ones(len(y))] + X)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(beta[1])


def estimates(df):
    a = df[df.answered]
    y = a.satisfaction.values
    T = a.reply_h.values
    dummies = [(a.type.values == k).astype(float) for k in range(1, 4)]
    g = a.groupby("day").agg(s_mean=("satisfaction", "mean"), t_mean=("reply_h", "mean"))
    return {"m1_simple": ols_slope(y, [T]),
            "m2_with_type": ols_slope(y, [T] + dummies),
            "m3_with_true_difficulty": ols_slope(y, [T, a.difficulty.values]),
            "m4_day_means": ols_slope(g.s_mean.values, [g.t_mean.values])}


def bands(df):
    a = df[df.answered]
    out = []
    for (lo, hi), lab in zip(BANDS, BLAB):
        s = a[(a.reply_h >= lo) & (a.reply_h < hi)]
        out.append({"band": lab, "n": len(s), "satisfaction_mean": s.satisfaction.mean(), "difficulty_mean": s.difficulty.mean()})
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"seed": SEED, "base": BASE, "reps": REPS}
    # 基本：b=0 と 0.05
    est_rows, band_rows = [], []
    one = None
    for b in B_MAIN:
        E = {k: [] for k in METHODS}
        B = []
        for i in range(REPS):
            df = make(rng, b)
            if b == 0.0 and i == 0:
                one = df
            e = estimates(df)
            for k in METHODS:
                E[k].append(e[k])
            B.append(bands(df))
        for k in METHODS:
            v = np.array(E[k])
            est_rows.append({"b_true": b, "method": k, "label": MLAB[k], "mean": r(v.mean()), "p10": r(np.percentile(v, 10)),
                             "p90": r(np.percentile(v, 90)), "slope_true": -b + 0.0, "bias": r(v.mean() + b),
                             "share_negative_pct": r(100 * (v < 0).mean(), 2)})
        for j, lab in enumerate(BLAB):
            band_rows.append({"b_true": b, "band": lab, "n_mean": r(np.mean([x[j]["n"] for x in B]), 1),
                              "satisfaction_mean": r(np.mean([x[j]["satisfaction_mean"] for x in B]), 3),
                              "difficulty_mean": r(np.mean([x[j]["difficulty_mean"] for x in B]), 3)})
    est = pd.DataFrame(est_rows)
    est.to_csv(RES / "estimates_base.csv", index=False)
    bdf = pd.DataFrame(band_rows)
    bdf.to_csv(RES / "bands_base.csv", index=False)
    res["estimates_base"] = est_rows
    res["bands_base"] = band_rows
    # 1回分の記述
    a1 = one[one.answered]
    res["one_run_b0"] = {"n_answered": int(len(a1)),
                         "corr_reply_satisfaction": r(np.corrcoef(a1.reply_h, a1.satisfaction)[0, 1]),
                         "corr_reply_difficulty": r(np.corrcoef(a1.reply_h, a1.difficulty)[0, 1]),
                         "median_reply_h": r(a1.reply_h.median(), 3), "mean_reply_h": r(a1.reply_h.mean(), 3)}
    # 確かめ：54通り
    g = []
    for b in GRID_B:
        for k in GRID_K:
            for R in GRID_R:
                for gm in GRID_G:
                    P = dict(BASE, k_diff=k, R_cat=R, gamma_day=gm)
                    E = {m: [] for m in METHODS}
                    for _ in range(GRID_REPS):
                        e = estimates(make(rng, b, P))
                        for m in METHODS:
                            E[m].append(e[m])
                    row = {"b_true": b, "k_diff": k, "R_cat": R, "gamma_day": gm}
                    for m in METHODS:
                        v = np.array(E[m])
                        row[f"{m}_mean"] = r(v.mean())
                        row[f"{m}_bias"] = r(v.mean() + b)
                        row[f"{m}_p10"] = r(np.percentile(v, 10))
                        row[f"{m}_p90"] = r(np.percentile(v, 90))
                    g.append(row)
    grid = pd.DataFrame(g)
    grid.to_csv(RES / "grid.csv", index=False)
    summ = {}
    for gm in GRID_G:
        d = grid[grid.gamma_day == gm]
        for m in METHODS:
            summ[f"gamma{gm}_{m}_bias_range"] = [r(d[f"{m}_bias"].min()), r(d[f"{m}_bias"].max())]
    d0 = grid[grid.b_true == 0]
    summ["b0_m1_mean_range"] = [r(d0.m1_simple_mean.min()), r(d0.m1_simple_mean.max())]
    summ["b0_m2_mean_range"] = [r(d0.m2_with_type_mean.min()), r(d0.m2_with_type_mean.max())]
    by_r = {}
    for R in GRID_R:
        d = grid[(grid.R_cat == R) & (grid.gamma_day == 0)]
        by_r[str(R)] = {"m1_bias": [r(d.m1_simple_bias.min()), r(d.m1_simple_bias.max())],
                        "m2_bias": [r(d.m2_with_type_bias.min()), r(d.m2_with_type_bias.max())]}
    summ["by_R_gamma0"] = by_r
    g0 = grid[grid.gamma_day == 0]
    summ["gamma0_m4_width_range"] = [r((g0.m4_day_means_p90 - g0.m4_day_means_p10).min()), r((g0.m4_day_means_p90 - g0.m4_day_means_p10).max())]
    summ["gamma0_m1_more_negative_than_true_count"] = int((g0.m1_simple_bias < 0).sum())
    summ["gamma0_m2_more_negative_than_true_count"] = int((g0.m2_with_type_bias < 0).sum())
    summ["gamma0_n"] = int(len(g0))
    res["grid_summary"] = summ

    # データ：b=0 の1回分（アンケートに答えた人だけ、記録に残る列＋本当の難しさ）
    out = a1[["day", "type", "reply_h", "satisfaction", "difficulty"]].copy()
    out["reply_h"] = out.reply_h.round(3)
    out["satisfaction"] = out.satisfaction.round(3)
    out["difficulty"] = out.difficulty.round(3)
    out.to_csv(DATA / "answers_b0_one_run.csv", index=False)

    # 図1 返事までの時間の帯ごとの満足度（b=0 と b=0.05）
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = np.arange(len(BLAB))
    for i, (b, col) in enumerate([(0.0, GRAY), (0.05, BLUE)]):
        v = bdf[bdf.b_true == b].satisfaction_mean.values
        ax.bar(x + (i - 0.5) * 0.38, v, 0.38, color=col, label=f"遅さの本当の効き目 {b:g}点／時間" + ("（遅さは効かない）" if b == 0 else ""))
        for xi, vi in zip(x, v):
            ax.text(xi + (i - 0.5) * 0.38, vi + 0.08, f"{vi:g}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(BLAB)
    ax.set_ylim(0, 10)
    ax.set_ylabel("満足度の平均（10点満点）")
    ax.set_xlabel("返事までの時間")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("遅さが効かないと置いても、返事が遅い問い合わせほど満足度は低く出た")
    save(fig, "a1196_bands.png", "出典：" + SRC + "。300回の平均")

    # 図2 4つの数え方（b=0 と 0.05、10〜90%）
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    y = np.arange(len(METHODS))[::-1]
    for i, (b, col) in enumerate([(0.0, GRAY), (0.05, BLUE)]):
        d = est[est.b_true == b].set_index("method").loc[METHODS]
        yy = y + (0.15 if i == 0 else -0.15)
        ax.errorbar(d["mean"], yy, xerr=[d["mean"] - d["p10"], d["p90"] - d["mean"]], fmt="o", color=col, capsize=3,
                    label=f"置いた効き目 {b:g}点／時間")
        ax.axvline(-b, color=col, ls="--", lw=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels([MLAB[m] for m in METHODS])
    ax.set_xlabel("返事が1時間遅いと満足度が何点変わるか（300回の平均と10〜90%）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("時間だけの傾き①は、置いた効き目より下にずれた（点線が置いた値）")
    save(fig, "a1196_estimates.png", "出典：" + SRC)

    # 図3 確かめ：種類で難しさが分かる度合いとずれ（γ=0 と 0.3、置いた効き目0.05）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    for ax, gm in zip(axes, GRID_G):
        d = grid[(grid.gamma_day == gm) & (grid.b_true == 0.05)]
        for j, (m, col, mk) in enumerate([("m1_simple", BLUE, "o"), ("m2_with_type", ORANGE, "s"), ("m4_day_means", GREEN, "^")]):
            base = d[d.k_diff == 0.5].sort_values("R_cat")
            lo = d.groupby("R_cat")[f"{m}_bias"].min().loc[GRID_R].values
            hi = d.groupby("R_cat")[f"{m}_bias"].max().loc[GRID_R].values
            xs = np.array(GRID_R) + (j - 1) * 0.03
            ax.vlines(xs, lo, hi, color=col, lw=4, alpha=0.35)
            ax.plot(xs, base[f"{m}_bias"].values, mk + "-", color=col, label=MLAB[m])
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.set_xticks(GRID_R)
        ax.set_xlabel("問い合わせの種類で難しさが分かる度合い")
        ax.set_title("混んだ日に難しい問い合わせが多くない" if gm == 0 else "混んだ日ほど難しい問い合わせが多い（強さ0.3）", fontsize=11)
    axes[0].set_ylabel("置いた効き目とのずれ（点／時間）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3)
    fig.suptitle("置いた効き目0.05のとき：種類を入れても②のずれは残り、④は日ごとの難しさが混ざると大きく外れる", y=1.02, fontsize=12)
    save(fig, "a1196_grid.png", "出典：" + SRC + "。線と印は難しさの効き0.5、薄い帯は難しさの効き0.25〜0.75の範囲（各100回の平均）", y=-0.09)

    # 確かめ：1日に答える人の数と④のずれ（置いた効き目0.05、γ=0）
    pd_rows = []
    for perday in [60, 600]:
        P = dict(BASE, per_day=perday)
        v = np.array([estimates(make(rng, 0.05, P))["m4_day_means"] for _ in range(50)])
        pd_rows.append({"per_day": perday, "answers_per_day": perday * BASE["answer_rate"], "m4_mean": r(v.mean()),
                        "m4_bias": r(v.mean() + 0.05), "m4_p10": r(np.percentile(v, 10)), "m4_p90": r(np.percentile(v, 90))})
    pd.DataFrame(pd_rows).to_csv(RES / "day_size_check.csv", index=False)
    res["day_size_check"] = pd_rows
    print(pd_rows)

    with open(RES / "a1196_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(est.to_string())
    print(bdf.to_string())
    print(res["one_run_b0"])
    print(json.dumps(summ, ensure_ascii=False, indent=0))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
