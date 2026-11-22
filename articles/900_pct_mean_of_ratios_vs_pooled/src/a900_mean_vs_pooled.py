"""900 割合の平均と、合計で出した割合はどれだけ違うのか？（架空のデータ）

架空の雑貨チェーン200店の1か月。店ごとに来店数と「本当の購入率」を置き、購入数は二項分布で引く。
「店ごとの購入率の平均」と「購入数の合計÷来店数の合計」を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 900
SRC = "架空の雑貨チェーンの来店数と購入数（作成者が乱数で作成、seed 900）"
N_STORE = 200
MED_VISIT = 3000
P_MID = 0.20          # 購入率の真ん中
TAU = 0.5             # 購入率の店どうしの差（ロジットの標準偏差）
RHO = -0.4            # 来店数（対数）と購入率（ロジット）の相関
SIG = 0.8             # 来店数の店どうしの差（対数の標準偏差）


def logit(p):
    return np.log(p / (1 - p))


def make_stores(rng, rho=RHO, sig=SIG, n=N_STORE):
    z = rng.normal(0, 1, n)
    u = rng.normal(0, 1, n)
    w = np.maximum(np.round(np.exp(np.log(MED_VISIT) + sig * z)).astype(int), 50)
    p = 1 / (1 + np.exp(-(logit(P_MID) + TAU * (rho * z + np.sqrt(1 - rho ** 2) * u))))
    b = rng.binomial(w, p)
    return pd.DataFrame({"store_id": np.arange(1, n + 1), "visits": w, "true_rate": p, "buys": b})


def measures(df):
    r = df.buys / df.visits
    pooled = df.buys.sum() / df.visits.sum()
    mean_r = r.mean()
    cov = ((df.visits - df.visits.mean()) * (r - r.mean())).mean()
    return {"pooled": pooled, "mean_of_rates": mean_r, "median_of_rates": r.median(),
            "diff": mean_r - pooled, "formula_diff": -cov / df.visits.mean(),
            "t_company": (df.visits * df.true_rate).sum() / df.visits.sum(), "t_store": df.true_rate.mean()}


def q(x, a):
    return round(float(np.quantile(x, a)), 5)


def main():
    rng = np.random.default_rng(SEED)
    df = make_stores(rng)
    df["rate"] = df.buys / df.visits
    df.to_csv(DATA / "stores.csv", index=False, float_format="%.5f")
    one = {k: round(float(v), 5) for k, v in measures(df).items()}
    big = df.visits >= df.visits.quantile(.8)
    one["share_visits_top20pct_stores"] = round(float(df.visits[big].sum() / df.visits.sum()), 4)
    one["rate_top20pct_stores_pooled"] = round(float(df.buys[big].sum() / df.visits[big].sum()), 5)
    one["rate_rest_pooled"] = round(float(df.buys[~big].sum() / df.visits[~big].sum()), 5)
    one["min_visits"] = int(df.visits.min()); one["max_visits"] = int(df.visits.max())
    one["median_visits"] = float(df.visits.median())

    # 1) 1,000回：2つの数え方と、2つの「本当の値」
    rows = []
    for r in range(1000):
        rows.append(measures(make_stores(np.random.default_rng(SEED * 1000 + r))))
    sim = pd.DataFrame(rows)
    sim.round(6).to_csv(RES / "reps_1000.csv", index_label="rep")
    rep = {"diff_mean": round(float(sim["diff"].mean()), 5), "diff_p10": q(sim["diff"], .1), "diff_p90": q(sim["diff"], .9),
           "share_mean_gt_pooled": round(float((sim["diff"] > 0).mean()), 3),
           "rel_diff_mean": round(float((sim["diff"] / sim["pooled"]).mean()), 4),
           "max_abs_formula_error": float(f"{(sim['diff'] - sim['formula_diff']).abs().max():.2e}"),
           "t_company_mean": round(float(sim.t_company.mean()), 5), "t_store_mean": round(float(sim.t_store.mean()), 5)}
    grid = []
    for est, en in [("pooled", "合計で割る"), ("mean_of_rates", "店ごとの率の平均")]:
        for tgt, tn in [("t_company", "会社全体の本当の購入率"), ("t_store", "店の本当の購入率の平均")]:
            e = sim[est] - sim[tgt]
            grid.append({"estimator": en, "target": tn, "bias_pt": round(float(e.mean() * 100), 3),
                         "sd_pt": round(float(e.std() * 100), 3), "p10_pt": round(float(np.quantile(e, .1) * 100), 3),
                         "p90_pt": round(float(np.quantile(e, .9) * 100), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "estimator_vs_target.csv", index=False)

    # 2) 確かめ：相関 rho × 来店数の差 sig（各300回）
    sens = []
    for i, rho in enumerate([-0.6, -0.3, 0.0, 0.3, 0.6]):
        for j, sig in enumerate([0.3, 0.8, 1.2]):
            d = [measures(make_stores(np.random.default_rng(SEED * 7 + 1000 * i + 100 * j + r), rho, sig))["diff"]
                 for r in range(300)]
            d = np.array(d)
            sens.append({"rho": rho, "sig": sig, "diff_mean_pt": round(float(d.mean() * 100), 3),
                         "diff_p10_pt": round(float(np.quantile(d, .1) * 100), 3),
                         "diff_p90_pt": round(float(np.quantile(d, .9) * 100), 3),
                         "share_mean_gt_pooled": round(float((d > 0).mean()), 3)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    s_range = {"diff_mean_pt_min": float(sens.diff_mean_pt.min()), "diff_mean_pt_max": float(sens.diff_mean_pt.max()),
               "rho0_abs_mean_pt_max": float(sens[sens.rho == 0].diff_mean_pt.abs().max()),
               "rho0_sig12_p10_pt": float(sens[(sens.rho == 0) & (sens.sig == 1.2)].diff_p10_pt.iloc[0]),
               "rho0_sig12_p90_pt": float(sens[(sens.rho == 0) & (sens.sig == 1.2)].diff_p90_pt.iloc[0]),
               "rho_neg06_sig12_pt": float(sens[(sens.rho == -0.6) & (sens.sig == 1.2)].diff_mean_pt.iloc[0]),
               "rho_pos06_sig12_pt": float(sens[(sens.rho == 0.6) & (sens.sig == 1.2)].diff_mean_pt.iloc[0]),
               "base_rho_m04_sig08_pt": round(rep["diff_mean"] * 100, 3)}

    out = {"settings": {"n_store": N_STORE, "median_visits": MED_VISIT, "sig_log_visits": SIG, "rate_mid": P_MID,
                        "tau_logit": TAU, "rho": RHO, "seed": SEED},
           "one_month": one, "reps_1000": rep, "estimator_vs_target": grid.to_dict("records"),
           "sensitivity_range": s_range}
    json.dump(out, open(RES / "a900_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：店の来店数と購入率（1か月分）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.visits, df.rate * 100, s=12, color=BLUE, alpha=.55, lw=0)
    ax.set_xscale("log")
    ax.axhline(one["mean_of_rates"] * 100, color=ORANGE, lw=1.4, ls="--")
    ax.axhline(one["pooled"] * 100, color=INK, lw=1.4)
    x0 = df.visits.min() * 0.9
    ax.text(x0, one["mean_of_rates"] * 100 + 0.8, f"店ごとの率の平均 {one['mean_of_rates']*100:.1f}%", color=ORANGE, fontsize=9)
    ax.text(x0, one["pooled"] * 100 - 2.4, f"合計÷合計 {one['pooled']*100:.1f}%", color=INK, fontsize=9)
    ax.set_xlabel("1か月の来店数（対数の目盛り）"); ax.set_ylabel("購入率（%）")
    ax.set_title("来店の多い店ほど購入率が低いと置くと、率の平均は合計の率より高く出る（200店）")
    save(fig, "a900_scatter.png", SRC)

    # 図2：2つの数え方 × 2つの本当の値（1,000回）
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    lab = [f"{a}\n→ {b}" for a, b in zip(grid.estimator, grid.target)]
    yy = np.arange(len(grid))[::-1]
    for y, (_, g) in zip(yy, grid.iterrows()):
        c = BLUE if abs(g.bias_pt) < 0.3 else ORANGE
        ax.plot([g.p10_pt, g.p90_pt], [y, y], color=c, lw=3, alpha=.5)
        ax.plot(g.bias_pt, y, "o", color=c)
        ax.text(g.p90_pt + 0.08, y, f"平均のずれ {g.bias_pt:+.2f}ポイント", va="center", fontsize=9)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=9)
    ax.set_xlabel("数えた値 − 本当の値（ポイント。点は平均、線は10〜90%の範囲、1,000回）")
    ax.set_xlim(min(grid.p10_pt) - 0.3, max(grid.p90_pt) + 1.6)
    ax.set_title("どちらの数え方も、自分の問いには当たり、相手の問いには外れる")
    save(fig, "a900_target.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for sig, c in zip([0.3, 0.8, 1.2], [LIGHT, BLUE, INK]):
        g = sens[sens.sig == sig]
        ax.plot(g.rho, g.diff_mean_pt, "o-", color=c, label=f"来店数の店どうしの差 {sig}（対数の標準偏差）")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xlabel("来店数と購入率の相関（作成者が置いた値）"); ax.set_ylabel("率の平均 − 合計の率（ポイント）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("ずれの向きは相関の向きで、大きさは店の大きさの差で決まる（各300回の平均）")
    save(fig, "a900_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
