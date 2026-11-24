"""1173 「倍率10倍」の抽選で、1人が当たる見込みは本当に10分の1なのか？（架空のデータ）

作成者が置いた架空の講座の抽選。申し込んだ人は5,000人、1人が出す口の数は1〜5口（1口50%、2口25%、3口10%、4口5%、5口10%、
平均2口）で、口の合計は10,000口。当選の枠は1,000。「倍率」＝口の合計÷枠＝10倍。
3つの決まりで抽選する（口をでたらめに並べて上から取る）。
 ① 口ごと：当たった口はすべて有効（同じ人が2口当たれば2枠）
 ② 1人1枠・繰り上げ：同じ人の2口目以降の当たりは数えず、空いた枠は次の口に回す（当たる人はちょうど1,000人）
 ③ 1人1枠・繰り上げなし：同じ人の2口目以降の当たりは数えず、空いた枠はそのまま
(1) 口の数ごとの「1人が当たる見込み」を 4,000回くり返して数える（①は式でも出す）
(2) 申し込んだ人の割合と、当たった人の割合を口の数ごとに比べる
(3) 確かめ：口の数の分かれ方4通り×倍率3通り（3・10・30倍）の12通り（各1,000回、②の決まり）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1173
SRC = "架空の講座の抽選（作成者が置いた申し込みの口の数からの乱数、seed 1173）"
TOTAL_ENTRIES = 10_000
DISTS = {  # 口の数: 申し込んだ人に占める割合
    "全員1口": {1: 1.0},
    "少し多口": {1: 0.7, 2: 0.2, 3: 0.1},
    "基本": {1: 0.5, 2: 0.25, 3: 0.1, 4: 0.05, 5: 0.1},
    "10口の人も": {1: 0.6, 2: 0.2, 5: 0.1, 10: 0.1},
}
SEATS_BASE = 1000
R_BASE, R_GRID = 4000, 1000
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def make_people(dist):
    mean_k = sum(k * p for k, p in dist.items())
    n_people = int(round(TOTAL_ENTRIES / mean_k))
    ks = []
    for k, p in dist.items():
        ks += [k] * int(round(n_people * p))
    ks = np.array(ks)
    assert ks.sum() == TOTAL_ENTRIES, (ks.sum(), dist)
    return ks


def formula_rule1(k, M, W):
    """①：M 口から W 口を当てるとき、k 口の人が1口以上当たる確率（式）"""
    p_none = 1.0
    for i in range(k):
        p_none *= (M - W - i) / (M - i)
    return 1 - p_none


def simulate(rng, ks, W, R):
    """R 回抽選し、人ごとの ①の当たり口数の合計、①③で1口以上当たった回数、②で当たった回数を返す"""
    n = len(ks)
    owner = np.repeat(np.arange(n), ks)
    starts = np.concatenate([[0], np.cumsum(ks)[:-1]])
    wins1 = np.zeros(n)
    any1 = np.zeros(n)
    win2 = np.zeros(n)
    seats3 = []
    for _ in range(R):
        key = rng.random(len(owner))
        cut = np.partition(key, W - 1)[W - 1]
        hit = key <= cut
        c = np.bincount(owner[hit], minlength=n)
        wins1 += c
        any1 += c > 0
        seats3.append(int((c > 0).sum()))
        mk = np.minimum.reduceat(key, starts)
        cut2 = np.partition(mk, W - 1)[W - 1]
        win2 += mk <= cut2
    return wins1 / R, any1 / R, win2 / R, np.array(seats3)


def main():
    rng = np.random.default_rng(SEED)
    out = {}
    ks = make_people(DISTS["基本"])
    n_people, W, M = len(ks), SEATS_BASE, TOTAL_ENTRIES
    out["setting"] = {"people": n_people, "entries": M, "seats": W, "ratio_entries_per_seat": r(M / W, 2),
                      "ratio_people_per_seat": r(n_people / W, 2), "mean_entries_per_person": r(M / n_people, 2),
                      "dist": {str(k): p for k, p in DISTS["基本"].items()}, "reps": R_BASE}
    wins1, any1, win2, seats3 = simulate(rng, ks, W, R_BASE)
    rows = []
    for k in sorted(set(ks)):
        m = ks == k
        rows.append({"entries": int(k), "people": int(m.sum()), "people_share_pct": r(m.mean() * 100, 2),
                     "rule1_any_win_pct": r(any1[m].mean() * 100, 2),
                     "rule1_any_win_formula_pct": r(formula_rule1(int(k), M, W) * 100, 2),
                     "rule1_mean_seats": r(wins1[m].mean(), 4),
                     "rule2_win_pct": r(win2[m].mean() * 100, 2),
                     "rule2_winner_share_pct": r(win2[m].sum() / W * 100, 2),
                     "rule1_seat_share_pct": r(wins1[m].sum() / W * 100, 2)})
    byk = pd.DataFrame(rows)
    byk.to_csv(RES / "by_entries.csv", index=False)
    out["by_entries"] = rows
    out["rule1"] = {"person_avg_any_win_pct": r(any1.mean() * 100, 2),
                    "winners_people_mean": r(any1.sum(), 1),
                    "extra_seats_to_same_people_mean": r(wins1.sum() - any1.sum(), 1)}
    out["rule2"] = {"person_avg_win_pct": r(win2.mean() * 100, 2),
                    "person_avg_formula_pct": r(W / n_people * 100, 2),
                    "ratio_people_per_winner": r(n_people / W, 2)}
    out["rule3"] = {"seats_used_mean": r(seats3.mean(), 1), "seats_used_min": int(seats3.min()),
                    "seats_used_max": int(seats3.max()), "empty_seats_mean": r(W - seats3.mean(), 1),
                    "person_avg_win_pct": r(any1.mean() * 100, 2),
                    "ratio_people_per_winner": r(n_people / seats3.mean(), 2)}
    one = byk[byk.entries == 1].iloc[0]
    five = byk[byk.entries == 5].iloc[0]
    out["headline"] = {"one_entry_rule1_pct": one.rule1_any_win_pct, "one_entry_rule2_pct": one.rule2_win_pct,
                       "five_entry_rule2_pct": five.rule2_win_pct, "person_avg_rule2_pct": out["rule2"]["person_avg_win_pct"],
                       "one_entry_rule2_x_ratio": r(one.rule2_win_pct / 100 * M / W, 2),
                       "five_vs_one_rule2": r(five.rule2_win_pct / one.rule2_win_pct, 2)}
    print("base", round(time.time() - T0, 1), flush=True)

    # data：申し込んだ人の例（1回分の抽選、②の決まり）
    owner = np.repeat(np.arange(n_people), ks)
    key = rng.random(M)
    mk = np.minimum.reduceat(key, np.concatenate([[0], np.cumsum(ks)[:-1]]))
    won = mk <= np.partition(mk, W - 1)[W - 1]
    pd.DataFrame({"person_id": np.arange(1, n_people + 1), "entries": ks, "won_rule2": won.astype(int)}).to_csv(
        DATA / "applicants_example.csv", index=False)

    # (3) 12通り
    grows = []
    for name, dist in DISTS.items():
        kk = make_people(dist)
        for ratio in [3, 10, 30]:
            Wg = int(round(TOTAL_ENTRIES / ratio))
            _, a1, w2, _ = simulate(rng, kk, Wg, R_GRID)
            kmax = int(kk.max())
            p1 = w2[kk == 1].mean()
            grows.append({"dist": name, "mean_entries": r(kk.mean(), 2), "people": len(kk),
                          "ratio_entries_per_seat": ratio, "seats": Wg,
                          "ratio_people_per_seat": r(len(kk) / Wg, 3),
                          "one_entry_rule2_pct": r(p1 * 100, 2),
                          "one_entry_rule2_x_ratio": r(p1 * TOTAL_ENTRIES / Wg, 2),
                          "one_entry_rule1_pct": r(a1[kk == 1].mean() * 100, 2),
                          "max_entries": kmax, "max_entry_rule2_pct": r(w2[kk == kmax].mean() * 100, 2),
                          "person_avg_rule2_pct": r(w2.mean() * 100, 2),
                          "person_avg_formula_pct": r(Wg / len(kk) * 100, 2)})
        print("grid", name, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grows)
    grid.to_csv(RES / "grid.csv", index=False)
    g2 = grid[grid.dist != "全員1口"]
    out["grid"] = {"settings": len(grid),
                   "one_entry_x_ratio_min": r(g2.one_entry_rule2_x_ratio.min(), 2),
                   "one_entry_x_ratio_max": r(g2.one_entry_rule2_x_ratio.max(), 2),
                   "all_one_x_ratio_min": r(grid[grid.dist == "全員1口"].one_entry_rule2_x_ratio.min()),
                   "all_one_x_ratio_max": r(grid[grid.dist == "全員1口"].one_entry_rule2_x_ratio.max()),
                   "person_avg_x_ratio_min": r((g2.person_avg_rule2_pct / 100 * g2.ratio_entries_per_seat).min(), 2),
                   "person_avg_x_ratio_max": r((g2.person_avg_rule2_pct / 100 * g2.ratio_entries_per_seat).max(), 2)}

    # 図1：口の数ごとの当たる見込み
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    x = np.arange(len(byk))
    ax.bar(x - 0.2, byk.rule1_any_win_pct, width=0.4, color=GRAY, label="①③ 口ごと（1口以上当たる）")
    ax.bar(x + 0.2, byk.rule2_win_pct, width=0.4, color=BLUE, label="② 1人1枠・繰り上げ")
    for i, row in byk.iterrows():
        ax.text(i - 0.2, row.rule1_any_win_pct + 0.8, f"{row.rule1_any_win_pct:g}", ha="center", fontsize=8)
        ax.text(i + 0.2, row.rule2_win_pct + 0.8, f"{row.rule2_win_pct:g}", ha="center", fontsize=8, color=BLUE)
    ax.axhline(10, color=ORANGE, lw=1.2, ls="--", label="10分の1（10%）")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k}口\n（{p:g}%の人）" for k, p in zip(byk.entries, byk.people_share_pct)])
    ax.set_ylim(0, max(byk.rule2_win_pct.max(), byk.rule1_any_win_pct.max()) * 1.18)
    ax.set_ylabel("1人が当たる見込み（%）")
    ax.set_title("倍率10倍（口÷枠）でも、1人の見込みは口の数で決まる")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1173_by_entries.png", SRC)

    # 図2：申し込んだ人の割合と当たった人の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.bar(x - 0.2, byk.people_share_pct, width=0.4, color=GRAY, label="申し込んだ人に占める割合")
    ax.bar(x + 0.2, byk.rule2_winner_share_pct, width=0.4, color=BLUE, label="当たった人に占める割合（②）")
    for i, row in byk.iterrows():
        ax.text(i - 0.2, row.people_share_pct + 0.8, f"{row.people_share_pct:g}", ha="center", fontsize=8)
        ax.text(i + 0.2, row.rule2_winner_share_pct + 0.8, f"{row.rule2_winner_share_pct:g}", ha="center", fontsize=8, color=BLUE)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k}口" for k in byk.entries])
    ax.set_ylim(0, byk.people_share_pct.max() * 1.15)
    ax.set_ylabel("%")
    ax.set_title(f"1口の人は、申し込んだ人の50%、当たった人（②）の{byk.rule2_winner_share_pct.iloc[0]:g}%")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1173_share.png", SRC)

    # 図3：12通り（1口の人の見込み×倍率）
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    cols = {3: GRAY, 10: BLUE, 30: GREEN}
    names = list(DISTS.keys())
    for j, name in enumerate(names):
        for t, ratio in enumerate([3, 10, 30]):
            v = grid[(grid.dist == name) & (grid.ratio_entries_per_seat == ratio)].one_entry_rule2_x_ratio.iloc[0]
            ax.bar(j + (t - 1) * 0.27, v, width=0.27, color=cols[ratio], label=f"倍率{ratio}倍" if j == 0 else None)
            ax.text(j + (t - 1) * 0.27, v + 0.02, f"{v:.2f}", ha="center", fontsize=7.5)
    ax.axhline(1, color=INK, lw=1)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([f"{n}\n（平均{grid[grid.dist == n].mean_entries.iloc[0]:g}口）" for n in names], fontsize=9)
    ax.set_ylim(0, grid.one_entry_rule2_x_ratio.max() * 1.2)
    ax.set_ylabel("1口の人の見込み ÷（1÷倍率）")
    ax.set_xlabel("口の数の分かれ方（②の決まり）")
    ax.legend(frameon=False, fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.set_title("1口の人の見込みが「1÷倍率」の何倍か（1＝ちょうど1÷倍率）", pad=28)
    save(fig, "a1173_grid.png", SRC, y=-0.07)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1173_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
