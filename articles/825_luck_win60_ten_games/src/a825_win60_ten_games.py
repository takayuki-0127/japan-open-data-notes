"""825 勝率6割のチームが、10試合で負け越す確率は？（架空のデータ）

架空のチーム。1試合ごとに、本当の勝率 p で勝つ（引き分けなし、試合どうしは互いに影響しない）と置く。
10試合で負け越す（勝ち数 < 負け数）確率を、二項分布の式と乱数の両方で数える。
"""
import json
import time
from math import comb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 825
SRC = "架空のチームの試合結果（作成者が乱数で作成、seed 825）"
rng = np.random.default_rng(SEED)
N_SIM = 200_000


def p_losing_exact(p, n):
    """n試合で勝ち数 < 負け数 になる確率（二項分布の式）"""
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1) if k < n - k)


def p_even_exact(p, n):
    if n % 2:
        return 0.0
    k = n // 2
    return comb(n, k) * p ** k * (1 - p) ** (n - k)


def sim_basic(rng, p, n, reps):
    w = rng.random((reps, n)) < p
    return w


def sim_draws(rng, p, n, reps, draw=0.10):
    """引き分けを draw の割合で入れる。決着した試合の中では勝率 p"""
    u = rng.random((reps, n))
    win = u < (1 - draw) * p
    lose = (u >= (1 - draw) * p) & (u < 1 - draw)
    return win.sum(1), lose.sum(1)


def schedule_probs(p, n, sd):
    """相手が10試合でそれぞれ違う（日程が決まっている）。1試合ごとの勝率は平均 p・標準偏差 sd に並べる"""
    z = (np.arange(n) - (n - 1) / 2)
    z = z / z.std()
    return np.clip(p + sd * z, 0.02, 0.98)


def p_losing_schedule(pp):
    """1試合ごとに勝率の違う n 試合で、勝ち数 < 負け数 になる確率（足し上げで正確に計算）"""
    f = np.array([1.0])
    for q in pp:
        f = np.convolve(f, [1 - q, q])
    n = len(pp)
    return float(sum(f[k] for k in range(n + 1) if k < n - k))


def sim_momentum(rng, p, n, reps, d=0.10):
    """勝った次の試合は勝率 p+d、負けた次は全体の勝率が p になるように下げる（勢いがあると置く）"""
    p_ww = p + d
    p_lw = p * (1 - p_ww) / (1 - p)  # 定常の勝率が p になる値
    w = np.zeros((reps, n), bool)
    w[:, 0] = rng.random(reps) < p
    for j in range(1, n):
        pj = np.where(w[:, j - 1], p_ww, p_lw)
        w[:, j] = rng.random(reps) < pj
    return w, p_lw


