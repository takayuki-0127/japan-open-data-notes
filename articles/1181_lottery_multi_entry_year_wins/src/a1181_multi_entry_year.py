"""1181 何口も申し込める人と1口だけの人では、1年で当たる回数の差はどれだけ開くのか？（架空のデータ）

架空の工房の体験会の抽選を、毎月1回・1年で12回行う。毎回、同じ会員3,000人が申し込み、枠は200人。
会員の区分で申し込める口の数が違う決まりを置く（基本：8割が1口、2割が5口）。
抽選は口を1つずつ引き、すでに当たった人の口は飛ばす（1回の抽選で1人1枠まで）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1181
SRC = "架空の体験会の抽選1年分（作成者が置いた会員・口の数・枠からの乱数、seed 1181）"
N_PEOPLE = 3000
ROUNDS = 12
REPS = 400
REPS_GRID = 150


def draw_year(rng, tickets, seats, reps):
    """reps 年分。口の数に比べた重みで、1回あたり seats 人を重ならないように選ぶ（口を1つずつ引いて当たった人を飛ばすのと同じ）。
    返り値：reps×人数 の1年の当たり回数"""
    n = len(tickets)
    wins = np.zeros((reps, n), dtype=np.int16)
    for _ in range(ROUNDS):
        key = np.log(rng.random((reps, n))) / tickets[None, :]  # 大きいほど先に引かれる
        idx = np.argpartition(-key, seats - 1, axis=1)[:, :seats]
        np.add.at(wins, (np.repeat(np.arange(reps), seats), idx.ravel()), 1)
    return wins


def summarize(wins, tickets, k):
    one, many = wins[:, tickets == 1], wins[:, tickets == k]
    m1, mk = float(one.mean()), float(many.mean())
    p1, pk = m1 / ROUNDS, mk / ROUNDS
    # 1口の人と k口の人を1組ずつでたらめに組んだとき、1口の人のほうが多く当たる・同じ割合
    i = np.arange(min(one.shape[1], many.shape[1]))
    a, b = one[:, i], many[:, i]
    tot = wins.sum(1, keepdims=True)
    share_wins_many = float((many.sum(1) / tot[:, 0]).mean())
    return {"mean_wins_1": round(m1, 4), "mean_wins_k": round(mk, 4), "ratio_mean": round(mk / m1, 3),
            "per_round_p1_pct": round(p1 * 100, 3), "per_round_pk_pct": round(pk * 100, 3),
            "zero_1_pct": round(float((one == 0).mean() * 100), 2), "zero_k_pct": round(float((many == 0).mean() * 100), 2),
            "zero_1_formula_pct": round((1 - p1) ** ROUNDS * 100, 2), "zero_k_formula_pct": round((1 - pk) ** ROUNDS * 100, 2),
            "ge3_1_pct": round(float((one >= 3).mean() * 100), 2), "ge3_k_pct": round(float((many >= 3).mean() * 100), 2),
            "pair_1_more_pct": round(float((a > b).mean() * 100), 2), "pair_same_pct": round(float((a == b).mean() * 100), 2),
            "share_people_k_pct": round(float((tickets == k).mean() * 100), 2),
            "share_wins_k_pct": round(share_wins_many * 100, 2),
            "gap_mean": round(mk - m1, 4)}


def main():
    rng = np.random.default_rng(SEED)
    k, share = 5, 0.2
    tickets = np.where(np.arange(N_PEOPLE) < int(N_PEOPLE * share), k, 1).astype(float)
    wins = draw_year(rng, tickets, 200, REPS)
    base = summarize(wins, tickets, k)
    base["per_round_ratio"] = round(base["per_round_pk_pct"] / base["per_round_p1_pct"], 3)
    base["ratio_of_tickets"] = k
    # 1年の当たり回数の分布
    dist = []
    for lab, sel in [("1口", tickets == 1), (f"{k}口", tickets == k)]:
        w = wins[:, sel].ravel()
        for c in range(0, 8):
            dist.append({"group": lab, "wins": c, "share_pct": round(float((w == c).mean() * 100), 3)})
    dist = pd.DataFrame(dist); dist.to_csv(RES / "wins_distribution_base.csv", index=False)
    one_year = pd.DataFrame({"person_id": np.arange(1, N_PEOPLE + 1), "tickets": tickets.astype(int), "wins_in_year": wins[0]})
    one_year.to_csv(DATA / "one_year_wins.csv", index=False)

    # 口の数ごと（同じ人数で、2割の人の口の数だけ 1〜10 に変える）
    by_k = []
    for kk in [1, 2, 3, 5, 10]:
        t = np.where(np.arange(N_PEOPLE) < int(N_PEOPLE * share), kk, 1).astype(float)
        w = draw_year(np.random.default_rng(SEED * 10 + kk), t, 200, REPS_GRID)
        s = summarize(w, t, kk) if kk > 1 else None
        if kk == 1:
            m = float(w.mean()); s = {"mean_wins_1": round(m, 4), "mean_wins_k": round(m, 4), "ratio_mean": 1.0,
                                      "zero_1_pct": round(float((w == 0).mean() * 100), 2), "zero_k_pct": round(float((w == 0).mean() * 100), 2)}
        by_k.append({"k": kk, **{x: s[x] for x in ["mean_wins_1", "mean_wins_k", "ratio_mean", "zero_1_pct", "zero_k_pct"]}})
    by_k = pd.DataFrame(by_k); by_k.to_csv(RES / "by_k.csv", index=False)

    # 確かめ：人数あたりの倍率（枠に対する人数）×口の多い人の割合×口の数 の27通り
    rows = []
    for seats in [400, 200, 100]:
        for sh in [0.05, 0.2, 0.4]:
            for kk in [3, 5, 10]:
                t = np.where(np.arange(N_PEOPLE) < int(N_PEOPLE * sh), kk, 1).astype(float)
                w = draw_year(np.random.default_rng(SEED * 100 + seats + int(sh * 100) * 7 + kk), t, seats, REPS_GRID)
                s = summarize(w, t, kk)
                rows.append({"seats": seats, "people_per_seat": N_PEOPLE / seats, "share_k": sh, "k": kk,
                             **{x: s[x] for x in ["mean_wins_1", "mean_wins_k", "ratio_mean", "zero_1_pct", "zero_k_pct",
                                                  "zero_1_formula_pct", "zero_k_formula_pct", "pair_1_more_pct",
                                                  "share_people_k_pct", "share_wins_k_pct"]}})
    grid = pd.DataFrame(rows); grid.to_csv(RES / "grid.csv", index=False)
    gs = {"ratio_mean_range": [float(grid.ratio_mean.min()), float(grid.ratio_mean.max())],
          "ratio_below_k_count": int((grid.ratio_mean < grid.k).sum()),
          "zero_1_range": [float(grid.zero_1_pct.min()), float(grid.zero_1_pct.max())],
          "zero_k_range": [float(grid.zero_k_pct.min()), float(grid.zero_k_pct.max())],
          "pair_1_more_range": [float(grid.pair_1_more_pct.min()), float(grid.pair_1_more_pct.max())],
          "zero_formula_max_abs_diff": round(float(max((grid.zero_1_pct - grid.zero_1_formula_pct).abs().max(),
                                                       (grid.zero_k_pct - grid.zero_k_formula_pct).abs().max())), 3),
          "by_seats": {str(s): {"ratio_mean_range": [float(g.ratio_mean.min()), float(g.ratio_mean.max())],
                                "zero_1_range": [float(g.zero_1_pct.min()), float(g.zero_1_pct.max())],
                                "zero_k_range": [float(g.zero_k_pct.min()), float(g.zero_k_pct.max())]}
                       for s, g in grid.groupby("seats", sort=False)}}
    out = {"setup": {"people": N_PEOPLE, "rounds_per_year": ROUNDS, "seats_base": 200, "share_k_base": share, "k_base": k,
                     "people_per_seat_base": N_PEOPLE / 200, "tickets_per_seat_base": float(tickets.sum() / 200),
                     "reps": REPS, "reps_grid": REPS_GRID},
           "base": base, "by_k": by_k.to_dict("records"), "grid_summary": gs}
    json.dump(out, open(RES / "a1181_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1年で当たる回数の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(8); w_ = .38
    d1 = dist[dist.group == "1口"].share_pct.values; dk = dist[dist.group == f"{k}口"].share_pct.values
    ax.bar(x - w_ / 2, d1, w_, color=LIGHT, label="1口の人")
    ax.bar(x + w_ / 2, dk, w_, color=BLUE, label=f"{k}口の人")
    for xi, v in zip(x, d1):
        if v >= 1: ax.text(xi - w_ / 2, v + 1, f"{v:.1f}", ha="center", fontsize=8)
    for xi, v in zip(x, dk):
        if v >= 1: ax.text(xi + w_ / 2, v + 1, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x, [f"{i}回" for i in x]); ax.set_ylim(0, 75)
    ax.set_xlabel("1年（12回）で当たった回数"); ax.set_ylabel("人の割合（%）")
    ax.legend(frameon=False)
    ax.set_title(f"1口の人の{base['zero_1_pct']:.1f}%は1年で1回も当たらない（{k}口は{base['zero_k_pct']:.1f}%）")
    save(fig, "a1181_year_dist.png", SRC + f"。会員3,000人・枠200人・2割が{k}口、{REPS}年分")

    # 図2：口の数ごとの1年の平均の当たり回数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    xs = np.arange(len(by_k))
    ax.bar(xs - .2, by_k.mean_wins_1, .4, color=LIGHT, label="1口の人（8割）")
    ax.bar(xs + .2, by_k.mean_wins_k, .4, color=BLUE, label="口の多い人（2割）")
    for xi, a_, b_, r_ in zip(xs, by_k.mean_wins_1, by_k.mean_wins_k, by_k.ratio_mean):
        ax.text(xi + .2, b_ + .05, f"{r_:.2f}倍", ha="center", fontsize=8.5)
    ax.set_xticks(xs, [f"{kk}口" for kk in by_k.k]); ax.set_ylim(0, None)
    ax.set_xlabel("2割の人が申し込める口の数"); ax.set_ylabel("1年の平均の当たり回数（回）")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("口の数を増やすと、1口の人の当たりが減り、比は口の数より少し小さい")
    save(fig, "a1181_by_k.png", SRC + f"。各{REPS_GRID}年分、数字は口の多い人÷1口の人")

    # 図3：27通りの平均の比と口の数
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for s, col, mk in [(400, LIGHT, "o"), (200, BLUE, "s"), (100, INK, "^")]:
        g = grid[grid.seats == s]
        ax.scatter(g.k + {400: -.25, 200: 0, 100: .25}[s], g.ratio_mean, color=col, marker=mk, s=40, edgecolor=INK, lw=.4,
                   label=f"枠{s}人（人数の倍率{N_PEOPLE / s:.1f}倍）")
    ax.plot([0, 11], [0, 11], color=GRAY, ls="--", lw=1)
    ax.text(5.4, 9.6, "点線：口の数と同じ倍", color=GRAY, fontsize=8.5)
    ax.set_xticks([3, 5, 10]); ax.set_xlim(0, 11); ax.set_ylim(0, 11)
    ax.set_xlabel("口の多い人の口の数"); ax.set_ylabel("1年の当たり回数の比（口の多い人÷1口の人）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("27通り：枠が多いほど、比は口の数より小さくなる")
    save(fig, "a1181_robust.png", SRC + f"。口の多い人の割合5%・20%・40%を重ねて表示、各{REPS_GRID}年分")


if __name__ == "__main__":
    main()
