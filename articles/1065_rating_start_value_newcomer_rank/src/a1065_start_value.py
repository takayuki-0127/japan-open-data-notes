"""1065 初めの点数をいくつにするかで、新しく入った人の順位はどれだけずれるのか？（架空のデータ）

架空の対戦ゲームのリーグ。1人ひとりに本当の強さを作成者が置き、1対1の勝ち負けを
「強さの差から決まる勝つ見込み」で乱数で決める。点数の付け方は、試合ごとに
「勝ち負け（1か0）− 勝つ見込み」に幅 K を掛けて、勝った人に足し、負けた人から引くもの。
すでに300試合した1,000人のリーグに200人が新しく入ったとき、新しい人の初めの点数で
順位のずれがどう変わるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1065
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1065）"
N_EX, N_NEW = 1000, 200
EX_MEAN, EX_SD = 1500.0, 200.0
BASE = {"new_mean": 1400.0, "new_sd": 200.0, "K": 32.0}
INITS = [1000.0, 1200.0, 1300.0, 1400.0, 1500.0, 1800.0]
WARM, ROUNDS = 300, 100
GRID_R = 12
CHECK = [0, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100]


def expect(ra, rb):
    """a が b に勝つ見込み（点数の差400で10倍の比になる形）"""
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def play_round(rng, rating, true, K):
    """全員を2人ずつでたらめに組み、1試合ずつ。rating: (..., R, N)、true: (R, N)。組み方と乱数は先頭の軸で共通"""
    R, N = true.shape
    perm = np.argsort(rng.random((R, N)), axis=1)
    tp = np.take_along_axis(true, perm, 1)
    win = (rng.random((R, N // 2)) < expect(tp[:, 0::2], tp[:, 1::2])).astype(float)  # 組の前の人が勝てば1
    ip = np.broadcast_to(perm, rating.shape)
    rp = np.take_along_axis(rating, ip, -1)
    d = K * (win - expect(rp[..., 0::2], rp[..., 1::2]))
    rp[..., 0::2] += d
    rp[..., 1::2] -= d
    np.put_along_axis(rating, ip, rp, -1)


def ranks(x):
    """大きい順の順位（1が最上位）。同じ値は並びの順"""
    o = np.argsort(-x, axis=-1, kind="stable")
    rk = np.empty_like(o)
    np.put_along_axis(rk, o, np.arange(1, x.shape[-1] + 1), -1)
    return rk


def simulate(rng, new_mean, new_sd, K, R, inits=INITS, every=False, keep_one=False):
    true = np.concatenate([rng.normal(EX_MEAN, EX_SD, (R, N_EX)), rng.normal(new_mean, new_sd, (R, N_NEW))], 1)
    # すでにいる人：初め1500から300試合
    ex = np.full((1, R, N_EX), EX_MEAN)
    for _ in range(WARM):
        play_round(rng, ex, true[:, :N_EX], K)
    ex_before = ex[0].copy()
    nI = len(inits)
    rating = np.concatenate([np.repeat(ex, nI, 0), np.broadcast_to(np.array(inits)[:, None, None], (nI, R, N_NEW))], 2).copy()
    true_rank = ranks(true)
    new = slice(N_EX, None)
    out = {}
    steps = CHECK
    for g in range(ROUNDS + 1):
        if g > 0:
            play_round(rng, rating, true, K)
        if g in steps:
            rk = ranks(rating)
            dr = true_rank[None] - rk  # 正なら本当より上に見える
            out[g] = {"new_bias": (rating[:, :, new] - true[None, :, new]).mean((1, 2)),
                      "new_abs_rank": np.abs(dr[:, :, new]).mean((1, 2)),
                      "new_rank_up": dr[:, :, new].mean((1, 2)),
                      "ex_abs_rank": np.abs(dr[:, :, :N_EX]).mean((1, 2)),
                      "ex_shift": (rating[:, :, :N_EX] - ex_before[None]).mean((1, 2)),
                      "new_mean_rating": rating[:, :, new].mean((1, 2)),
                      "new_top100_share": ((rk[:, :, new] <= 100).sum(2) / 100).mean(1),
                      "true_new_top100_share": float(((true_rank[:, new] <= 100).sum(1) / 100).mean())}
    one = None
    if keep_one:
        one = {"true": true[0], "rating": rating[:, 0, :]}
    return out, one


def r(x, d=4):
    return round(float(x), d)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    R = 100
    base, one = simulate(rng, BASE["new_mean"], BASE["new_sd"], BASE["K"], R, keep_one=True)

    rows = []
    for g in CHECK:
        for i, I in enumerate(INITS):
            o = base[g]
            rows.append({"games": g, "start": int(I), "new_bias": r(o["new_bias"][i], 2),
                         "new_abs_rank": r(o["new_abs_rank"][i], 2), "new_rank_up": r(o["new_rank_up"][i], 2),
                         "existing_abs_rank": r(o["ex_abs_rank"][i], 2), "existing_shift": r(o["ex_shift"][i], 2),
                         "new_mean_rating": r(o["new_mean_rating"][i], 2),
                         "new_share_top100_pct": r(o["new_top100_share"][i] * 100, 2)})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "by_start_and_games.csv", index=False)

    # 新しい人のずれが、すでにいる人のずれの1.1倍以下になる最初の試合数
    catch = {}
    for i, I in enumerate(INITS):
        gg = None
        for g in CHECK:
            if base[g]["new_abs_rank"][i] <= 1.1 * base[g]["ex_abs_rank"][i]:
                gg = g
                break
        catch[int(I)] = gg
    # 点数の合計は動かない：すでにいる人の上がり＝新しい人の下がり×200÷1000（式）
    conserv = {int(I): {"existing_shift": r(base[ROUNDS]["ex_shift"][i], 3),
                        "formula": r((I - base[ROUNDS]["new_mean_rating"][i]) * N_NEW / N_EX, 3)}
               for i, I in enumerate(INITS)}

    # 1回分のデータ（data）
    t1, rt = one["true"], one["rating"]
    df = pd.DataFrame({"player": np.arange(1, N_EX + N_NEW + 1), "group": ["existing"] * N_EX + ["new"] * N_NEW,
                       "true_strength": t1.round(1)})
    for i, I in enumerate(INITS):
        df[f"rating_after100_start{int(I)}"] = rt[i].round(1)
    df.to_csv(DATA / "league_one_run.csv", index=False)

    # 確かめ：新しい人の本当の平均 × 幅K × 新しい人の散らばり（27通り）
    grid = []
    j = 0
    for nm in [1300.0, 1400.0, 1500.0]:
        for K in [16.0, 32.0, 48.0]:
            for ns in [100.0, 200.0, 300.0]:
                o, _ = simulate(np.random.default_rng(SEED * 100 + j), nm, ns, K, GRID_R)
                j += 1
                for i, I in enumerate(INITS):
                    grid.append({"new_mean": nm, "K": K, "new_sd": ns, "start": int(I),
                                 "abs_rank_g10": r(o[10]["new_abs_rank"][i], 2),
                                 "abs_rank_g30": r(o[30]["new_abs_rank"][i], 2),
                                 "abs_rank_g100": r(o[100]["new_abs_rank"][i], 2),
                                 "existing_abs_rank_g10": r(o[10]["ex_abs_rank"][i], 2),
                                 "rank_up_g10": r(o[10]["new_rank_up"][i], 2),
                                 "existing_shift_g100": r(o[100]["ex_shift"][i], 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    # 各通りで、10試合後のずれがいちばん小さい初めの点数
    best = g.loc[g.groupby(["new_mean", "K", "new_sd"]).abs_rank_g10.idxmin()]
    best_match = int((best.start == best.new_mean.astype(int)).sum())
    g1500 = g[g.start == 1500]
    g_own = g[g.start == g.new_mean.astype(int)]
    ratio = (g1500.abs_rank_g10.values / g_own.abs_rank_g10.values)
    ratio18 = ratio[g1500.new_mean.values != 1500]  # 新しい人の本当の平均が1500でない18通り

    b10 = tab[tab.games == 10].set_index("start")
    b30 = tab[tab.games == 30].set_index("start")
    b100 = tab[tab.games == 100].set_index("start")
    out = {"base_setting": dict(BASE, existing_mean=EX_MEAN, existing_sd=EX_SD, n_existing=N_EX, n_new=N_NEW,
                                warmup_games=WARM, games_after_join=ROUNDS, reps=R, starts=INITS),
           "headline": {
               "g10_abs_rank_start1500": float(b10.loc[1500, "new_abs_rank"]),
               "g10_abs_rank_start1400": float(b10.loc[1400, "new_abs_rank"]),
               "g10_abs_rank_start1000": float(b10.loc[1000, "new_abs_rank"]),
               "g10_abs_rank_start1800": float(b10.loc[1800, "new_abs_rank"]),
               "g10_rank_up_start1500": float(b10.loc[1500, "new_rank_up"]),
               "g10_rank_up_start1800": float(b10.loc[1800, "new_rank_up"]),
               "g10_rank_up_start1000": float(b10.loc[1000, "new_rank_up"]),
               "g10_existing_abs_rank": float(b10.loc[1500, "existing_abs_rank"]),
               "g10_start1400_over_existing": r(b10.loc[1400, "new_abs_rank"] / b10.loc[1400, "existing_abs_rank"], 3),
               "g30_abs_rank_start1500": float(b30.loc[1500, "new_abs_rank"]),
               "g30_abs_rank_start1400": float(b30.loc[1400, "new_abs_rank"]),
               "g100_abs_rank_start1500": float(b100.loc[1500, "new_abs_rank"]),
               "g100_abs_rank_start1400": float(b100.loc[1400, "new_abs_rank"]),
               "g100_existing_abs_rank": float(b100.loc[1500, "existing_abs_rank"]),
               "g10_ratio_1500_over_1400": r(b10.loc[1500, "new_abs_rank"] / b10.loc[1400, "new_abs_rank"], 3),
               "existing_shift_g100_start1500": float(b100.loc[1500, "existing_shift"]),
               "existing_shift_g100_start1800": float(b100.loc[1800, "existing_shift"]),
               "existing_shift_g100_start1000": float(b100.loc[1000, "existing_shift"]),
               "g10_new_share_top100_start1800_pct": float(b10.loc[1800, "new_share_top100_pct"]),
               "true_new_share_top100_pct": r(base[0]["true_new_top100_share"] * 100, 2),
               "games_to_catch_up": catch},
           "constants": {"win_prob_scale": 400, "catch_up_ratio": 1.1, "check_games": CHECK},
           "conservation_check": conserv,
           "by_start_and_games": tab.to_dict("records"),
           "grid_summary": {"n": 27,
                            "best_start_equals_new_mean": best_match,
                            "best_start_by_case": best[["new_mean", "K", "new_sd", "start"]].to_dict("records"),
                            "ratio_g10_start1500_over_own_mean_min": r(ratio.min(), 3),
                            "ratio_g10_start1500_over_own_mean_max": r(ratio.max(), 3),
                            "ratio18_g10_start1500_over_own_mean_min": r(ratio18.min(), 3),
                            "ratio18_g10_start1500_over_own_mean_max": r(ratio18.max(), 3),
                            "ratio18_newmean1400_min": r(ratio[g1500.new_mean.values == 1400].min(), 3),
                            "ratio18_newmean1400_max": r(ratio[g1500.new_mean.values == 1400].max(), 3),
                            "ratio18_newmean1300_min": r(ratio[g1500.new_mean.values == 1300].min(), 3),
                            "ratio18_newmean1300_max": r(ratio[g1500.new_mean.values == 1300].max(), 3),
                            "abs_rank_g100_K16_start1000or1800_max": r(g[(g.K == 16) & g.start.isin([1000, 1800])].abs_rank_g100.max(), 2),
                            "abs_rank_g100_K32_48_max": r(g[g.K >= 32].abs_rank_g100.max(), 2),
                            "own_over_existing_g10_min": r((g_own.abs_rank_g10 / g_own.existing_abs_rank_g10).min(), 3),
                            "own_over_existing_g10_max": r((g_own.abs_rank_g10 / g_own.existing_abs_rank_g10).max(), 3),
                            "abs_rank_g10_start1500_min": r(g1500.abs_rank_g10.min(), 2),
                            "abs_rank_g10_start1500_max": r(g1500.abs_rank_g10.max(), 2),
                            "abs_rank_g10_own_min": r(g_own.abs_rank_g10.min(), 2),
                            "abs_rank_g10_own_max": r(g_own.abs_rank_g10.max(), 2),
                            "abs_rank_g100_all_min": r(g.abs_rank_g100.min(), 2),
                            "abs_rank_g100_all_max": r(g.abs_rank_g100.max(), 2),
                            "g1500_newmean1500_g10_min": r(g1500[g1500.new_mean == 1500].abs_rank_g10.min(), 2)},
           "run_sec": None}

    # 図1：試合数ごとの順位のずれ（初めの点数ごと）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    gs = CHECK
    cols = {1000: GRAY, 1200: LIGHT, 1300: "#7a5fb0", 1400: GREEN, 1500: BLUE, 1800: ORANGE}
    for i, I in enumerate(INITS):
        ax.plot(gs, [base[k]["new_abs_rank"][i] for k in gs], color=cols[int(I)], lw=2, marker="o", ms=3, label=f"初め{int(I)}")
    ax.plot(gs, [base[k]["ex_abs_rank"][3] for k in gs], color=INK, lw=1.2, ls="--", label="すでにいる人（初め1500のとき）")
    ax.set_xlabel("新しい人が入ってからの試合数")
    ax.set_ylabel("順位のずれの平均（1,200人中、位）")
    ax.set_ylim(0, None)
    ax.set_title("新しい人の順位のずれ（本当の強さの順位との差、100回の平均）")
    ax.legend(fontsize=8.5, frameon=False)
    save(fig, "a1065_rank_error.png", SRC + "。新しい人の本当の強さは平均1400、すでにいる人は平均1500。幅K=32")

    # 図2：10試合後、本当より何位上に見えるか（棒、0から）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    vals = [b10.loc[int(I), "new_rank_up"] for I in INITS]
    ax.bar([f"初め{int(I)}" for I in INITS], vals, color=[cols[int(I)] for I in INITS])
    ax.axhline(0, color=INK, lw=0.8)
    for x, v in enumerate(vals):
        ax.text(x, v + (8 if v >= 0 else -8), f"{v:+g}位", ha="center", va="bottom" if v >= 0 else "top", fontsize=9.5)
    lo, hi = min(vals + [0]), max(vals + [0])
    ax.set_ylim(lo - 70, hi + 50)
    ax.set_ylabel("本当より上に見える順位（平均、位）")
    ax.set_title("10試合後の新しい人：初めの点数で上にも下にもずれる")
    save(fig, "a1065_bias_g10.png", SRC + "。正なら本当より上の順位に見える。100回の平均")

    # 図3：27通りでの10試合後のずれ（初め1500と、新しい人の本当の平均に合わせたとき）
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    lab = [f"{int(a)}/{int(k)}/{int(s)}" for a, k, s in zip(g1500.new_mean, g1500.K, g1500.new_sd)]
    x = np.arange(len(lab))
    ax.bar(x - 0.2, g1500.abs_rank_g10.values, 0.4, color=BLUE, label="初め1500")
    ax.bar(x + 0.2, g_own.abs_rank_g10.values, 0.4, color=GREEN, label="初め＝新しい人の本当の平均")
    ax.set_xticks(x)
    ax.set_xticklabels(lab, rotation=90, fontsize=7)
    ax.set_xlabel("新しい人の本当の平均／幅K／新しい人の散らばり")
    ax.set_ylabel("10試合後の順位のずれ（位）")
    ax.set_ylim(0, max(g1500.abs_rank_g10.max(), g_own.abs_rank_g10.max()) * 1.22)
    ax.set_title("置き方27通りでの10試合後の順位のずれ（各12回の平均）")
    ax.legend(fontsize=8.5, frameon=False, ncol=2, loc="upper left")
    save(fig, "a1065_grid.png", SRC + "。新しい人の本当の平均が1500の9通りは、2本の棒が同じ置き方", y=-0.2)

    out["run_sec"] = None
    with open(RES / "a1065_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=lambda v: v if not isinstance(v, np.generic) else v.item())
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, indent=1, default=str)[:1500])
    print(conserv)
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
