"""1214 見つけやすい大きな生き物と見つけにくい小さな生き物では、数の割合はどれだけゆがむのか？（架空のデータ）

作成者が置いた架空の草地「C草地」（100区画）に、大きさの違う6つの架空の種（種A〜種F）がいる。
本当の数と、歩いて数えたときに1匹が見つかる確率を種ごとに置き（大きい種ほど見つかりやすい）、
見つかった数で出した種の割合が、本当の割合からどれだけずれるかを数える。
日ごとの見えやすさ（草の高さなど）の上下は、どの種にも同じように効くと置く。
あわせて、見本の区画で全部を数えて種ごとの見つかる割合を見積もり、割り戻す読み方を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1214
SRC = "架空の草地（作成者が乱数で作成、seed 1214）"
SP = ["種A", "種B", "種C", "種D", "種E", "種F"]
SIZE = ["大", "大", "中", "中", "小", "小"]
N_TRUE = np.array([60, 120, 200, 300, 500, 800])
P_FIND = np.array([0.85, 0.80, 0.50, 0.45, 0.12, 0.10])
DAY_SD = 0.5            # 日ごとの見えやすさの上下（対数オッズでの標準偏差、どの種にも同じ）
N_PLOT = 100
CLUMP_SD = 0.8          # 区画ごとの散らばりのむら（対数での標準偏差）
REPS = 2000


def r(x, d=3):
    return round(float(x), d)


def q(a, p):
    return float(np.quantile(a, p))


def logit(p):
    return np.log(p / (1 - p))


def expit(z):
    return 1 / (1 + np.exp(-z))


def place(rng, n_true):
    """種ごとに、本当の数を100区画に散らす（区画×種）"""
    out = np.zeros((N_PLOT, n_true.size), dtype=int)
    for j, n in enumerate(n_true):
        w = np.exp(rng.normal(0, CLUMP_SD, N_PLOT))
        out[:, j] = rng.multinomial(n, w / w.sum())
    return out


def one_day(rng, n_true, p_find, day_sd, k_sample=(3, 10, 30)):
    plots = place(rng, n_true)
    p_day = expit(logit(p_find) + rng.normal(0, day_sd)) if day_sd > 0 else p_find
    seen = rng.binomial(plots, p_day[None, :])               # 歩いて数えて見つかった数（区画×種）
    obs = seen.sum(axis=0)
    res = {"obs": obs, "true": plots.sum(axis=0), "p_day": p_day, "corr": {}}
    order = rng.permutation(N_PLOT)
    for k in k_sample:
        idx = order[:k]
        full = plots[idx].sum(axis=0)                          # 見本の区画で全部を数えた数
        found = seen[idx].sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            p_hat = np.where(full > 0, found / np.maximum(full, 1), np.nan)
            est = np.where(p_hat > 0, obs / p_hat, np.nan)
        res["corr"][k] = est
    return res


def share(x):
    return x / x.sum()


def run(rng, n_true, p_find, day_sd, reps, ks=(3, 10, 30)):
    ts = share(n_true.astype(float))
    obs_sh = np.zeros((reps, n_true.size))
    corr_sh = {k: np.full((reps, n_true.size), np.nan) for k in ks}
    top_obs = np.zeros(reps, dtype=bool)
    top_corr = {k: np.zeros(reps) for k in ks}
    fail = {k: 0 for k in ks}
    for i in range(reps):
        d = one_day(rng, n_true, p_find, day_sd, ks)
        obs_sh[i] = share(d["obs"].astype(float))
        top_obs[i] = np.argmax(d["obs"]) == np.argmax(n_true)
        for k in ks:
            e = d["corr"][k]
            if np.all(np.isfinite(e)):
                corr_sh[k][i] = share(e)
                top_corr[k][i] = float(np.argmax(e) == np.argmax(n_true))
            else:
                fail[k] += 1
                top_corr[k][i] = np.nan
    return dict(true_share=ts, obs_sh=obs_sh, corr_sh=corr_sh, top_obs=top_obs, top_corr=top_corr, fail=fail)


def formula_share(n_true, p_find):
    """見つかった数の割合の見込み（本当の数×見つかる確率で割り振る、式）"""
    return share(n_true * p_find)


def main():
    rng = np.random.default_rng(SEED)
    out = {"setup": {"species": SP, "size": SIZE, "n_true": N_TRUE.tolist(), "p_find": P_FIND.tolist(),
                     "day_sd_logodds": DAY_SD, "plots": N_PLOT, "reps": REPS}}

    base = run(rng, N_TRUE, P_FIND, DAY_SD, REPS)
    ts = base["true_share"]
    fs = formula_share(N_TRUE, P_FIND)
    rows = []
    for j, sp in enumerate(SP):
        x = base["obs_sh"][:, j] * 100
        rows.append({"種": sp, "大きさ": SIZE[j], "本当の数": int(N_TRUE[j]), "見つかる確率": P_FIND[j],
                     "本当の割合%": r(ts[j] * 100, 2), "見つかった数の割合%_平均": r(x.mean(), 2),
                     "10%点": r(q(x, 0.1), 2), "90%点": r(q(x, 0.9), 2),
                     "式の割合%": r(fs[j] * 100, 2), "見かけ÷本当": r(x.mean() / 100 / ts[j], 3)})
        for k in (3, 10, 30):
            y = base["corr_sh"][k][:, j] * 100
            rows[-1][f"見本{k}区画で割り戻し%_平均"] = r(np.nanmean(y), 2)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "base_shares.csv", index=False)
    small = np.array([s == "小" for s in SIZE]); large = np.array([s == "大" for s in SIZE])
    obs_small = base["obs_sh"][:, small].sum(axis=1) * 100
    obs_large = base["obs_sh"][:, large].sum(axis=1) * 100
    out["base"] = {
        "small_share_true_pct": r(ts[small].sum() * 100, 2), "small_share_obs_pct": r(obs_small.mean(), 2),
        "small_share_obs_10_90": [r(q(obs_small, 0.1), 2), r(q(obs_small, 0.9), 2)],
        "small_share_formula_pct": r(fs[small].sum() * 100, 2),
        "large_share_true_pct": r(ts[large].sum() * 100, 2), "large_share_obs_pct": r(obs_large.mean(), 2),
        "large_share_formula_pct": r(fs[large].sum() * 100, 2),
        "top_true": SP[int(np.argmax(N_TRUE))], "top_formula": SP[int(np.argmax(N_TRUE * P_FIND))],
        "top_correct_obs_pct": r(base["top_obs"].mean() * 100, 2),
        "obs_rank_formula": [SP[i] for i in np.argsort(-(N_TRUE * P_FIND))],
        "true_rank": [SP[i] for i in np.argsort(-N_TRUE)],
        "mean_abs_share_err_obs_pt": r(np.abs(base["obs_sh"] - ts[None, :]).sum(axis=1).mean() / 2 * 100, 2),
    }
    corr = []
    for k in (3, 10, 30):
        c = base["corr_sh"][k]
        ok = np.all(np.isfinite(c), axis=1)
        err = np.abs(c[ok] - ts[None, :]).sum(axis=1) / 2 * 100
        sm = c[ok][:, small].sum(axis=1) * 100
        corr.append({"見本の区画": k, "割り戻せなかった日%": r(base["fail"][k] / REPS * 100, 2),
                     "割合のずれ_ポイント_平均": r(err.mean(), 2), "ずれ_90%点": r(q(err, 0.9), 2),
                     "小さい種の割合%_平均": r(sm.mean(), 2), "小さい種_10%点": r(q(sm, 0.1), 2), "小さい種_90%点": r(q(sm, 0.9), 2),
                     "いちばん多い種が当たった%": r(np.nanmean(base["top_corr"][k]) * 100, 2)})
    corr.insert(0, {"見本の区画": 0, "割り戻せなかった日%": 0.0,
                    "割合のずれ_ポイント_平均": out["base"]["mean_abs_share_err_obs_pt"],
                    "ずれ_90%点": r(q(np.abs(base["obs_sh"] - ts[None, :]).sum(axis=1) / 2 * 100, 0.9), 2),
                    "小さい種の割合%_平均": r(obs_small.mean(), 2), "小さい種_10%点": r(q(obs_small, 0.1), 2),
                    "小さい種_90%点": r(q(obs_small, 0.9), 2),
                    "いちばん多い種が当たった%": out["base"]["top_correct_obs_pct"]})
    cdf = pd.DataFrame(corr)
    cdf.to_csv(RES / "correction.csv", index=False)
    out["correction"] = corr

    # 1日分のデータ
    d0 = one_day(np.random.default_rng(SEED + 7), N_TRUE, P_FIND, DAY_SD)
    pd.DataFrame({"species": SP, "size": SIZE, "true": d0["true"], "p_find_day": np.round(d0["p_day"], 4),
                  "seen": d0["obs"]}).to_csv(DATA / "one_day.csv", index=False)

    # ---- 確かめ：小さい種の見つかる確率×本当の数の形×日ごとの上下 の27通り ----
    patterns = {"小さい種が多い": N_TRUE, "どの種も同じ数": np.full(6, 330),
                "小さい種が少ない": N_TRUE[::-1].copy()}
    grid = []
    for p_small in [0.05, 0.12, 0.3]:
        pf = P_FIND.copy(); pf[4] = p_small; pf[5] = p_small * 10 / 12
        for pname, nt in patterns.items():
            for dsd in [0.0, 0.5, 1.0]:
                rr = run(rng, nt, pf, dsd, 300, ks=(10,))
                tsg = rr["true_share"]
                sm_o = rr["obs_sh"][:, small].sum(axis=1).mean() * 100
                c = rr["corr_sh"][10]; ok = np.all(np.isfinite(c), axis=1)
                grid.append({"小さい種の見つかる確率": f"{p_small}・{r(p_small * 10 / 12, 3)}", "本当の数の形": pname,
                             "日ごとの上下": dsd,
                             "小さい種の割合_本当%": r(tsg[small].sum() * 100, 2),
                             "小さい種の割合_見かけ%": r(sm_o, 2),
                             "小さい種_式%": r(formula_share(nt, pf)[small].sum() * 100, 2),
                             "見かけ÷本当": r(sm_o / (tsg[small].sum() * 100), 3),
                             "いちばん多い種が当たった%_見かけ": r(rr["top_obs"].mean() * 100, 2) if pname != "どの種も同じ数" else None,
                             "見本10区画で割り戻し_小さい種%": r(c[ok][:, small].sum(axis=1).mean() * 100, 2),
                             "割り戻せなかった日%": r(rr["fail"][10] / 300 * 100, 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    out["grid"] = {"n": len(g), "ratio_min": r(g["見かけ÷本当"].min()), "ratio_max": r(g["見かけ÷本当"].max()),
                   "max_gap_obs_vs_formula_pt": r((g["小さい種の割合_見かけ%"] - g["小さい種_式%"]).abs().max(), 2),
                   "by_p_small_ratio": {k: [r(v.min()), r(v.max())] for k, v in g.groupby("小さい種の見つかる確率", sort=False)["見かけ÷本当"]},
                   "corr10_gap_pt_max": r((g["見本10区画で割り戻し_小さい種%"] - g["小さい種の割合_本当%"]).abs().max(), 2),
                   "fail10_max_pct": r(g["割り戻せなかった日%"].max(), 2),
                   "top_correct_small_many_range": [r(g[g["本当の数の形"] == "小さい種が多い"]["いちばん多い種が当たった%_見かけ"].min(), 2),
                                                    r(g[g["本当の数の形"] == "小さい種が多い"]["いちばん多い種が当たった%_見かけ"].max(), 2)]}

    # ---- 図1：本当の割合と見つかった数の割合 ----
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    xs = np.arange(6); w = 0.38
    ax.bar(xs - w / 2, df["本当の割合%"], w, color=GRAY, label="本当の割合")
    ax.bar(xs + w / 2, df["見つかった数の割合%_平均"], w, color=ORANGE, label="見つかった数の割合（2,000日の平均）")
    for x0, a, b in zip(xs, df["本当の割合%"], df["見つかった数の割合%_平均"]):
        ax.text(x0 - w / 2, a + 0.6, f"{a:g}", ha="center", fontsize=8.5)
        ax.text(x0 + w / 2, b + 0.6, f"{b:g}", ha="center", fontsize=8.5, color=ORANGE)
    ax.set_xticks(xs); ax.set_xticklabels([f"{s}\n（{z}・{p:.0%}）" for s, z, p in zip(SP, SIZE, P_FIND)])
    ax.set_ylim(0, max(df["本当の割合%"].max(), df["見つかった数の割合%_平均"].max()) * 1.15)
    ax.set_ylabel("割合（%）")
    ax.set_title("種の割合：本当と、見つかった数（かっこは大きさ・1匹が見つかる確率）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1214_shares.png", SRC)

    # ---- 図2：見本の区画の数と割合のずれ ----
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    labs = ["割り戻さない"] + [f"見本{k}区画" for k in (3, 10, 30)]
    vals = cdf["割合のずれ_ポイント_平均"].tolist()
    ax.bar(range(4), vals, color=[ORANGE, LIGHT, BLUE, INK])
    for i, v in enumerate(vals):
        ax.text(i, v + 0.5, f"{v:g}", ha="center", fontsize=9.5)
    ax.set_xticks(range(4)); ax.set_xticklabels(labs)
    ax.set_ylim(0, max(vals) * 1.18)
    ax.set_ylabel("割合のずれ（ポイント、日ごとの平均）")
    ax.set_title("6種の割合の本当からのずれ（ずれの合計÷2、割り戻せた日だけ）", fontsize=11.5)
    save(fig, "a1214_correction.png", SRC)

    # ---- 図3：27通りの小さい種の割合 ----
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    mk = {"小さい種が多い": "o", "どの種も同じ数": "s", "小さい種が少ない": "^"}
    keys = list(dict.fromkeys(g["小さい種の見つかる確率"]))
    cl = dict(zip(keys, [LIGHT, BLUE, INK]))
    for _, rw in g.iterrows():
        ax.scatter(rw["小さい種の割合_本当%"], rw["小さい種の割合_見かけ%"], marker=mk[rw["本当の数の形"]],
                   color=cl[rw["小さい種の見つかる確率"]], s=36, zorder=3)
    ax.plot([0, 100], [0, 100], color=GRAY, ls="--", lw=1)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xlabel("小さい2種の本当の割合（%）"); ax.set_ylabel("見つかった数での割合（%、300日の平均）")
    for k, m_ in mk.items():
        ax.scatter([], [], marker=m_, color=GRAY, label=k)
    for k, c_ in cl.items():
        ax.scatter([], [], marker="o", color=c_, label=f"小さい種の見つかる確率 {k}")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("27通りすべてで、小さい2種の割合は点線（本当）より下に出た\n（日ごとの上下3通りの点はほぼ重なる）", fontsize=11.5)
    save(fig, "a1214_grid.png", SRC)

    with open(RES / "a1214_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(df.to_string()); print(cdf.to_string()); print(g.to_string())
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
