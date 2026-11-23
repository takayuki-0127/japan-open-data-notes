"""1072 調整の前後でキャラクターの勝率を比べると、使う人の入れかわりが何をまぜるのか？（架空のデータ）

架空の対戦ゲームで、キャラクターXを強くする調整を作成者が置く（同じ人が使えば勝つ確率が上がる）。
調整の前はうまい人の多い「使い続けてきた人」が使い、調整の後は、その一部が残り、うまさの低い「新しく使い始めた人」が加わる。
  ① 前後の勝率をそのまま比べる
  ② 前後の両方で使った同じ人だけで比べる
  ③ 調整の前の点数（うまさの目安、誤差あり）の帯ごとに比べて、後の試合数で重みをつける
の3つを、作成者が置いた本当の上がり幅（後に使った人の平均、同じ人での差）と比べる。
相手は全体からでたらめに当たると置く（点数の近い人どうしを当てる仕組みは入れない）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from numpy.polynomial.hermite_e import hermegauss
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1072
SRC = "架空の対戦ゲームのキャラクターXの調整（作成者が乱数で作成、seed 1072）"
BETA = 0.6        # うまさ1標準偏差あたりの勝ちやすさ（ロジット）
GAMES = 40        # 1人あたりの試合数（前・後それぞれ）
N_REP = 500
BASE = {"mains": 1500, "main_skill": 0.5, "stay": 0.8, "newcomers": 2500, "new_skill": -0.5, "delta": 0.25,
        "rating_noise": 0.5, "stay_by_wins": 0.0}
NODES, WTS = hermegauss(60); WTS = WTS / WTS.sum()
CUTZ = np.array([-0.841621, -0.253347, 0.253347, 0.841621])   # 標準正規分布の20・40・60・80%点（全体の点数を5等分する区切り）


def pwin(theta, delta):
    """うまさ theta の人が、全体からでたらめに選んだ相手（うまさ N(0,1)）に勝つ確率（式、数値積分）"""
    z = BETA * (np.asarray(theta)[..., None] - NODES[None, :]) + delta
    return (WTS / (1 + np.exp(-z))).sum(-1)


def one_rep(rng, c, keep=False):
    nm, nn = c["mains"], c["newcomers"]
    th_m = rng.normal(c["main_skill"], 1, nm)
    th_n = rng.normal(c["new_skill"], 1, nn)
    p0_m = pwin(th_m, 0.0)
    w_before = rng.binomial(GAMES, p0_m)
    if c["stay_by_wins"] > 0:     # 前に勝った人ほど残る（確率の平均は stay のまま）
        z = c["stay_by_wins"] * (w_before / GAMES - 0.5) * 10
        base = np.log(c["stay"] / (1 - c["stay"]))
        stay = rng.random(nm) < 1 / (1 + np.exp(-(base + z - z.mean())))
    else:
        stay = rng.random(nm) < c["stay"]
    th_after = np.concatenate([th_m[stay], th_n])
    p1 = pwin(th_after, c["delta"]); p0_after = pwin(th_after, 0.0)
    w_after = rng.binomial(GAMES, p1)
    rate_b = w_before.sum() / (nm * GAMES)
    rate_a = w_after.sum() / (len(th_after) * GAMES)
    ns = int(stay.sum())
    # ② 同じ人だけ
    stay_b = w_before[stay].sum() / (ns * GAMES); stay_a = w_after[:ns].sum() / (ns * GAMES)
    # ③ 調整の前の点数の帯（全体の5等分の区切り）
    r_m = th_m + rng.normal(0, c["rating_noise"], nm)
    r_after = np.concatenate([r_m[stay], th_n + rng.normal(0, c["rating_noise"], nn)])
    cuts = CUTZ * np.sqrt(1 + c["rating_noise"] ** 2)
    bb = np.digitize(r_m, cuts); ba = np.digitize(r_after, cuts)
    diff, wsum = 0.0, 0.0
    for k in range(5):
        mb, ma = bb == k, ba == k
        if mb.sum() == 0 or ma.sum() == 0:
            continue
        d = w_after[ma].sum() / (ma.sum() * GAMES) - w_before[mb].sum() / (mb.sum() * GAMES)
        diff += d * ma.sum(); wsum += ma.sum()
    band = diff / wsum if wsum else np.nan
    out = {"naive": (rate_a - rate_b) * 100, "stayers": (stay_a - stay_b) * 100, "band": band * 100,
           "true_after_users": float((p1 - p0_after).mean()) * 100, "true_stayers": float((p1[:ns] - p0_after[:ns]).mean()) * 100,
           "mix_term": float(p0_after.mean() - p0_m.mean()) * 100,
           "before_rate": rate_b * 100, "after_rate": rate_a * 100, "stayers_n": ns,
           "newcomer_share_after": nn / len(th_after) * 100,
           "skill_before_mean": float(th_m.mean()), "skill_after_mean": float(th_after.mean())}
    if keep:
        df = pd.DataFrame({"player": np.arange(1, nm + nn + 1),
                           "group": ["使い続けてきた人"] * nm + ["新しく使い始めた人"] * nn,
                           "rating_before": np.round(np.concatenate([r_m, r_after[ns:]]), 3),
                           "used_before": [1] * nm + [0] * nn,
                           "used_after": np.concatenate([stay.astype(int), np.ones(nn, int)]),
                           "games_before": [GAMES] * nm + [0] * nn,
                           "wins_before": np.concatenate([w_before, np.zeros(nn, int)]),
                           "games_after": np.concatenate([np.where(stay, GAMES, 0), np.full(nn, GAMES)]),
                           "wins_after": np.concatenate([np.where(stay, 0, 0), np.zeros(nn, int)])})
        wa = np.zeros(nm + nn, int); idx_m = np.where(stay)[0]
        wa[idx_m] = w_after[:ns]; wa[nm:] = w_after[ns:]
        df["wins_after"] = wa
        return out, df
    return out


def run(seed, c, n_rep):
    rows = [one_rep(np.random.default_rng(seed + i), c) for i in range(n_rep)]
    return pd.DataFrame(rows)


def r2(x):
    return round(float(x), 2)


def main():
    t0 = time.time()
    c = BASE
    res = {"setting": {**c, "beta": BETA, "games_per_player_per_period": GAMES, "reps": N_REP}}
    # 式の値（人数を無限にしたときの期待値）
    th = NODES
    def mean_p(mu, d):
        return float((WTS * pwin(mu + th, d)).sum())
    sh_new = c["newcomers"] / (c["newcomers"] + c["mains"] * c["stay"])
    f_before = mean_p(c["main_skill"], 0)
    f_after = (1 - sh_new) * mean_p(c["main_skill"], c["delta"]) + sh_new * mean_p(c["new_skill"], c["delta"])
    f_true = (1 - sh_new) * (mean_p(c["main_skill"], c["delta"]) - mean_p(c["main_skill"], 0)) + \
        sh_new * (mean_p(c["new_skill"], c["delta"]) - mean_p(c["new_skill"], 0))
    f_true_stay = mean_p(c["main_skill"], c["delta"]) - mean_p(c["main_skill"], 0)
    res["formula"] = {"before_rate": r2(f_before * 100), "after_rate": r2(f_after * 100), "naive": r2((f_after - f_before) * 100),
                      "true_after_users": r2(f_true * 100), "true_stayers": r2(f_true_stay * 100),
                      "mix_term": r2((f_after - f_before - f_true) * 100), "newcomer_share_after": r2(sh_new * 100)}

    rng = np.random.default_rng(SEED)
    ex, df = one_rep(rng, c, keep=True)
    df.to_csv(DATA / "players_example.csv", index=False)
    res["example_one_rep"] = {k: (r2(v) if isinstance(v, float) else v) for k, v in ex.items()}

    base = run(SEED * 1000, c, N_REP)
    base.round(4).to_csv(RES / "reps_base.csv", index=False)
    q = lambda s: [r2(s.quantile(0.05)), r2(s.quantile(0.95))]
    res["base_reps"] = {k: {"mean": r2(base[k].mean()), "p5_p95": q(base[k])} for k in
                        ["naive", "stayers", "band", "true_after_users", "true_stayers", "mix_term", "before_rate", "after_rate"]}
    res["base_reps"]["naive_negative_pct"] = r2((base.naive < 0).mean() * 100)
    res["base_reps"]["stayers_negative_pct"] = r2((base.stayers < 0).mean() * 100)
    res["base_reps"]["band_negative_pct"] = r2((base.band < 0).mean() * 100)
    res["base_reps"]["max_abs_naive_minus_true_plus_mix"] = r2((base.naive - base.true_after_users - base.mix_term).abs().max())

    # 確かめ：新しく使い始めた人の数×うまさ×調整の効き×残り方（42通り、各100回）
    grid = []; j = 0
    for nn in [0, 1500, 3000]:
        for ns in [0.0, -0.5, -1.0]:
            for d in [0.0, 0.15, 0.3]:
                for sw in [0.0, 1.0]:
                    cc = {**c, "newcomers": nn, "new_skill": ns, "delta": d, "stay_by_wins": sw}
                    if nn == 0 and ns != 0.0:
                        continue
                    g = run(SEED * 100000 + j * 1000, cc, 100); j += 1
                    grid.append({"newcomers": nn, "new_skill": ns, "delta": d, "stay_by_wins": sw,
                                 "true_after_users": r2(g.true_after_users.mean()), "true_stayers": r2(g.true_stayers.mean()),
                                 "naive": r2(g.naive.mean()), "stayers": r2(g.stayers.mean()), "band": r2(g.band.mean()),
                                 "naive_err": r2((g.naive - g.true_after_users).mean()),
                                 "stayers_err": r2((g.stayers - g.true_stayers).mean()),
                                 "band_err": r2((g.band - g.true_after_users).mean()),
                                 "naive_wrong_sign_pct": r2(((g.naive < 0) & (g.true_after_users > 0)).mean() * 100) if d > 0 else None})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    gd = grid[grid.delta > 0]
    res["grid"] = {"n_cases": int(len(grid)),
                   "naive_err_range": [float(grid.naive_err.min()), float(grid.naive_err.max())],
                   "stayers_err_range": [float(grid.stayers_err.min()), float(grid.stayers_err.max())],
                   "band_err_range": [float(grid.band_err.min()), float(grid.band_err.max())],
                   "stayers_err_range_random_stay": [float(grid[grid.stay_by_wins == 0].stayers_err.min()), float(grid[grid.stay_by_wins == 0].stayers_err.max())],
                   "stayers_err_range_stay_by_wins": [float(grid[grid.stay_by_wins == 1].stayers_err.min()), float(grid[grid.stay_by_wins == 1].stayers_err.max())],
                   "naive_err_when_no_skill_gap": [float(grid[(grid.new_skill == 0)].naive_err.min()), float(grid[(grid.new_skill == 0)].naive_err.max())],
                   "cases_delta_pos": int(len(gd)),
                   "cases_naive_mean_below_zero_delta_pos": int((gd.naive < 0).sum()),
                   "naive_wrong_sign_pct_range": [float(gd.naive_wrong_sign_pct.min()), float(gd.naive_wrong_sign_pct.max())]}
    res["groups_formula"] = {"mains_no_patch": r2(mean_p(c["main_skill"], 0) * 100), "mains_after": r2(mean_p(c["main_skill"], c["delta"]) * 100),
                             "newcomers_no_patch": r2(mean_p(c["new_skill"], 0) * 100), "newcomers_after": r2(mean_p(c["new_skill"], c["delta"]) * 100)}
    g0 = grid[(grid.newcomers == 0) & (grid.stay_by_wins == 0)]
    res["grid"]["no_newcomer_random_stay_err_range_all_methods"] = [float(g0[["naive_err", "stayers_err", "band_err"]].min().min()),
                                                                    float(g0[["naive_err", "stayers_err", "band_err"]].max().max())]
    g1 = grid[(grid.newcomers == 0) & (grid.stay_by_wins == 1)]
    res["grid"]["no_newcomer_stay_by_wins_naive_err_range"] = [float(g1.naive_err.min()), float(g1.naive_err.max())]
    gn = grid[grid.newcomers > 0]
    res["grid"]["with_newcomers_cases"] = int(len(gn))
    res["grid"]["with_newcomers_stayers_abs_err_lt_naive_cases"] = int((gn.stayers_err.abs() < gn.naive_err.abs()).sum())
    res["grid"]["with_newcomers_band_abs_err_lt_naive_cases"] = int((gn.band_err.abs() < gn.naive_err.abs()).sum())
    with open(RES / "a1072_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：前後の勝率（棒、0始まり）
    b = res["base_reps"]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    labs = ["① 前後をそのまま", "② 同じ人だけ", "③ 点数の帯ごと", "本当の上がり幅\n（後に使った人）", "本当の上がり幅\n（同じ人）"]
    keys = ["naive", "stayers", "band", "true_after_users", "true_stayers"]
    vals = [b[k]["mean"] for k in keys]
    cols = [ORANGE, BLUE, GREEN, INK, GRAY]
    ax.bar(range(5), vals, color=cols, width=0.6)
    ax.axhline(0, color=INK, lw=0.8)
    for i, k in enumerate(keys):
        lo, hi = b[k]["p5_p95"]
        ax.plot([i, i], [lo, hi], color=INK, lw=1)
        ax.text(i + 0.08, vals[i] + (0.3 if vals[i] >= 0 else -0.3), f"{vals[i]:+.2f}", fontsize=9, va="bottom" if vals[i] >= 0 else "top")
    ax.set_xticks(range(5)); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylabel("調整の後−前の勝率（ポイント）")
    ax.set_title(f"基本の置き方（{N_REP:,}回の平均、縦線は5〜95%の範囲）")
    save(fig, "a1072_methods.png", SRC, y=-0.07)

    # 図2：前後の勝率の分かれ方（グループ別の式の値）
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    grp = [("使い続けてきた人", c["main_skill"]), ("新しく使い始めた人", c["new_skill"])]
    x = np.arange(2); w = 0.35
    v0 = [mean_p(m, 0) * 100 for _, m in grp]; v1 = [mean_p(m, c["delta"]) * 100 for _, m in grp]
    ax.bar(x - w / 2, v0, w, color=LIGHT, label="調整がなかったら（式の値）")
    ax.bar(x + w / 2, v1, w, color=BLUE, label="調整の後（式の値）")
    for i in range(2):
        # 値は棒の内側のまん中に置く（全体の勝率の横線と重ならないように）
        ax.text(x[i] - w / 2, v0[i] / 2, f"{v0[i]:.2f}%", ha="center", va="center", fontsize=10, color=INK)
        ax.text(x[i] + w / 2, v1[i] / 2, f"{v1[i]:.2f}%", ha="center", va="center", fontsize=10, color="white")
    ax.axhline(res["formula"]["before_rate"], color=ORANGE, ls="--", lw=1.2,
               label=f"調整の前の勝率（全体）{res['formula']['before_rate']:.2f}%")
    ax.axhline(res["formula"]["after_rate"], color=INK, ls=":", lw=1.2,
               label=f"調整の後の勝率（全体、新しく使い始めた人が{res['formula']['newcomer_share_after']:.2f}%）{res['formula']['after_rate']:.2f}%")
    ax.set_xticks(x); ax.set_xticklabels([f"{n}（うまさの平均 {m:+.1f}）" for n, m in grp])
    ax.set_ylabel("勝率（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("どちらのグループも調整で勝率が上がるのに、全体では下がって見える")
    save(fig, "a1072_groups.png", SRC)

    # 図3：42通りのずれ（新しく使い始めた人の数・うまさごとに並べる）
    fig, ax = plt.subplots(figsize=(9.0, 4.6))
    combos = [(0, 0.0), (1500, 0.0), (1500, -0.5), (1500, -1.0), (3000, 0.0), (3000, -0.5), (3000, -1.0)]
    ax.axhline(0, color=INK, lw=0.8)
    for ci, (nn, ns) in enumerate(combos):
        g = grid[(grid.newcomers == nn) & (grid.new_skill == ns)].reset_index(drop=True)
        off = np.linspace(-0.3, 0.3, len(g))
        for col, cl, mk, lab in [("naive_err", ORANGE, "o", "① 前後をそのまま − 本当（後に使った人）"),
                                 ("stayers_err", BLUE, "s", "② 同じ人だけ − 本当（同じ人）"),
                                 ("band_err", GREEN, "^", "③ 点数の帯ごと − 本当（後に使った人）")]:
            ax.scatter(ci + off, g[col], color=cl, marker=mk, s=20, label=lab if ci == 0 else None)
    ax.set_xticks(range(len(combos)))
    ax.set_xticklabels(["0人"] + [f"{nn:,}人\nうまさ{ns:+.1f}" for nn, ns in combos[1:]], fontsize=9)
    ax.set_xlabel("新しく使い始めた人の数とうまさの平均（使い続けてきた人は+0.5）\n各列の中は、調整の効き3通り×残り方2通り")
    ax.set_ylabel("ずれ（ポイント、各100回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    gr = res["grid"]
    ax.set_title(f"置き方の{gr['n_cases']}通り：ずれは①{gr['naive_err_range'][0]:+.1f}〜{gr['naive_err_range'][1]:+.1f}、"
                 f"②{gr['stayers_err_range'][0]:+.2f}〜{gr['stayers_err_range'][1]:+.2f}、③{gr['band_err_range'][0]:+.1f}〜{gr['band_err_range'][1]:+.1f}ポイント", fontsize=12)
    save(fig, "a1072_grid.png", SRC, y=-0.08)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
