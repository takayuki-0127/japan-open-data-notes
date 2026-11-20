"""854 過去の実績で見積もりを直すと、外れはどれだけ減るのか？（架空のデータ）

架空のチーム（見積もる人）2,000組。チームごとに「見積もりの癖」（実際の日数÷見積もりの日数の、そのチームの中心）を置く。
1件ごとの実際の日数 = 見積もり × 癖 × 毎回のぶれ（対数正規）。
過去 N 件の「実際÷見積もり」から補正の倍率を作り、新しい1件の見積もりに掛けて、外れの大きさを比べる。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 854
SRC = "架空のチームと見積もり（作成者が乱数で作成、seed 854）"
N_TEAM = 2000
REP = 20          # チームを作り直す回数
BIAS_MED = 1.4    # 癖の中心（実際は見積もりの1.4倍かかる）
BIAS_SD = 0.15    # チームどうしの癖の違い（対数の標準偏差）
NOISE = 0.35      # 1件ごとのぶれ（対数の標準偏差）


def run(rng, n_past, noise=NOISE, bias_sd=BIAS_SD, drift=0.0, bias_med=BIAS_MED, n_team=N_TEAM):
    bias = np.log(bias_med) + rng.normal(0, bias_sd, n_team)
    past = bias[:, None] + rng.normal(0, noise, (n_team, n_past))           # 過去の log(実際/見積もり)
    new_bias = bias + rng.normal(0, drift, n_team)                         # 新しい仕事の癖（drift>0 で過去と違う）
    new = new_bias + rng.normal(0, noise, n_team)                          # 新しい1件の log(実際/見積もり)
    est = np.round(rng.uniform(5, 60, n_team), 1)                          # 見積もりの日数
    common = np.median(past)                                               # 全チーム共通の倍率（全員の過去の中央値）
    plans = {"見積もりそのまま": np.zeros(n_team),
             "全チーム共通の倍率": np.full(n_team, common),
             "自分の過去の平均の倍率": past.mean(1)}
    if n_past >= 5:
        plans["自分の過去の8割の点"] = np.quantile(past, 0.8, axis=1)
    rows = {}
    for k, lp in plans.items():
        ratio = np.exp(new - lp)                                           # 実際 ÷ 計画
        rows[k] = {"mdape": float(np.median(np.abs(ratio - 1))), "within20": float((np.abs(ratio - 1) <= 0.2).mean()),
                   "ontime": float((ratio <= 1).mean())}
    return rows, (bias, past, new, est)


def agg(n_past, **kw):
    acc = {}
    for r in range(REP):
        rows, _ = run(np.random.default_rng(SEED * 1000 + r + n_past * 100 + int(kw.get("drift", 0) * 1000)
                                            + int(kw.get("noise", NOISE) * 10000)), n_past, **kw)
        for k, v in rows.items():
            acc.setdefault(k, []).append(v)
    return {k: {m: round(float(np.mean([x[m] for x in v])), 4) for m in v[0]} for k, v in acc.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分のデータ（過去10件）
    _, (bias, past, new, est) = run(rng, 10)
    pd.DataFrame({"team": np.arange(1, N_TEAM + 1), "bias": np.round(np.exp(bias), 4),
                  **{f"past{i+1}_ratio": np.round(np.exp(past[:, i]), 4) for i in range(10)},
                  "new_estimate_days": est, "new_actual_days": np.round(est * np.exp(new), 2)}).to_csv(
        DATA / "teams_past10.csv", index=False)

    # 2) 過去の件数ごと
    rows = []
    for n in [1, 3, 5, 10, 30]:
        res = agg(n)
        for k, v in res.items():
            rows.append({"n_past": n, "method": k, **v})
    by_n = pd.DataFrame(rows)
    by_n.to_csv(RES / "error_by_n_past.csv", index=False)

    # 理屈の下限：癖が完全に分かっても残る外れ（1件ごとのぶれだけ）
    z = np.random.default_rng(SEED + 1).normal(0, NOISE, 1_000_000)
    floor = {"mdape": round(float(np.median(np.abs(np.exp(z) - 1))), 4),
             "within20": round(float((np.abs(np.exp(z) - 1) <= 0.2).mean()), 4)}

    # 3) 確かめ：ぶれの大きさ・仕事の種類の違い（drift）を変える（過去10件）
    sens = []
    for noise in [0.2, 0.35, 0.5]:
        for drift in [0.0, 0.1, 0.2, 0.3]:
            res = agg(10, noise=noise, drift=drift)
            for k in ["見積もりそのまま", "全チーム共通の倍率", "自分の過去の平均の倍率"]:
                sens.append({"noise": noise, "drift": drift, "method": k, **res[k]})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    # 癖の違いがないとき（チームどうし同じ癖）
    same = agg(10, bias_sd=0.0)
    # 癖がないとき（見積もりが平均では正しい）
    nobias = agg(10, bias_med=1.0)

    piv = by_n.pivot(index="n_past", columns="method", values="mdape")
    out = {"setting": {"n_team": N_TEAM, "rep": REP, "bias_median": BIAS_MED, "bias_sd_log": BIAS_SD, "noise_sd_log": NOISE},
           "by_n_past": rows, "floor_noise_only": floor, "sensitivity": sens.to_dict("records"),
           "check_same_bias_all_teams_n10": same, "check_no_bias_n10": nobias,
           "one_draw": {"bias_median": round(float(np.exp(np.median(bias))), 3),
                        "new_ratio_median": round(float(np.exp(np.median(new))), 3),
                        "raw_ratio_p10_p90": [round(float(np.quantile(np.exp(new), q)), 3) for q in (.1, .9)],
                        "corrected_ratio_p10_p90": [round(float(np.quantile(np.exp(new - past.mean(1)), q)), 3) for q in (.1, .9)],
                        "corrected_ratio_median": round(float(np.median(np.exp(new - past.mean(1)))), 3)}}
    json.dump(out, open(RES / "a854_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：過去の件数と外れ（中央値）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.array([1, 3, 5, 10, 30])
    for k, col, ls in [("見積もりそのまま", GRAY, "-"), ("全チーム共通の倍率", GREEN, "-"), ("自分の過去の平均の倍率", BLUE, "-")]:
        v = piv[k].values * 100
        ax.plot(xs, v, "o-", color=col, label=k, ls=ls)
        off = {"全チーム共通の倍率": 1.5, "自分の過去の平均の倍率": -1.5}.get(k, 0)
        ax.text(xs[-1] * 1.1, v[-1] + off, f"{v[-1]:.0f}%", color=col, va="center", fontsize=9)
    ax.axhline(floor["mdape"] * 100, color=ORANGE, ls="--", lw=1)
    ax.text(1, floor["mdape"] * 100 - 2.5, f"1件ごとのぶれだけで残る外れ（{floor['mdape']*100:.0f}%）", color=ORANGE, fontsize=9)
    ax.set_xscale("log"); ax.set_xticks(xs, [str(x) for x in xs]); ax.set_xlim(0.8, 45)
    ax.set_xlabel("補正に使った過去の実績の件数"); ax.set_ylabel("外れの大きさ（実際÷計画−1 の絶対値の中央値、%）")
    ax.set_ylim(0, max(np.nanmax(piv.values) * 100 * 1.15, 50)); ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("過去の実績で直すと外れは減るが、ぶれの分は残る")
    save(fig, "a854_error_by_n.png", SRC)

    # 図2：1回分の、見積もりそのままと補正後の「実際÷計画」
    raw = np.exp(new); cor = np.exp(new - past.mean(1))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bins = np.linspace(0.2, 4, 77)
    ax.hist(raw, bins=bins, color=GRAY, alpha=.6, density=True, label="見積もりそのまま")
    ax.hist(cor, bins=bins, color=BLUE, alpha=.6, density=True, label="自分の過去10件の平均の倍率で補正")
    ax.axvline(1, color=INK, lw=1, ls="--"); ax.text(1.03, ax.get_ylim()[1] * .9, "計画どおり", fontsize=9)
    ax.set_xlabel("実際の日数 ÷ 計画の日数（1より右は遅れ）"); ax.set_yticks([]); ax.legend(frameon=False, fontsize=9)
    ax.set_title("補正すると中心は1に寄るが、上下の外れは残る（チーム2,000組）")
    save(fig, "a854_ratio_hist.png", SRC)

    # 図3：仕事の種類が過去と違う（drift）と、補正の効き目
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    s = sens[sens.noise == NOISE]
    for k, col in [("見積もりそのまま", GRAY), ("全チーム共通の倍率", GREEN), ("自分の過去の平均の倍率", BLUE)]:
        t = s[s.method == k]
        ax.plot(t.drift, t.mdape * 100, "o-", color=col, label=k)
    ax.set_xticks([0, .1, .2, .3]); ax.set_xlabel("新しい仕事の癖が、過去の仕事の癖とずれる大きさ（対数の標準偏差）")
    ax.set_ylabel("外れの大きさ（中央値、%）"); ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9)
    ax.set_title("過去と違う種類の仕事では、直したあとの外れが大きくなる")
    save(fig, "a854_drift.png", SRC)
    print(by_n.to_string()); print(floor); print(sens.to_string()); print("same", same); print("nobias", nobias)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
