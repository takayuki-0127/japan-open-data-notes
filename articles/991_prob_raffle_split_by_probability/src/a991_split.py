"""991 くじの当たりを「確率で山分け」すると、何がずれるのか？（架空のデータ）

架空の社内イベントのくじ。くじは100枚、当たりは10本（当たり1本＝景品1個、引いたくじは戻さない）。
4人の仲間（1枚・4枚・15枚・30枚、合わせて50枚）が、当たった景品を持ち寄って「確率で」分けると決めた。
「確率」を (a) 当たる本数の見込み（枚数の割合）、(b) 少なくとも1本当たる確率、(c) 1枚あたりの当たる確率
のどれと読むかで、1人あたりの取り分の見込みがどれだけずれるかを、式と乱数の両方で数える。
"""
import json
import time
from math import comb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 991
SRC = "架空の社内イベントのくじ（作成者が乱数で作成、seed 991）"
N_TICKET = 100
PRIZE = 10
NAMES = ["Aさん", "Bさん", "Cさん", "Dさん"]
HOLD = np.array([1, 4, 15, 30])
HOLD2 = np.array([5, 10, 15, 20])        # 確かめ：持つ枚数の差が小さい仲間
RULES = ["(a) 本数の見込みの割合", "(b) 少なくとも1本の確率の割合", "(c) 1枚あたりの確率（均等）"]
N_SIM = 200000