def main():
    t0 = time.time()
    P, N = 0.6, 10

    # 1) 勝率6割・10試合の勝ち数の分布（式と乱数）
    exact = {k: comb(N, k) * P ** k * (1 - P) ** (N - k) for k in range(N + 1)}
    w = sim_basic(rng, P, N, N_SIM).sum(1)
    sim = {k: float((w == k).mean()) for k in range(N + 1)}
    dist = pd.DataFrame({"wins": list(exact), "exact": list(exact.values()), "sim": list(sim.values())})
    dist.round(4).to_csv(RES / "wins_dist_p60_n10.csv", index=False)
    base = {"p_losing_exact": round(p_losing_exact(P, N), 4), "p_even_exact": round(p_even_exact(P, N), 4),
            "p_winning_exact": round(1 - p_losing_exact(P, N) - p_even_exact(P, N), 4),
            "p_losing_sim": round(float((w < N - w).mean()), 4), "p_even_sim": round(float((w == N - w).mean()), 4),
            "p_le3_wins_exact": round(sum(exact[k] for k in range(4)), 4),
            "p_ge8_wins_exact": round(sum(exact[k] for k in range(8, 11)), 4),
            "p_exactly6_exact": round(exact[6], 4),
            "p_losing_or_even_exact": round(p_losing_exact(P, N) + p_even_exact(P, N), 4)}

    # 1回分の 1,000シーズン（data）
    one = rng.random((1000, N)) < P
    dd = pd.DataFrame(one.astype(int), columns=[f"g{i}" for i in range(1, N + 1)])
    dd.insert(0, "season_id", np.arange(1, 1001))
    dd["wins"] = one.sum(1); dd["losses"] = N - dd["wins"]
    dd.to_csv(DATA / "seasons_p60_10games.csv", index=False)
    base["one_draw_1000_losing"] = int((dd.wins < dd.losses).sum())
    base["one_draw_1000_even"] = int((dd.wins == dd.losses).sum())

    # 2) 試合数×本当の勝率ごとの負け越す確率（式）
    ps = [0.55, 0.6, 0.65, 0.7]
    ns = [10, 20, 40, 80, 140]
    tab = pd.DataFrame([{"games": n, **{f"p{int(p*100)}": round(p_losing_exact(p, n), 4) for p in ps}} for n in ns])
    tab.to_csv(RES / "p_losing_by_games.csv", index=False)
    even = pd.DataFrame([{"games": n, **{f"p{int(p*100)}": round(p_even_exact(p, n), 4) for p in ps}} for n in ns])

    # 負け越す確率が5%・1%を下回る最少の試合数（偶数の試合数で見る）
    need = {}
    for p in ps:
        row = {}
        for th in [0.05, 0.01]:
            n = 2
            while p_losing_exact(p, n) > th or p_losing_exact(p, n + 2) > th:
                n += 2
            row[str(th)] = n
        need[str(p)] = row

    # 3) 140試合のシーズンの中で、10試合で負け越す区間はどれくらい来るか（乱数）
    S = 20000
    season = rng.random((S, 140)) < P
    blocks = season.reshape(S, 14, 10).sum(2)
    cs = np.concatenate([np.zeros((S, 1), int), season.cumsum(1)], 1)
    win10 = cs[:, 10:] - cs[:, :-10]  # 連続する10試合（131区間）
    in_season = {"blocks_losing_mean": round(float((blocks < 5).sum(1).mean()), 3),
                 "p_any_block_losing": round(float(((blocks < 5).sum(1) > 0).mean()), 4),
                 "p_any_sliding10_losing": round(float(((win10 < 5).sum(1) > 0).mean()), 4),
                 "p_any_sliding10_le3": round(float(((win10 <= 3).sum(1) > 0).mean()), 4),
                 "season_losing_140": round(float((season.sum(1) < 70).mean()), 4)}

    # 4) 確かめ：置き方を変える（10試合、乱数 200,000 回）
    rob = []
    rob.append({"case": "基本（毎試合 勝率0.6）", "p_losing": base["p_losing_exact"]})
    wv, lv = sim_draws(rng, P, N, N_SIM, 0.10)
    rob.append({"case": "引き分け1割（決着した試合の勝率0.6）", "p_losing": round(float((wv < lv).mean()), 4)})
    wv, lv = sim_draws(rng, P, N, N_SIM, 0.20)
    rob.append({"case": "引き分け2割（決着した試合の勝率0.6）", "p_losing": round(float((wv < lv).mean()), 4)})
    for sd in [0.10, 0.20]:
        pp = schedule_probs(P, N, sd)
        rob.append({"case": f"相手ごとに勝率が違う（平均0.6・{pp.min():.2f}〜{pp.max():.2f}）",
                    "p_losing": round(p_losing_schedule(pp), 4)})
    for d in [0.10, 0.20]:
        wm, plw = sim_momentum(rng, P, N, N_SIM, d)
        wm = wm.sum(1)
        rob.append({"case": f"勢いあり（勝った次は{P+d:.1f}、負けた次は{plw:.2f}）",
                    "p_losing": round(float((wm < N - wm).mean()), 4)})
    for p in [0.55, 0.65]:
        rob.append({"case": f"本当の勝率を{p}にする", "p_losing": round(p_losing_exact(p, N), 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_10games.csv", index=False)

    out = {"p60_n10": base, "p_losing_by_games": tab.to_dict("records"), "p_even_by_games": even.to_dict("records"),
           "games_needed_even_n": need, "season140_p60": in_season, "robustness_10games": rob.to_dict("records")}
    json.dump(out, open(RES / "a825_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：10試合の勝ち数の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    col = [ORANGE if k < 5 else (GRAY if k == 5 else BLUE) for k in dist.wins]
    ax.bar(dist.wins, dist.exact * 100, color=col, width=.75)
    ax.plot(dist.wins, dist.sim * 100, "o", color=INK, ms=4, label="乱数20万回")
    for k, v in zip(dist.wins, dist.exact * 100):
        ax.text(k, v + .5, f"{v:.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(range(11)); ax.set_xlabel("10試合の勝ち数"); ax.set_ylabel("確率（%）")
    ax.text(1.6, 22, f"負け越し（4勝以下）\n{base['p_losing_exact']*100:.1f}%", color=ORANGE, fontsize=10, ha="center")
    ax.text(5, 27.5, f"五分 {base['p_even_exact']*100:.1f}%", color=INK, fontsize=10, ha="center")
    ax.text(8.6, 22, f"勝ち越し（6勝以上）\n{base['p_winning_exact']*100:.1f}%", color=BLUE, fontsize=10, ha="center")
    ax.set_ylim(0, 31); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("本当の勝率6割のチームでも、10試合で負け越すことは6回に1回ある")
    save(fig, "a825_wins_dist.png", SRC + "。棒は二項分布の式、点は乱数")

    # 図2：試合数と負け越す確率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    nn = np.arange(10, 142, 2)
    for p, c in zip(ps, [LIGHT, BLUE, GREEN, INK]):
        ax.plot(nn, [p_losing_exact(p, n) * 100 for n in nn], color=c, lw=2, label=f"本当の勝率{p}")
    ax.axhline(5, color=ORANGE, lw=1, ls="--"); ax.text(142, 5.6, "5%", color=ORANGE, fontsize=9, ha="right")
    ax.set_xlabel("試合数（偶数の試合数で計算）"); ax.set_ylabel("負け越す確率（%）")
    ax.set_xlim(8, 142); ax.set_ylim(0, 36); ax.legend(frameon=False, fontsize=9)
    ax.set_title("負け越す確率は、試合数が増えるほど下がる（二項分布の式）")
    save(fig, "a825_by_games.png", SRC)

    # 図3：置き方を変えた確かめ
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    r = rob.iloc[::-1]
    cc = [ORANGE if c.startswith("基本") else (LIGHT if c.startswith("本当") else BLUE) for c in r.case]
    ax.barh(r.case, r.p_losing * 100, color=cc)
    for i, v in enumerate(r.p_losing * 100):
        ax.text(v + .4, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("10試合で負け越す確率（%）"); ax.set_xlim(0, 32)
    ax.set_title("置き方を変えると、10試合で負け越す確率は1割から3割近くまで動く")
    save(fig, "a825_robust.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
