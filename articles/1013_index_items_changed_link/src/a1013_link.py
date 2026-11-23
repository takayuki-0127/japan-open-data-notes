"""1013 前年の項目と今年の項目が違うとき、指数はつなげるのか？（架空のデータ）

架空のチェーンの60店の「店の総合指数」（5項目の平均、各100点満点）。1年目は項目A〜E、
2年目は両方（E と新しい項目F）を測り、3年目は E を F に入れかえた A〜D・F。
本当の変化は「3年目も1年目と同じ5項目（A〜E）で測ったら」の、見方の揺れを除いた変化。
1年目→3年目の変化を、そのまま・共通の4項目だけ・重なりの年でつなぐ（全体の差・店ごとの差）の4通りで読む。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1013
SRC = "架空のチェーンの店の総合指数（作成者が乱数で作成、seed 1013）"
N = 60
ITEMS = ["A 接客", "B 店内の清潔さ", "C 品ぞろえ", "D 会計の速さ", "E 電話の応対", "F ネット注文の使いやすさ"]
MU = np.array([70, 70, 70, 70, 72, 64], float)  # 項目の水準。F は E より8点低い（基本）
Q_SD, DELTA, DELTA_SD = 6.0, 2.0, 2.0           # 店の共通の良さ、2年での本当の変化（平均・店ごとの散らばり）
U_SD, E_SD = 4.0, 3.0                             # 店×項目のずっと続く違い、年ごとの見方の揺れ
G_E = 0.0                                         # 項目Eだけの2年での変化（基本0）
REPS, GRID_REPS = 1000, 200
METHODS = {"naive": "そのまま比べる", "common": "共通の4項目だけで比べる",
           "link_all": "重なりの年の全体の差でつなぐ", "link_store": "重なりの年の店ごとの差でつなぐ"}


def make_chain(rng, gap=-8.0, g_e=G_E, u_sd=U_SD, e_sd=E_SD, n=N):
    mu = MU.copy(); mu[5] = mu[4] + gap
    q1 = rng.normal(0, Q_SD, n)
    d = rng.normal(DELTA, DELTA_SD, n)
    u = rng.normal(0, u_sd, (n, 6))
    true = {}
    for t, frac in [(1, 0.0), (2, 0.5), (3, 1.0)]:
        x = mu + (q1 + frac * d)[:, None] + u
        x[:, 4] += frac * g_e
        true[t] = x
    obs = {t: true[t] + rng.normal(0, e_sd, (n, 6)) for t in (1, 2, 3)}
    truth = true[3][:, :5].mean(1) - true[1][:, :5].mean(1)
    return obs, truth


def readings(obs):
    old = lambda x: x[:, :5].mean(1)
    new = lambda x: x[:, [0, 1, 2, 3, 5]].mean(1)
    naive = new(obs[3]) - old(obs[1])
    common = obs[3][:, :4].mean(1) - obs[1][:, :4].mean(1)
    off = old(obs[2]) - new(obs[2])
    return {"naive": naive, "common": common, "link_all": naive + off.mean(), "link_store": naive + off}


def spearman(a, b):
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def one_rep(rng, **kw):
    obs, truth = make_chain(rng, **kw)
    r = readings(obs)
    out = {"truth_chain": float(truth.mean()), "truth_down_share": float((truth < 0).mean())}
    top_t = set(np.argsort(-truth, kind="stable")[:10])
    for m in METHODS:
        v = r[m]
        out[f"{m}_chain"] = float(v.mean())
        out[f"{m}_chain_err"] = float(v.mean() - truth.mean())
        out[f"{m}_down_share"] = float((v < 0).mean())
        out[f"{m}_store_rmse"] = float(np.sqrt(((v - truth) ** 2).mean()))
        out[f"{m}_spearman"] = spearman(v, truth)
        out[f"{m}_top10"] = len(top_t & set(np.argsort(-v, kind="stable")[:10]))
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分（data/stores.csv）
    obs, truth = make_chain(rng)
    r = readings(obs)
    d = pd.DataFrame({"store": [f"T{i + 1:02d}" for i in range(N)]})
    keys = list("ABCDEF")
    for t, cols in [(1, [0, 1, 2, 3, 4]), (2, [0, 1, 2, 3, 4, 5]), (3, [0, 1, 2, 3, 5])]:
        for c in cols:
            d[f"y{t}_{keys[c]}"] = obs[t][:, c].round(2)
    d["true_change"] = truth.round(3)
    for m in METHODS:
        d[f"read_{m}"] = r[m].round(3)
    d.to_csv(DATA / "stores.csv", index=False)
    one = {"truth_chain": round(float(truth.mean()), 3),
           "y2_E_mean": round(float(obs[2][:, 4].mean()), 3), "y2_F_mean": round(float(obs[2][:, 5].mean()), 3),
           "truth_down_stores": int((truth < 0).sum())}
    for m in METHODS:
        one[m] = {"chain": round(float(r[m].mean()), 3), "down_stores": int((r[m] < 0).sum()),
                  "store_rmse": round(float(np.sqrt(((r[m] - truth) ** 2).mean())), 3)}

    # 基本の置き方（1,000回）
    reps = pd.DataFrame([one_rep(np.random.default_rng(SEED * 1000 + i)) for i in range(REPS)])
    reps.round(5).to_csv(RES / "reps_base.csv", index=False)
    base = []
    for m in METHODS:
        base.append({"key": m, "method": METHODS[m], "chain_mean": round(reps[f"{m}_chain"].mean(), 3),
                     "chain_p5": round(reps[f"{m}_chain"].quantile(.05), 3), "chain_p95": round(reps[f"{m}_chain"].quantile(.95), 3),
                     "chain_err_mean": round(reps[f"{m}_chain_err"].mean(), 3),
                     "chain_looks_down_share": round(float((reps[f"{m}_chain"] < 0).mean()), 4),
                     "stores_down_share": round(reps[f"{m}_down_share"].mean(), 4),
                     "store_rmse": round(reps[f"{m}_store_rmse"].mean(), 3),
                     "spearman": round(reps[f"{m}_spearman"].mean(), 4), "top10": round(reps[f"{m}_top10"].mean(), 3)})
    base = pd.DataFrame(base)
    base.to_csv(RES / "methods_base.csv", index=False)
    truth_sum = {"chain_mean": round(reps.truth_chain.mean(), 3), "chain_p5": round(reps.truth_chain.quantile(.05), 3),
                 "chain_p95": round(reps.truth_chain.quantile(.95), 3), "stores_down_share": round(reps.truth_down_share.mean(), 4)}
    formula = {"naive_bias_gap_over_5": round((MU[5] - MU[4]) / 5, 3)}

    # 確かめ：F と E の水準の差×E だけの変化×店×項目の違い×見方の揺れ（各200回）
    grid = []
    gi = 0
    for gap in [0.0, -4.0, -8.0, -12.0]:
        for g_e in [0.0, 2.0, 4.0]:
            for u_sd in [2.0, 4.0, 8.0]:
                for e_sd in [1.5, 3.0, 6.0]:
                    rr = pd.DataFrame([one_rep(np.random.default_rng(SEED * 100000 + gi * 1000 + i), gap=gap, g_e=g_e,
                                               u_sd=u_sd, e_sd=e_sd) for i in range(GRID_REPS)])
                    gi += 1
                    row = {"gap_F_minus_E": gap, "E_only_change": g_e, "u_sd": u_sd, "noise_sd": e_sd,
                           "truth_chain": round(rr.truth_chain.mean(), 3),
                           "formula_naive_err": round((gap - g_e) / 5, 3), "formula_common_err": round(-g_e / 5, 3),
                           "formula_link_err": round(-g_e / 10, 3)}
                    for m in METHODS:
                        row[f"{m}_chain_err"] = round(rr[f"{m}_chain_err"].mean(), 3)
                        row[f"{m}_store_rmse"] = round(rr[f"{m}_store_rmse"].mean(), 3)
                        row[f"{m}_spearman"] = round(rr[f"{m}_spearman"].mean(), 4)
                        row[f"{m}_down_share"] = round(rr[f"{m}_down_share"].mean(), 4)
                    row["truth_down_share"] = round(rr.truth_down_share.mean(), 4)
                    grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    gs = {}
    for m in METHODS:
        gs[f"{m}_chain_err_range"] = [float(grid[f"{m}_chain_err"].min()), float(grid[f"{m}_chain_err"].max())]
        gs[f"{m}_store_rmse_range"] = [float(grid[f"{m}_store_rmse"].min()), float(grid[f"{m}_store_rmse"].max())]
    gs["max_abs_gap_naive_vs_formula"] = round(float((grid.naive_chain_err - grid.formula_naive_err).abs().max()), 3)
    gs["max_abs_gap_common_vs_formula"] = round(float((grid.common_chain_err - grid.formula_common_err).abs().max()), 3)
    gs["max_abs_gap_link_all_vs_formula"] = round(float((grid.link_all_chain_err - grid.formula_link_err).abs().max()), 3)
    gs["link_store_better_rmse_than_link_all_count"] = int((grid.link_store_store_rmse < grid.link_all_store_rmse).sum())
    for m in METHODS:
        gs[f"{m}_stores_down_share_range"] = [float(grid[f"{m}_down_share"].min()), float(grid[f"{m}_down_share"].max())]
    gs["truth_stores_down_share_range"] = [float(grid.truth_down_share.min()), float(grid.truth_down_share.max())]
    gs["n_grid"] = int(len(grid))
    # 店×項目の違いと見方の揺れの組ごと（水準の差−8、Eだけの変化0）
    sub = grid[(grid.gap_F_minus_E == -8) & (grid.E_only_change == 0)][["u_sd", "noise_sd", "naive_store_rmse", "common_store_rmse",
                                                                      "link_all_store_rmse", "link_store_store_rmse",
                                                                      "naive_spearman", "link_all_spearman", "link_store_spearman", "common_spearman"]]
    gs["by_u_noise_gap8"] = sub.to_dict("records")
    out = {"one_draw": one, "truth_base_1000reps": truth_sum, "methods_base_1000reps": base.to_dict("records"),
           "formula": formula, "grid_summary": gs}
    json.dump(out, open(RES / "a1013_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：チェーン全体の変化（1,000回の平均と5〜95%）
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    labs = ["本当の変化（同じ5項目なら）"] + [METHODS[m] for m in METHODS]
    means = [truth_sum["chain_mean"]] + list(base.chain_mean)
    lo = [truth_sum["chain_p5"]] + list(base.chain_p5)
    hi = [truth_sum["chain_p95"]] + list(base.chain_p95)
    cols = [INK, ORANGE, GRAY, BLUE, GREEN]
    for i in range(len(labs)):
        y = len(labs) - 1 - i
        ax.plot([lo[i], hi[i]], [y, y], color=cols[i], lw=2)
        ax.plot(means[i], y, "o", color=cols[i], ms=7)
        ax.text(hi[i] + 0.15, y, f"{means[i]:+.2f}点", va="center", fontsize=9)
    ax.axvline(0, color=GRAY, lw=1); ax.axvline(truth_sum["chain_mean"], color=INK, lw=0.8, ls=":")
    ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs[::-1])
    ax.set_xlabel("1年目→3年目の指数の変化（60店の平均、点。線は1,000回の5〜95%）")
    ax.set_title("項目EをFに入れかえたまま比べると、上がった指数がほぼ横ばいに見える")
    ax.set_xlim(min(lo) - 0.5, max(hi) + 1.4)
    save(fig, "a1013_chain.png", SRC)

    # 図2：1回分、店ごとの本当の変化と読んだ変化
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharex=True, sharey=True)
    lim = [min(truth.min(), min(r[m].min() for m in METHODS)) - 0.5, max(truth.max(), max(r[m].max() for m in METHODS)) + 0.5]
    for ax, m, col in zip(axes, ["naive", "link_all", "link_store"], [ORANGE, BLUE, GREEN]):
        ax.scatter(truth, r[m], s=14, color=col, alpha=.75, lw=0)
        ax.plot(lim, lim, color=GRAY, lw=1, ls="--")
        ax.axhline(0, color=GRAY, lw=.6); ax.axvline(0, color=GRAY, lw=.6)
        ax.set_title(f"{METHODS[m]}\n（ずれの大きさ {one[m]['store_rmse']:.2f}点）", fontsize=10.5)
        ax.set_xlabel("本当の変化（点）")
    axes[0].set_ylabel("読んだ変化（点）")
    axes[0].set_xlim(lim); axes[0].set_ylim(lim)
    fig.suptitle("店ごとの変化（60店、1回分。点線の上なら本当どおり）", fontsize=12, y=1.03)
    save(fig, "a1013_stores.png", SRC)

    # 図3：水準の差と E だけの変化で、チェーン全体の変化のずれ（店×項目の違い4点・見方の揺れ3点）
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharey=True)
    gaps = [0.0, -4.0, -8.0, -12.0]
    for ax, g_e in zip(axes, [0.0, 2.0, 4.0]):
        g = grid[(grid.E_only_change == g_e) & (grid.u_sd == 4.0) & (grid.noise_sd == 3.0)].set_index("gap_F_minus_E").loc[gaps]
        for m, col, mk, ls in [("naive", ORANGE, "o", "-"), ("common", GRAY, "D", "-"), ("link_all", BLUE, "s", "--")]:
            ax.plot(gaps, g[f"{m}_chain_err"], color=col, marker=mk, ls=ls, label=METHODS[m])
        ax.axhline(0, color=INK, lw=.8)
        ax.set_xticks(gaps); ax.set_xticklabels(["0", "−4", "−8", "−12"])
        ax.set_xlabel("新しい項目Fの水準−項目Eの水準（点）")
        ax.set_title(f"項目Eだけの2年での変化 {g_e:+g}点", fontsize=10.5)
    axes[0].set_ylabel("チェーン全体の変化の本当とのずれ（点）")
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("そのままのずれは（水準の差−Eだけの変化）÷5、共通の4項目は−Eだけの変化÷5、"
                 "つなぐと−Eだけの変化÷10（式どおり、各200回）", fontsize=11, y=1.03)
    save(fig, "a1013_by_gap.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