def exact(hold, prize, n=N_TICKET):
    """式：本数の見込み・少なくとも1本当たる確率・3つの分け方の取り分の見込み"""
    e = hold * prize / n
    q = np.array([1 - comb(n - h, prize) / comb(n, prize) for h in hold])
    per_ticket = np.full(len(hold), prize / n)      # 1枚あたりの当たる確率（誰でも同じ）
    pool = e.sum()                                  # 仲間で持ち寄る本数の見込み
    shares = {RULES[0]: hold / hold.sum(), RULES[1]: q / q.sum(), RULES[2]: per_ticket / per_ticket.sum()}
    take = {k: v * pool for k, v in shares.items()}
    return e, q, pool, shares, take


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    owner = np.repeat(np.arange(len(HOLD) + 1), list(HOLD) + [N_TICKET - HOLD.sum()])   # 4 はほかの人

    # 1) 乱数：くじを20万回引く（当たり10本を、100枚から戻さずに選ぶ）
    wins = np.zeros((N_SIM, len(HOLD)), dtype=int)
    for r in range(N_SIM):
        w = owner[rng.choice(N_TICKET, PRIZE, replace=False)]
        wins[r] = np.bincount(w, minlength=len(HOLD) + 1)[:len(HOLD)]
    pool_sim = wins.sum(1)

    e, q, pool, shares, take = exact(HOLD, PRIZE)
    base = []
    for i, nm in enumerate(NAMES):
        row = {"person": nm, "tickets": int(HOLD[i]),
               "own_expected": round(float(e[i]), 4), "own_expected_sim": round(float(wins[:, i].mean()), 4),
               "p_at_least_one": round(float(q[i]) * 100, 2), "p_at_least_one_sim": round(float((wins[:, i] >= 1).mean()) * 100, 2),
               "p_zero_alone": round(float((wins[:, i] == 0).mean()) * 100, 2)}
        for k in RULES:
            tk = take[k][i]
            sim_take = float((shares[k][i] * pool_sim).mean())
            row[f"share_{k[:3]}"] = round(float(shares[k][i]) * 100, 2)
            row[f"take_{k[:3]}"] = round(float(tk), 4)
            row[f"take_sim_{k[:3]}"] = round(sim_take, 4)
            row[f"gap_pct_{k[:3]}"] = round(float((tk - e[i]) / e[i]) * 100, 2)
        base.append(row)
    base = pd.DataFrame(base)
    base.to_csv(RES / "split_base.csv", index=False)
    p_pool_zero = comb(N_TICKET - HOLD.sum(), PRIZE) / comb(N_TICKET, PRIZE)

    # 2) 確かめ：当たりの本数と、持つ枚数の組を変える（式）
    grid = []
    for hname, hold in [("1・4・15・30枚", HOLD), ("5・10・15・20枚", HOLD2)]:
        for prize in [1, 3, 5, 10, 20, 30, 50]:
            e2, q2, pool2, sh2, tk2 = exact(hold, prize)
            for i in [0, len(hold) - 1]:
                grid.append({"holding": hname, "prizes": prize, "person": NAMES[i], "tickets": int(hold[i]),
                             "own_expected": round(float(e2[i]), 4), "p_at_least_one": round(float(q2[i]) * 100, 2),
                             "take_b": round(float(tk2[RULES[1]][i]), 4),
                             "gap_pct_b": round(float((tk2[RULES[1]][i] - e2[i]) / e2[i]) * 100, 2) + 0.0,
                             "gap_pct_c": round(float((tk2[RULES[2]][i] - e2[i]) / e2[i]) * 100, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "by_prizes.csv", index=False)
    gb = grid[grid.prizes > 1]

    # データ：最初の1,000回の当たり本数
    d = pd.DataFrame(wins[:1000], columns=[f"wins_{c}" for c in ["A", "B", "C", "D"]])
    d.insert(0, "draw", np.arange(1, 1001))
    d["pool"] = d.iloc[:, 1:5].sum(1)
    d.to_csv(DATA / "draws_first1000.csv", index=False)
    pd.DataFrame({"person": NAMES + ["ほかの人"], "tickets": list(HOLD) + [int(N_TICKET - HOLD.sum())]}).to_csv(
        DATA / "holders.csv", index=False)

    out = {"setting": {"tickets": N_TICKET, "prizes": PRIZE, "holdings": HOLD.tolist(), "draws": N_SIM},
           "pool_expected": round(float(pool), 4), "pool_expected_sim": round(float(pool_sim.mean()), 4),
           "p_pool_zero_pct": round(p_pool_zero * 100, 4), "p_pool_zero_sim_pct": round(float((pool_sim == 0).mean()) * 100, 4),
           "max_abs_diff_exact_sim": {
               "own_expected": round(float((base.own_expected - base.own_expected_sim).abs().max()), 4),
               "p_at_least_one_pct": round(float((base.p_at_least_one - base.p_at_least_one_sim).abs().max()), 2),
               "take": round(float(max((base[f"take_{k[:3]}"] - base[f"take_sim_{k[:3]}"]).abs().max() for k in RULES)), 4)},
           "ratio_p_at_least_one_D_over_A": round(float(q[3] / q[0]), 2), "ratio_tickets_D_over_A": int(HOLD[3] / HOLD[0]),
           "take_sum_by_rule": {k: round(float(take[k].sum()), 4) for k in RULES},
           "base": base.to_dict("records"),
           "range_gap_b_largest_holder": {h: [float(g[g.person == "Dさん"].gap_pct_b.min()), float(g[g.person == "Dさん"].gap_pct_b.max())]
                                          for h, g in gb.groupby("holding")},
           "range_gap_b_smallest_holder": {h: [float(g[g.person == "Aさん"].gap_pct_b.min()), float(g[g.person == "Aさん"].gap_pct_b.max())]
                                           for h, g in gb.groupby("holding")},
           "prize1_gap_b_max_abs": float(grid[grid.prizes == 1].gap_pct_b.abs().max()),
           "grid_cases": int(len(grid) // 2), "data_draws_saved": 1000,
           "grid": grid.to_dict("records")}
    json.dump(out, open(RES / "a991_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：持ち寄らないときの見込みと、3つの分け方の取り分の見込み
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(NAMES)); bw = 0.2
    cols = [GRAY, BLUE, ORANGE, GREEN]
    series = [("自分のくじの当たり本数の見込み", base.own_expected)] + [(k, base[f"take_{k[:3]}"]) for k in RULES]
    for j, (lab, v) in enumerate(series):
        ax.bar(x + (j - 1.5) * bw, v, bw, color=cols[j], label=lab)
        for i, vv in enumerate(v):
            ax.text(i + (j - 1.5) * bw, vv + 0.05, f"{vv:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{n}（{h}枚）" for n, h in zip(NAMES, HOLD)])
    ax.set_ylabel("景品の個数（見込み）"); ax.set_ylim(0, 3.6)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("「確率で山分け」の読み方で、取り分の見込みが変わる（100枚・当たり10本）", fontsize=12)
    save(fig, "a991_take.png", SRC)

    # 図2：当たりの本数を変えたとき、(b) の取り分が自分の見込みから何%ずれるか
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (h, nm), c, ls in [(("1・4・15・30枚", "Dさん"), ORANGE, "-"), (("1・4・15・30枚", "Aさん"), BLUE, "-"),
                           (("5・10・15・20枚", "Dさん"), ORANGE, "--"), (("5・10・15・20枚", "Aさん"), BLUE, "--")]:
        g = grid[(grid.holding == h) & (grid.person == nm)]
        tk = int(g.tickets.iloc[0])
        ax.plot(g.prizes, g.gap_pct_b, ls, marker="o", ms=4, color=c, label=f"{h}の組の{tk}枚の人")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xlabel("100枚の中の当たりの本数"); ax.set_ylabel("自分の見込みからのずれ（%）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("(b) 少なくとも1本の確率で分けたときのずれ。当たり1本なら0", fontsize=12)
    save(fig, "a991_by_prizes.png", SRC)

    # 図3：景品が0個になる割合（持ち寄らない・持ち寄る）
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    v = base.p_zero_alone.values
    ax.barh(np.arange(4)[::-1] + 0.18, v, 0.36, color=GRAY, label="持ち寄らない（自分のくじだけ）")
    ax.barh(np.arange(4)[::-1] - 0.18, [out["p_pool_zero_sim_pct"]] * 4, 0.36, color=BLUE, label="持ち寄って分ける")
    for i, vv in enumerate(v):
        ax.text(vv + 1, 3 - i + 0.18, f"{vv:.1f}%", va="center", fontsize=8.5)
        ax.text(1, 3 - i - 0.18, f"{out['p_pool_zero_sim_pct']:.2f}%", va="center", fontsize=8.5)
    ax.set_yticks(np.arange(4)[::-1]); ax.set_yticklabels([f"{n}（{h}枚）" for n, h in zip(NAMES, HOLD)])
    ax.set_xlabel("景品が0個になる割合（%、20万回）"); ax.set_xlim(0, 105)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("持ち寄ると、景品が0個の人はほぼいなくなる", fontsize=12)
    save(fig, "a991_zero.png", SRC)

    print(json.dumps({k: out[k] for k in out if k != "grid"}, ensure_ascii=False, indent=1), round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
