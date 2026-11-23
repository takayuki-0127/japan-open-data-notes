"""1120 回復と攻撃を同じ割合で強くすると、勝負がつくまでの長さはどう変わるのか？（架空のデータ）

架空のゲームで、同じ強さの2人が1対1で戦う。毎ターン、2人は同時に動き、決まった確率で回復（体力の上限を超えた分は捨てる）、残りは攻撃する。
攻撃のダメージは攻撃力×（0.75〜1.25の一様な乱数）、1割で会心（2倍）。どちらかの体力が0以下になったら勝負がつく。
攻撃力と回復量を同じ倍率 k で強くし（体力の上限はそのまま）、勝負がつくまでのターン数が 1/k・1/k² とどう比べられるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1120
SRC = "架空のゲームの1対1の勝負（作成者が置いた攻撃・回復・体力からの乱数、seed 1120）"
HP = 1000.0
ATK = 100.0
Q_HEAL = 0.4          # 回復を選ぶ確率
SPREAD = 0.25         # ダメージの乱数の幅（±）
CRIT, CRIT_M = 0.1, 2.0
RHOS = [0.0, 0.5, 0.8, 1.0, 1.2]     # 回復の見込み÷受ける攻撃の見込み（1ターンあたり）
KS = [1.0, 1.1, 1.2, 1.5, 2.0]
N_FIGHT = 4000
MAX_T = 100000
GRID_HP = [500.0, 1000.0, 2000.0]
GRID_SPREAD = [0.1, 0.5]
GRID_Q = [0.3, 0.5]
GRID_RHOS = [0.0, 0.5, 1.0, 1.2]
GRID_K = 1.2
GRID_N = 1500


def r(x, d=3):
    return round(float(x), d)


def heal_amount(rho, q=Q_HEAL, atk=ATK, spread=SPREAD):
    """1ターンあたりの回復の見込み（q×回復量）が、受ける攻撃の見込み（(1−q)×攻撃力×会心込みの平均）の rho 倍になる回復量"""
    mean_hit = atk * (1 + CRIT * (CRIT_M - 1))
    return rho * (1 - q) * mean_hit / q


def fight(seed, k, rho, hp=HP, q=Q_HEAL, spread=SPREAD, n=N_FIGHT, hp_scale=1.0, keep=0):
    """n 回の勝負を同時に流し、勝負がついたターン数を返す（MAX_T まで。つかなければ −1）。
    k を比べるときは同じ seed から始める"""
    rng = np.random.default_rng(seed)
    hmax = hp * hp_scale
    h = heal_amount(rho, q) * k
    H = np.full((n, 2), hmax)
    T = np.full(n, -1)
    alive = np.ones(n, bool)
    trace = []
    t = 0
    while alive.any() and t < MAX_T:
        t += 1
        idx = np.where(alive)[0]
        m = len(idx)
        hl = rng.random((m, 2)) < q
        u = rng.uniform(1 - spread, 1 + spread, (m, 2))
        c = rng.random((m, 2)) < CRIT
        dmg = k * ATK * u * np.where(c, CRIT_M, 1.0)
        Hs = np.minimum(H[idx] + np.where(hl, h, 0.0), hmax) - np.where(hl, 0.0, dmg)[:, ::-1]
        H[idx] = Hs
        if keep and t <= 400:
            trace.append(H[:keep].copy())
        end = (Hs <= 0).any(1)
        T[idx[end]] = t
        alive[idx[end]] = False
    return T, trace


def summarize(T):
    done = T[T > 0]
    return {"mean": float(done.mean()), "median": float(np.median(done)), "p90": float(np.percentile(done, 90)),
            "censored": float((T < 0).mean())}


def main():
    t0 = time.time()
    rows = []
    traces = {}
    dists = {}
    for i, rho in enumerate(RHOS):
        base = None
        for k in KS:
            T, tr = fight([SEED, i], k, rho, keep=3 if k in (1.0, 1.5) and rho in (0.5, 1.2) else 0)
            if tr:
                traces[(rho, k)] = (np.array(tr), T[:3].copy())
            if rho == 1.2:
                dists[k] = T.copy()
            s = summarize(T)
            if base is None:
                base = s
            rows.append({"rho": rho, "heal": r(heal_amount(rho) * k, 2), "attack": r(ATK * k, 1), "k": k,
                         "mean_turns": r(s["mean"], 2), "median_turns": r(s["median"], 1), "p90_turns": r(s["p90"], 1),
                         "censored_share": r(s["censored"], 4),
                         "mean_ratio": r(s["mean"] / base["mean"], 3), "median_ratio": r(s["median"] / base["median"], 3),
                         "one_over_k": r(1 / k, 3), "one_over_k2": r(1 / k ** 2, 3)})
        # 体力の上限も同じ k=1.2 倍にしたとき（作りどおりなら長さは変わらない）
        T, _ = fight([SEED, i], 1.2, rho, hp_scale=1.2)
        s = summarize(T)
        rows.append({"rho": rho, "heal": r(heal_amount(rho) * 1.2, 2), "attack": r(ATK * 1.2, 1), "k": "1.2+HP1.2",
                     "mean_turns": r(s["mean"], 2), "median_turns": r(s["median"], 1), "p90_turns": r(s["p90"], 1),
                     "censored_share": r(s["censored"], 4),
                     "mean_ratio": r(s["mean"] / base["mean"], 3), "median_ratio": r(s["median"] / base["median"], 3),
                     "one_over_k": 1.0, "one_over_k2": 1.0})
    main_df = pd.DataFrame(rows)
    main_df.to_csv(RES / "length_by_k.csv", index=False)

    # 体力の動きの例（data）
    ex = []
    for (rho, k), (arr, tend) in traces.items():
        for f in range(arr.shape[1]):
            for t in range(min(arr.shape[0], tend[f] if tend[f] > 0 else arr.shape[0])):
                ex.append({"rho": rho, "k": k, "fight": f + 1, "turn": t + 1,
                           "hp_1": r(arr[t, f, 0], 1), "hp_2": r(arr[t, f, 1], 1)})
    pd.DataFrame(ex).to_csv(DATA / "hp_traces_example.csv", index=False)

    # 確かめ：置き方を変えて k=1.2
    grid = []
    gi = 0
    for hp in GRID_HP:
        for sp in GRID_SPREAD:
            for q in GRID_Q:
                for rho in GRID_RHOS:
                    gi += 1
                    T1, _ = fight([SEED, 100, gi], 1.0, rho, hp=hp, q=q, spread=sp, n=GRID_N)
                    T2, _ = fight([SEED, 100, gi], GRID_K, rho, hp=hp, q=q, spread=sp, n=GRID_N)
                    s1, s2 = summarize(T1), summarize(T2)
                    grid.append({"hp": hp, "spread": sp, "q_heal": q, "rho": rho,
                                 "mean_turns_k1": r(s1["mean"], 2), "mean_turns_k12": r(s2["mean"], 2),
                                 "censored_k1": r(s1["censored"], 4), "censored_k12": r(s2["censored"], 4),
                                 "mean_ratio": r(s2["mean"] / s1["mean"], 3),
                                 "median_ratio": r(s2["median"] / s1["median"], 3)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid_k12.csv", index=False)

    def pick(rho, k):
        return main_df[(main_df.rho == rho) & (main_df.k.astype(str) == str(k))].iloc[0]

    gsum = g.groupby("rho").agg(ratio_min=("mean_ratio", "min"), ratio_max=("mean_ratio", "max"),
                                mturn_min=("mean_turns_k1", "min"), mturn_max=("mean_turns_k1", "max"),
                                cens_max=("censored_k1", "max")).reset_index()
    out = {
        "settings": {"hp": HP, "attack": ATK, "q_heal": Q_HEAL, "spread": SPREAD, "crit": CRIT, "crit_mult": CRIT_M,
                     "rhos": RHOS, "heal_amounts": {str(x): r(heal_amount(x), 2) for x in RHOS}, "ks": KS,
                     "n_fight": N_FIGHT, "max_turns": MAX_T,
                     "grid_hp": GRID_HP, "grid_spread": GRID_SPREAD, "grid_q": GRID_Q, "grid_rhos": GRID_RHOS,
                     "grid_k": GRID_K, "grid_n": GRID_N, "seed": SEED},
        "by_rho_k": rows,
        "k12_mean_ratio": {str(rho): float(pick(rho, 1.2).mean_ratio) for rho in RHOS},
        "k2_mean_ratio": {str(rho): float(pick(rho, 2.0).mean_ratio) for rho in RHOS},
        "k1_mean_turns": {str(rho): float(pick(rho, 1.0).mean_turns) for rho in RHOS},
        "hp_scaled_mean_ratio": {str(rho): float(pick(rho, "1.2+HP1.2").mean_ratio) for rho in RHOS},
        "censored_max": r(main_df.censored_share.max(), 4),
        "grid_by_rho": [{k: (r(v, 3) if isinstance(v, float) else v) for k, v in rec.items()} for rec in gsum.to_dict("records")],
        "grid_n_cells": int(len(g)),
        "grid_below_1_over_k": int((g.mean_ratio < 1 / GRID_K).sum()),
        "grid_below_1_over_k2": int((g.mean_ratio < 1 / GRID_K ** 2).sum()),
        "grid_below_1_over_k2_rho_min": float(g[g.mean_ratio < 1 / GRID_K ** 2].rho.min()),
        "grid_censored_max": r(max(g.censored_k1.max(), g.censored_k12.max()), 4),
    }
    with open(RES / "a1120_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：倍率 k と、平均の長さの比（k=1 を1とする）
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    kk = np.linspace(1, 2, 50)
    ax.plot(kk, 1 / kk, color=INK, ls="--", lw=1.2, label="1/k（攻撃と回復の差の分だけ速くなる目安）")
    ax.plot(kk, 1 / kk ** 2, color=INK, ls=":", lw=1.2, label="1/k²（振れだけで決まるときの目安）")
    cols = [GRAY, LIGHT, BLUE, GREEN, ORANGE]
    for rho, col in zip(RHOS, cols):
        d = main_df[(main_df.rho == rho) & (main_df.k.astype(str) != "1.2+HP1.2")]
        ax.plot(d.k.astype(float), d.mean_ratio, color=col, marker="o", lw=2,
                label=f"回復÷攻撃の見込み {rho}（k=1で平均{float(d.mean_turns.iloc[0]):g}ターン）")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("攻撃力と回復量に掛けた倍率 k（体力の上限はそのまま）")
    ax.set_ylabel("勝負がつくまでの平均ターン数（k=1 を1とする）")
    ax.set_title("同じ倍率で強くしても、回復が強いほど長さは大きく縮む")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    save(fig, "a1120_ratio.png", SRC)

    # 図2：勝負がつくまでのターン数の分布（回復÷攻撃の見込み1.2）
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for k, col in zip([1.0, 1.2, 1.5, 2.0], [GRAY, LIGHT, BLUE, ORANGE]):
        t = np.sort(dists[k][dists[k] > 0])
        ax.step(t, np.arange(1, len(t) + 1) / len(t), where="post", color=col, lw=2,
                label=f"k={k}（平均{round(float(t.mean()), 2):g}・中央値{np.median(t):g}ターン）")
    ax.set_xscale("log")
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("勝負がつくまでのターン数（対数の目盛り）")
    ax.set_ylabel("そのターンまでに勝負がついた割合")
    ax.set_title("回復÷攻撃の見込み1.2：倍率を上げると長い勝負が減る")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1120_dist.png", SRC)

    # 図3：確かめ（k=1.2 の平均の比、置き方48通り）
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    xs = {rho: i for i, rho in enumerate(GRID_RHOS)}
    for j, (rho, d) in enumerate(g.groupby("rho")):
        ax.scatter(xs[rho] + np.linspace(-0.25, 0.25, len(d)), d.mean_ratio,
                   c=[{500.0: LIGHT, 1000.0: BLUE, 2000.0: INK}[h] for h in d.hp], s=22)
    ax.hlines([1 / GRID_K, 1 / GRID_K ** 2], -0.5, 3.45, color=INK, lw=1, linestyles=["--", ":"])
    ax.text(3.6, 1 / GRID_K, "1/1.2", va="center", fontsize=9)
    ax.text(3.6, 1 / GRID_K ** 2, "1/1.2²", va="center", fontsize=9)
    for h, col in [(500.0, LIGHT), (1000.0, BLUE), (2000.0, INK)]:
        ax.scatter([], [], c=col, s=22, label=f"体力の上限 {h:.0f}")
    ax.set_xticks(range(len(GRID_RHOS)))
    ax.set_xticklabels([f"回復÷攻撃 {x}" for x in GRID_RHOS])
    ax.set_ylim(0, 1.05)
    ax.set_xlim(-0.5, 4.0)
    ax.set_ylabel("k=1.2 の平均ターン数 ÷ k=1")
    ax.set_title("置き方48通り（体力・ダメージの振れ・回復を選ぶ確率）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1120_grid.png", SRC)

    print("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
