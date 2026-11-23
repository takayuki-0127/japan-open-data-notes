"""1068 対戦の相手を自分で選べると、点数はどれだけ上がって見えるのか？（架空のデータ）

架空の対戦ゲームのリーグ（400人）。1人ひとりの「本当の強さ」を作成者が置き、勝ち負けは本当の強さの差で決まる確率で引く。
点数の付け方は「勝ったら、勝つ見込みが低かった分だけ多く足し、負けたら見込みが高かった分だけ多く引く」一般的な形
（見込み E＝1/(1+10^(−点数の差/400))、点の動き＝K×(結果−E)）。
本当の強さがちょうど真ん中（リーグの平均）の人が、毎回くじで出された5人の候補から相手を選べるとき、
選び方で点数がどれだけ上がって見えるかを数える。本当の強さは変わらないので、点数の上がりはすべて「見かけ」。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1068
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1068）"
N = 400            # リーグの人数（相手になる人）
SD_TRUE = 200      # 本当の強さの散らばり（点数の物差しで）
WARM, EVAL, SETTLE = 300, 300, 100
N_FOCAL = 20       # 選び方ごとの人数（本当の強さは真ん中＝0）
BASE = {"eps": 0.1, "K": 20, "est_sd": 0.10, "m": 5}
STRAT = ["random", "low_rating", "easy_win", "underrated"]
SNAME = {"random": "①選ばない（くじ）", "low_rating": "②点数のいちばん低い相手",
         "easy_win": "③いちばん勝てそうな相手", "underrated": "④点数のわりに勝てそうな相手"}


def p_true(d_theta, eps):
    """本当の勝つ確率：試合の eps の割合は五分五分で決まり、残りは本当の強さの差で決まる"""
    return eps / 2 + (1 - eps) / (1 + 10 ** (-d_theta / 400))


def expect(d_r):
    return 1 / (1 + 10 ** (-d_r / 400))


def run(rng, eps, K, est_sd, m, keep=False):
    theta = rng.normal(0, SD_TRUE, N)
    R = np.full(N, 1500.0)
    # 慣らし：全員がくじで相手を決めて対戦
    for _ in range(WARM):
        idx = rng.permutation(N); a, b = idx[::2], idx[1::2]
        s = (rng.random(N // 2) < p_true(theta[a] - theta[b], eps)).astype(float)
        e = expect(R[a] - R[b])
        R[a] += K * (s - e); R[b] -= K * (s - e)
    nf = N_FOCAL * len(STRAT)
    strat = np.repeat(np.arange(len(STRAT)), N_FOCAL)
    Rf = np.full(nf, 1500.0)
    traj = np.zeros((EVAL, len(STRAT)))
    wins = np.zeros(nf); exp_sum = np.zeros(nf); opp_theta = np.zeros(nf); opp_err = np.zeros(nf)
    rmean = np.zeros(nf); n_meas = 0
    for t in range(EVAL):
        idx = rng.permutation(N); a, b = idx[::2], idx[1::2]
        s = (rng.random(N // 2) < p_true(theta[a] - theta[b], eps)).astype(float)
        e = expect(R[a] - R[b])
        R[a] += K * (s - e); R[b] -= K * (s - e)
        # 選べる人：くじで出された m 人の候補から相手を選ぶ
        cand = rng.integers(0, N, (nf, m))
        Rc = R[cand]
        pt = p_true(0 - theta[cand], eps)
        ph = pt + rng.normal(0, est_sd, (nf, m))           # 勝てそうかの見立て（誤差あり）
        ec = expect(Rf[:, None] - Rc)
        pick = np.where(strat == 0, 0,
               np.where(strat == 1, Rc.argmin(1),
               np.where(strat == 2, ph.argmax(1), (ph - ec).argmax(1))))
        j = cand[np.arange(nf), pick]
        pj = pt[np.arange(nf), pick]; ej = ec[np.arange(nf), pick]
        res = (rng.random(nf) < pj).astype(float)
        Rf += K * (res - ej)
        np.add.at(R, j, -K * (res - ej))
        traj[t] = [Rf[strat == k].mean() for k in range(len(STRAT))]
        if t >= SETTLE:
            wins += res; exp_sum += ej; opp_theta += theta[j]
            # 相手の「点数の高すぎ」：本当の強さに見合う点数（リーグ全体の点数を本当の強さに当てはめた線）との差
            if (t - SETTLE) % 10 == 0:
                slope, icpt = np.polyfit(theta, R, 1)
            opp_err += R[j] - (icpt + slope * theta[j])
            rmean += Rf; n_meas += 1
    out = {"strat": strat, "rating_mean": rmean / n_meas, "win": wins / n_meas, "expect": exp_sum / n_meas,
           "opp_theta": opp_theta / n_meas, "opp_over": opp_err / n_meas, "traj": traj,
           "pct_league": np.array([(R < r).mean() * 100 for r in rmean / n_meas]),
           "league_slope": np.polyfit(theta, R, 1)[0]}
    if keep:
        out["players"] = pd.DataFrame({"player_id": np.arange(1, N + 1), "theta": theta.round(2), "rating_end": R.round(2)})
    return out


def summarize(outs):
    rows = []
    for k, sname in enumerate(STRAT):
        rm = np.concatenate([o["rating_mean"][o["strat"] == k] for o in outs])
        rows.append({"strategy": sname, "name": SNAME[sname], "n_players": len(rm),
                     "rating_minus_1500": round(float(rm.mean() - 1500), 2),
                     "rating_se": round(float(rm.std(ddof=1) / np.sqrt(len(rm))), 2),
                     "league_percentile": round(float(np.concatenate([o["pct_league"][o["strat"] == k] for o in outs]).mean()), 2),
                     "win_rate": round(float(np.concatenate([o["win"][o["strat"] == k] for o in outs]).mean() * 100), 2),
                     "expected_by_points": round(float(np.concatenate([o["expect"][o["strat"] == k] for o in outs]).mean() * 100), 2),
                     "opp_true_strength": round(float(np.concatenate([o["opp_theta"][o["strat"] == k] for o in outs]).mean()), 2),
                     "opp_points_over_fair": round(float(np.concatenate([o["opp_over"][o["strat"] == k] for o in outs]).mean()), 2)})
    df = pd.DataFrame(rows)
    base = df.rating_minus_1500.iloc[0]
    df["vs_random"] = (df.rating_minus_1500 - base).round(2)
    return df


def main():
    t0 = time.time()
    b = BASE
    res = {"setting": {"league_players": N, "true_sd": SD_TRUE, "warm_rounds": WARM, "eval_rounds": EVAL,
                       "settle_rounds": SETTLE, "focal_per_strategy": N_FOCAL, **b, "reps": 30}}
    outs = [run(np.random.default_rng(SEED * 100 + r), b["eps"], b["K"], b["est_sd"], b["m"], keep=(r == 0)) for r in range(30)]
    base = summarize(outs)
    base.to_csv(RES / "base_by_strategy.csv", index=False)
    res["base"] = base.set_index("strategy").to_dict(orient="index")
    res["max_abs_win_minus_expected_pt"] = round(float((base.win_rate - base.expected_by_points).abs().max()), 2)
    res["focal_total_per_rep"] = N_FOCAL * len(STRAT)
    res["rating_se_range"] = [float(base.rating_se.min()), float(base.rating_se.max())]
    res["league_points_per_true_point"] = round(float(np.mean([o["league_slope"] for o in outs])), 3)
    traj = np.mean([o["traj"] for o in outs], 0)
    tr = pd.DataFrame(traj.round(2), columns=STRAT); tr.insert(0, "match", np.arange(1, EVAL + 1))
    tr.to_csv(RES / "trajectory.csv", index=False)

    o0 = outs[0]
    o0["players"].to_csv(DATA / "league_players.csv", index=False)
    pd.DataFrame({"focal_id": np.arange(1, len(o0["strat"]) + 1), "strategy": [STRAT[k] for k in o0["strat"]],
                  "rating_mean": o0["rating_mean"].round(2), "win_rate": (o0["win"] * 100).round(2),
                  "expected_by_points": (o0["expect"] * 100).round(2)}).to_csv(DATA / "focal_players.csv", index=False)

    # 確かめ1：五分五分の試合の割合×1試合の点の幅×見立ての誤差（27通り、各10回）
    grid = []
    j = 0
    for eps in [0.0, 0.1, 0.2]:
        for K in [10, 20, 40]:
            for es in [0.05, 0.10, 0.20]:
                g = summarize([run(np.random.default_rng(SEED * 10000 + j * 100 + r), eps, K, es, b["m"]) for r in range(10)]); j += 1
                row = {"eps": eps, "K": K, "est_sd": es}
                for _, x in g.iterrows():
                    row[f"{x.strategy}_vs_random"] = x.vs_random
                    row[f"{x.strategy}_win"] = x.win_rate
                    row[f"{x.strategy}_pct"] = x.league_percentile
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    rng_ = lambda c: [float(grid[c].min()), float(grid[c].max())]
    res["grid_range"] = {"n_cases": int(len(grid)),
                         "low_rating_vs_random": rng_("low_rating_vs_random"), "easy_win_vs_random": rng_("easy_win_vs_random"),
                         "underrated_vs_random": rng_("underrated_vs_random"),
                         "underrated_pct": rng_("underrated_pct"),
                         "underrated_positive_cases": int((grid.underrated_vs_random > 0).sum()),
                         "easy_win_negative_cases": int((grid.easy_win_vs_random < 0).sum()),
                         "low_rating_negative_cases": int((grid.low_rating_vs_random < 0).sum()),
                         "easy_win_win": rng_("easy_win_win")}
    for eps in [0.0, 0.1, 0.2]:
        gg = grid[grid.eps == eps]
        res["grid_range"][f"eps{eps}"] = {"low_rating_vs_random": [float(gg.low_rating_vs_random.min()), float(gg.low_rating_vs_random.max())],
                                          "easy_win_vs_random": [float(gg.easy_win_vs_random.min()), float(gg.easy_win_vs_random.max())],
                                          "underrated_vs_random": [float(gg.underrated_vs_random.min()), float(gg.underrated_vs_random.max())]}

    # 確かめ2：候補の人数 m（基本の置き方、各10回）
    mrows = []
    for i, m in enumerate([1, 2, 3, 5, 10, 20]):
        g = summarize([run(np.random.default_rng(SEED * 1000000 + i * 100 + r), b["eps"], b["K"], b["est_sd"], m) for r in range(10)])
        row = {"m": m}
        for _, x in g.iterrows():
            row[f"{x.strategy}_vs_random"] = x.vs_random
            row[f"{x.strategy}_pct"] = x.league_percentile
        mrows.append(row)
    mdf = pd.DataFrame(mrows)
    mdf.to_csv(RES / "by_candidates.csv", index=False)
    res["by_candidates"] = mdf.set_index("m").to_dict(orient="index")
    for K in [10, 20, 40]:
        gg = grid[grid.K == K]
        res["grid_range"][f"K{K}"] = {"low_rating_vs_random": [float(gg.low_rating_vs_random.min()), float(gg.low_rating_vs_random.max())],
                                      "underrated_vs_random": [float(gg.underrated_vs_random.min()), float(gg.underrated_vs_random.max())]}
    with open(RES / "a1068_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：選び方ごとの点数の上がり（①との差）と勝率
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.2))
    cols = [GRAY, LIGHT, BLUE, ORANGE]
    labs = [SNAME[s] for s in STRAT]
    ax = axes[0]
    v = base.vs_random.values
    ax.barh(range(4), v, color=cols)
    for i, x in enumerate(v):
        ax.text(x + (3 if x >= 0 else -3), i, f"{x:+.1f}点", va="center", ha="left" if x >= 0 else "right", fontsize=9)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(range(4)); ax.set_yticklabels(labs); ax.invert_yaxis()
    lim = max(abs(v).max() * 1.5, 10); ax.set_xlim(-lim, lim)
    ax.set_xlabel("点数の上がり（①選ばないとの差、点）")
    ax.set_title("点数")
    ax = axes[1]
    w = base.win_rate.values
    ax.barh(range(4), w, color=cols)
    for i, x in enumerate(w):
        ax.text(x + 1, i, f"{x:.1f}%", va="center", fontsize=9)
    ax.set_yticks(range(4)); ax.set_yticklabels([]); ax.invert_yaxis(); ax.set_xlim(0, 100)
    ax.set_xlabel("勝った割合（%）")
    ax.set_title("勝った割合")
    fig.suptitle("本当の強さが真ん中の人が5人の候補から相手を選ぶと（基本の置き方、600人の平均）", fontsize=12)
    fig.tight_layout()
    save(fig, "a1068_strategy.png", SRC, y=-0.01)

    # 図2：点数の動き（試合ごと、平均）
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    for s, c in zip(STRAT, cols):
        ax.plot(tr.match, tr[s], color=c if s != "low_rating" else "#7fa6d8", lw=1.6, label=SNAME[s])
    ax.axhline(1500, color=INK, lw=0.6, ls=":")
    ax.axvline(SETTLE, color=GRAY, lw=0.8, ls="--")
    ax.text(SETTLE + 3, ax.get_ylim()[0] + 2, "ここから後を平均", fontsize=9, color=INK, va="bottom")
    ax.set_xlabel("選べるようになってからの試合数"); ax.set_ylabel("点数（600人の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("点数の動き：はじめは全員1500点（本当の強さに見合う点数も1500点）")
    save(fig, "a1068_trajectory.png", SRC)

    # 図3：27通りの確かめ
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    xs = np.arange(len(grid))
    for s, c, mk in [("low_rating", "#7fa6d8", "v"), ("easy_win", BLUE, "o"), ("underrated", ORANGE, "s")]:
        ax.scatter(xs, grid[f"{s}_vs_random"], color=c, marker=mk, s=28, label=SNAME[s])
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_ylim(min(grid[[c for c in grid.columns if c.endswith("_vs_random")]].min().min() * 1.2, -10), grid.underrated_vs_random.max() * 1.15)
    for k in [9, 18]:
        ax.axvline(k - 0.5, color=GRAY, lw=0.8, ls="--")
    for k, eps in enumerate([0.0, 0.1, 0.2]):
        ax.text(k * 9 + 4, ax.get_ylim()[1], f"五分五分の試合 {int(eps * 100)}%", ha="center", va="top", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels([f"{k}" for k in grid.K], fontsize=7)
    ax.set_xlabel("1試合の点の幅 K（各Kの中は、見立ての誤差5・10・20ポイントの順）")
    ax.set_ylabel("①選ばないとの差（点）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    ax.set_title("置き方を変えた27通り：④は27通りすべてで上がり、②はKが大きいと下がる")
    save(fig, "a1068_grid.png", SRC, y=-0.13)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
