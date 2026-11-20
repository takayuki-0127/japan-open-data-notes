"""828 ガチャの「1%」を100回引いても当たらない人は、何%いるのか？（架空のデータ）

架空のゲームの架空のプレイヤー10万人。1回引くごとに当たりの確率は1%で、前の結果とは関係なく決まる（毎回1%）。
1人ずつ、最初に当たったのが何回目かと、100回のうち何回当たったかを数える。
確率の数え方だけを扱い、引くことをすすめたり、すすめなかったりする助言はしない。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 828
SRC = "架空のプレイヤーのくじ引き（作成者が乱数で作成、seed 828）"
rng = np.random.default_rng(SEED)
N_PLAYER = 100_000
P = 0.01
N_DRAW = 100


def first_hit(rng, n, p):
    """毎回 p で当たるとき、最初に当たったのが何回目か（幾何分布）"""
    return rng.geometric(p, n)


def box_first_hit(rng, n, size=100):
    """100個に1個の当たりが入った箱から、戻さずに引くとき（当たりの位置は1〜100で一様）"""
    return rng.integers(1, size + 1, n)


def main():
    # 1人100回ずつ実際に引く。100回で当たらなかった人は、その先も毎回1%で引き続けたとして最初の当たりを数える
    draws = rng.random((N_PLAYER, N_DRAW)) < P
    hits100 = draws.sum(1)
    fh = np.where(hits100 > 0, draws.argmax(1) + 1, 0)
    rest = hits100 == 0
    fh[rest] = N_DRAW + first_hit(rng, int(rest.sum()), P)
    df = pd.DataFrame({"player_id": np.arange(1, N_PLAYER + 1), "first_hit": fh, "hits_in_100": hits100})
    df.to_csv(DATA / "players.csv", index=False)

    # 1) 100回引いて1回も当たらない人
    miss_sim = float((fh > N_DRAW).mean())
    miss_exact = (1 - P) ** N_DRAW
    hits_dist = {str(k): round(float((hits100 == k).mean()), 4) for k in range(4)}
    hits_dist["4以上"] = round(float((hits100 >= 4).mean()), 4)
    hits_dist["2以上"] = round(float((hits100 >= 2).mean()), 4)
    from math import comb
    hits_exact = {str(k): round(comb(N_DRAW, k) * P ** k * (1 - P) ** (N_DRAW - k), 4) for k in range(4)}
    hits_exact["4以上"] = round(1 - sum(comb(N_DRAW, k) * P ** k * (1 - P) ** (N_DRAW - k) for k in range(4)), 4)

    # 2) 何回引けば、何%の人が当たるか
    need = []
    for q in [0.5, 0.632, 0.9, 0.95, 0.99]:
        exact = int(np.ceil(np.log(1 - q) / np.log(1 - P)))
        need.append({"share_hit": q, "draws_exact": exact, "draws_sim": int(np.quantile(fh, q, method="inverted_cdf"))})
    pd.DataFrame(need).to_csv(RES / "draws_needed.csv", index=False)
    fh_stats = {"mean": round(float(fh.mean()), 1), "median": int(np.median(fh)),
                "share_hit_by_1": round(float((fh <= 1).mean()), 4), "share_after_300": round(float((fh > 300).mean()), 4),
                "max": int(fh.max())}

    # 3) 外れが続いた人は、次の100回で当たりやすいか
    after = []
    for k in [0, 50, 100, 200, 300]:
        g = fh[fh > k]
        after.append({"missed_so_far": k, "players": int(len(g)),
                      "hit_next_100": round(float((g <= k + 100).mean()), 4),
                      "hit_next_10": round(float((g <= k + 10).mean()), 4)})

    # 4) 1万人ずつ10組に分けると、当たらない人の割合はどれだけ振れるか
    groups = [round(float((fh[i * 10000:(i + 1) * 10000] > N_DRAW).mean()), 4) for i in range(10)]

    # 5) 確かめ：確率と回数を変える（毎回の確率）・箱から戻さずに引く場合
    grid = []
    for p in [0.005, 0.01, 0.02, 0.03]:
        for n in [10, 50, 100, 200, 300]:
            sim = float((first_hit(np.random.default_rng(SEED + int(p * 1000) * 1000 + n), 100_000, p) > n).mean())
            grid.append({"p": p, "draws": n, "miss_sim": round(sim, 4), "miss_exact": round((1 - p) ** n, 4),
                         "exp_minus_np": round(float(np.exp(-p * n)), 4)})
    pd.DataFrame(grid).to_csv(RES / "miss_by_p_and_draws.csv", index=False)
    bfh = box_first_hit(rng, N_PLAYER)
    box = {"miss_50": round(float((bfh > 50).mean()), 4), "miss_100": round(float((bfh > 100).mean()), 4),
           "mean_first_hit": round(float(bfh.mean()), 1)}

    out = {"players": N_PLAYER, "p": P, "draws": N_DRAW,
           "miss_100": {"sim": round(miss_sim, 4), "exact": round(miss_exact, 4)},
           "hits_in_100": {"sim": hits_dist, "exact": hits_exact, "mean_sim": round(float(hits100.mean()), 3)},
           "first_hit": fh_stats, "draws_needed": need, "after_misses": after,
           "miss_100_by_group_of_10000": {"values": groups, "min": min(groups), "max": max(groups)},
           "box_100_without_replacement": box,
           "sensitivity_grid": grid}
    json.dump(out, open(RES / "a828_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：最初に当たったのは何回目か
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(0, 601, 10)
    cnt, _ = np.histogram(fh, bins=bins)
    col = [BLUE if b < N_DRAW else ORANGE for b in bins[:-1]]
    ax.bar(bins[:-1], cnt / N_PLAYER * 100, width=10, align="edge", color=col, lw=0)
    for v, lab in [(need[0]["draws_exact"], "半分の人が当たる"), (need[2]["draws_exact"], "9割の人が当たる"),
                   (need[4]["draws_exact"], "99%の人が当たる")]:
        ax.axvline(v, color=GRAY, lw=1, ls="--")
        ax.text(v + 4, ax.get_ylim()[1] * 0.92, f"{lab}\n{v}回", fontsize=8.5, color=INK, va="top")
    ax.text(140, ax.get_ylim()[1] * 0.45, f"100回で当たらない人（オレンジ）\n{miss_sim*100:.1f}%", color=ORANGE, fontsize=10)
    ax.set_xlabel("最初に当たったのは何回目か（10回ずつの区切り）"); ax.set_ylabel("プレイヤーの割合（%）")
    ax.set_xlim(0, 600)
    ax.set_title("毎回1%のくじで、最初に当たるまでの回数（架空のプレイヤー10万人）")
    save(fig, "a828_first_hit.png", SRC)

    # 図2：何回引いても当たらない人の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(0, 501)
    for p, c in [(0.005, LIGHT), (0.01, BLUE), (0.02, GREEN), (0.03, GRAY)]:
        ax.plot(x, (1 - p) ** x * 100, color=c, lw=2 if p == 0.01 else 1.4, label=f"毎回{p*100:g}%")
    ax.plot([0, 100, 100, 500], [100, 0, 0, 0], color=ORANGE, lw=1.6, ls="--", label="100個に1個の箱から戻さずに引く")
    ax.scatter([100], [miss_exact * 100], color=BLUE, zorder=3)
    ax.text(105, miss_exact * 100 + 3, f"毎回1%・100回で{miss_exact*100:.1f}%", fontsize=9, color=BLUE)
    ax.set_xlabel("引いた回数"); ax.set_ylabel("1回も当たっていない人の割合（%）"); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("同じ「1%」でも、引き方の決まりで当たらない人の割合は変わる")
    save(fig, "a828_miss_curve.png", SRC)

    # 図3：外れが続いた人が、次の100回で当たる割合
    a = pd.DataFrame(after)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.bar([f"{k}回\n外れたあと" if k else "はじめから" for k in a.missed_so_far], a.hit_next_100 * 100, color=BLUE)
    for i, v in enumerate(a.hit_next_100 * 100):
        ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 100); ax.set_ylabel("次の100回で当たる割合（%）")
    ax.set_title("外れが続いても、次に当たりやすくはならない（毎回1%のとき）")
    save(fig, "a828_after_miss.png", SRC, y=-0.06)
    print(json.dumps({k: out[k] for k in ["miss_100", "hits_in_100", "first_hit", "draws_needed", "after_misses",
                                          "miss_100_by_group_of_10000", "box_100_without_replacement"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
