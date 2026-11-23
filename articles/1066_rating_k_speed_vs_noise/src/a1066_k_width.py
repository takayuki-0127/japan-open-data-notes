"""1066 1試合で動かす点の幅を大きくすると、強さは早く当たるのか、ぶれるのか？（架空のデータ）

架空の対戦ゲームのリーグ500人。1人ひとりに本当の強さを作成者が置き、1対1の勝ち負けを
「強さの差から決まる勝つ見込み」で乱数で決める。点数の付け方は、試合ごとに
「勝ち負け（1か0）− 勝つ見込み」に幅 K を掛けて、勝った人に足し、負けた人から引くもの。
全員1500から始め、K を変えて、点数が本当の強さに近づく早さと、近づいたあとのぶれを数える。
300試合目に1割の人の本当の強さを上げ、点数が追いつく早さも数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1066
SRC = "架空の対戦ゲームのリーグ（作成者が乱数で作成、seed 1066）"
N = 500
MEAN = 1500.0
BASE = {"true_sd": 200.0, "jump": 200.0, "jump_share": 0.1}
KS = [8.0, 16.0, 24.0, 32.0, 48.0, 64.0, 96.0]
ROUNDS, JUMP_AT = 500, 300
STEADY = (200, 300)  # この間（201〜300試合目）の平均をぶれとする
CHECK = [0, 5, 10, 20, 30, 50, 75, 100, 150, 200, 250, 300, 310, 330, 350, 400, 500]
C = 400.0 / np.log(10)  # 近似の式で使う定数（約173.7）


def expect(ra, rb):
    """a が b に勝つ見込み（点数の差400で10倍の比になる形）"""
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def play_round(rng, rating, true, K):
    """全員を2人ずつでたらめに組み、1試合ずつ。rating: (nK, R, N)、K: (nK,1,1)。組み方と乱数は K で共通"""
    R, n = true.shape
    perm = np.argsort(rng.random((R, n)), axis=1)
    tp = np.take_along_axis(true, perm, 1)
    win = (rng.random((R, n // 2)) < expect(tp[:, 0::2], tp[:, 1::2])).astype(float)
    ip = np.broadcast_to(perm, rating.shape)
    rp = np.take_along_axis(rating, ip, -1)
    d = K * (win - expect(rp[..., 0::2], rp[..., 1::2]))
    rp[..., 0::2] += d
    rp[..., 1::2] -= d
    np.put_along_axis(rating, ip, rp, -1)


def ranks(x):
    o = np.argsort(-x, axis=-1, kind="stable")
    rk = np.empty_like(o)
    np.put_along_axis(rk, o, np.arange(1, x.shape[-1] + 1), -1)
    return rk


def simulate(rng, true_sd, jump, jump_share, R, keep_one=False):
    true = rng.normal(MEAN, true_sd, (R, N))
    nK = len(KS)
    Kc = np.array(KS)[:, None, None]
    rating = np.full((nK, R, N), MEAN)
    jumper = np.zeros((R, N), bool)
    jumper[:, : int(N * jump_share)] = True  # 並びはでたらめなので先頭の1割でよい
    rmse = np.zeros((ROUNDS + 1, nK))
    gap = np.zeros((ROUNDS + 1, nK))  # 強さが上がった人の（本当−点数）の平均
    rk_out, top10 = {}, {}
    trace = []
    prev_top = None
    for g in range(ROUNDS + 1):
        if g == JUMP_AT + 1:
            true = true + jump * jumper  # 301試合目の前に強さが上がる
        if g > 0:
            play_round(rng, rating, true, Kc)
        err = rating - true[None]
        rmse[g] = np.sqrt((err ** 2).mean((1, 2)))
        gap[g] = -(err * jumper[None]).sum((1, 2)) / jumper.sum()
        if keep_one:
            trace.append(rating[:, 0, ::100].copy())  # 1回目のリーグの5人（0・100・200・300・400番目）
        if g in CHECK:
            rk = ranks(rating)
            tr = ranks(true)
            rk_out[g] = np.abs(rk - tr[None]).mean((1, 2))
            rk_out[f"j{g}"] = ((rk - tr[None]) * jumper[None]).sum((1, 2)) / jumper.sum()  # 強くなった人が本当より何位下に見えるか
        if g in (290, 300):
            # 上位10人の顔ぶれ
            o = np.argsort(-rating, axis=-1)[..., :10]
            if prev_top is None:
                prev_top = o
            else:
                same = np.array([[len(set(prev_top[k, rr]) & set(o[k, rr])) for rr in range(R)] for k in range(nK)])
                top10["changed_in_10_games"] = 10 - same.mean(1)
    one = None
    if keep_one:
        one = {"true": (true[0] - jump * jumper[0])[::100], "trace": np.array(trace), "jumper": jumper[0, ::100]}
    return {"rmse": rmse, "gap": gap, "rank": rk_out, "top10": top10}, one


def first_le(series, thr, start=0):
    for i in range(start, len(series)):
        if series[i] <= thr:
            return i - start
    return None


def r(x, d=4):
    return round(float(x), d)


def summarize(res, true_sd, jump):
    rm, gp = res["rmse"], res["gap"]
    out = []
    for i, K in enumerate(KS):
        steady = rm[STEADY[0] + 1: STEADY[1] + 1, i].mean()
        out.append({"K": int(K), "true_sd": true_sd, "jump": jump,
                    "rmse_g10": r(rm[10, i], 2), "rmse_g30": r(rm[30, i], 2), "rmse_g100": r(rm[100, i], 2),
                    "rmse_g300": r(rm[300, i], 2),
                    "games_to_rmse_le_100": first_le(rm[:, i], 100.0),
                    "steady_rmse": r(steady, 2), "formula_sd": r(np.sqrt(K * C / 2), 2),
                    "gap_after_jump_10": r(gp[JUMP_AT + 10, i], 2), "gap_after_jump_30": r(gp[JUMP_AT + 30, i], 2),
                    "games_to_half_gap": first_le(gp[:, i], jump / 2, JUMP_AT + 1) + 1 if first_le(gp[:, i], jump / 2, JUMP_AT + 1) is not None else None,
                    "abs_rank_g10": r(res["rank"][10][i], 2), "abs_rank_g30": r(res["rank"][30][i], 2),
                    "abs_rank_g100": r(res["rank"][100][i], 2), "abs_rank_g300": r(res["rank"][300][i], 2),
                    "abs_rank_after_jump_10": r(res["rank"][310][i], 2), "abs_rank_after_jump_30": r(res["rank"][330][i], 2),
                    "abs_rank_after_jump_100": r(res["rank"][400][i], 2), "abs_rank_after_jump_200": r(res["rank"][500][i], 2),
                    "jumper_rank_below_after_10": r(res["rank"]["j310"][i], 2),
                    "jumper_rank_below_after_30": r(res["rank"]["j330"][i], 2),
                    "jumper_rank_below_after_100": r(res["rank"]["j400"][i], 2)})
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    R = 40
    base, one = simulate(rng, BASE["true_sd"], BASE["jump"], BASE["jump_share"], R, keep_one=True)
    tab = pd.DataFrame(summarize(base, BASE["true_sd"], BASE["jump"]))
    tab["top10_changed_in_10_games"] = [r(v, 2) for v in base["top10"]["changed_in_10_games"]]
    tab.to_csv(RES / "by_k.csv", index=False)
    curve = pd.DataFrame(base["rmse"].round(3), columns=[f"K{int(k)}" for k in KS])
    curve.insert(0, "games", np.arange(ROUNDS + 1))
    curve.to_csv(RES / "rmse_by_games.csv", index=False)

    # 1回分のデータ（data）：1回目のリーグの最初の5人の点数の動き
    tr = one["trace"]  # (rounds+1, nK, 5)
    rows = []
    for gi in range(ROUNDS + 1):
        for k, K in enumerate(KS):
            for p in range(5):
                rows.append((gi, int(K), p + 1, round(float(tr[gi, k, p]), 1)))
    d = pd.DataFrame(rows, columns=["games", "K", "player", "rating"])
    d["true_strength_before_jump"] = d.player.map({p + 1: round(float(one["true"][p]), 1) for p in range(5)})
    d["stronger_after_300"] = d.player.map({p + 1: int(one["jumper"][p]) for p in range(5)})
    d.to_csv(DATA / "five_players_trace.csv", index=False)

    # いちばんよい K（その試合数で点数のずれがいちばん小さい K）
    best, best_rank = {}, {}
    for g in [10, 30, 100, 300]:
        i = int(np.argmin(base["rmse"][g]))
        best[g] = {"K": int(KS[i]), "rmse": r(base["rmse"][g, i], 2)}
        ir = int(np.argmin(base["rank"][g]))
        best_rank[g] = {"K": int(KS[ir]), "abs_rank": r(base["rank"][g][ir], 2)}
    for h, gg in [(10, 310), (30, 330), (100, 400), (200, 500)]:
        ir = int(np.argmin(base["rank"][gg]))
        best_rank[f"after_jump_{h}"] = {"K": int(KS[ir]), "abs_rank": r(base["rank"][gg][ir], 2)}

    # 確かめ：本当の強さの散らばり × 強さの上がり幅（9通り）
    grid = []
    j = 0
    for sd in [100.0, 200.0, 300.0]:
        for jump in [100.0, 200.0, 400.0]:
            res, _ = simulate(np.random.default_rng(SEED * 100 + j), sd, jump, BASE["jump_share"], 12)
            j += 1
            rows = summarize(res, sd, jump)
            for g in [10, 30, 100, 300]:
                i = int(np.argmin(res["rmse"][g]))
                ir = int(np.argmin(res["rank"][g]))
                for row in rows:
                    row[f"best_K_g{g}"] = int(KS[i])
                    row[f"best_K_rank_g{g}"] = int(KS[ir])
            for h, gg in [(10, 310), (30, 330), (100, 400)]:
                ir = int(np.argmin(res["rank"][gg]))
                for row in rows:
                    row[f"best_K_rank_after_jump_{h}"] = int(KS[ir])
            grid += rows
    gdf = pd.DataFrame(grid)
    gdf.to_csv(RES / "grid.csv", index=False)
    gs = gdf.groupby(["true_sd", "jump"]).first().reset_index()
    gk = gdf[gdf.K >= 16]  # 幅8は300試合でも近づき切らないので、式との比べから外す
    ratio = gk.steady_rmse / gk.formula_sd
    gk24 = gdf[gdf.K >= 24]
    ratio24 = gk24.steady_rmse / gk24.formula_sd

    t = tab.set_index("K")
    out = {"base_setting": dict(BASE, n_players=N, start=MEAN, rounds=ROUNDS, jump_at=JUMP_AT, reps=R, Ks=KS,
                                steady_window=[STEADY[0] + 1, STEADY[1]]),
           "headline": {
               "K16_rmse_g30": float(t.loc[16, "rmse_g30"]), "K96_rmse_g30": float(t.loc[96, "rmse_g30"]),
               "K32_rmse_g30": float(t.loc[32, "rmse_g30"]),
               "K16_games_to_100": t.loc[16, "games_to_rmse_le_100"], "K32_games_to_100": t.loc[32, "games_to_rmse_le_100"],
               "K96_games_to_100": t.loc[96, "games_to_rmse_le_100"], "K8_games_to_100": t.loc[8, "games_to_rmse_le_100"],
               "K16_steady": float(t.loc[16, "steady_rmse"]), "K32_steady": float(t.loc[32, "steady_rmse"]),
               "K96_steady": float(t.loc[96, "steady_rmse"]), "K8_steady": float(t.loc[8, "steady_rmse"]),
               "K96_over_K16_steady": r(t.loc[96, "steady_rmse"] / t.loc[16, "steady_rmse"], 3),
               "sqrt6": r(np.sqrt(6), 3),
               "steady_over_formula_K16plus_min": r((tab[tab.K >= 16].steady_rmse / tab[tab.K >= 16].formula_sd).min(), 3),
               "steady_over_formula_K16plus_max": r((tab[tab.K >= 16].steady_rmse / tab[tab.K >= 16].formula_sd).max(), 3),
               "K8_abs_rank_g100": float(t.loc[8, "abs_rank_g100"]), "K96_abs_rank_g100": float(t.loc[96, "abs_rank_g100"]),
               "K16_abs_rank_g100": float(t.loc[16, "abs_rank_g100"]), "K32_abs_rank_g100": float(t.loc[32, "abs_rank_g100"]),
               "K8_abs_rank_g10": float(t.loc[8, "abs_rank_g10"]), "K96_abs_rank_g10": float(t.loc[96, "abs_rank_g10"]),
               "K16_jumper_below_30": float(t.loc[16, "jumper_rank_below_after_30"]),
               "K96_jumper_below_30": float(t.loc[96, "jumper_rank_below_after_30"]),
               "K8_abs_rank_after_jump_30": float(t.loc[8, "abs_rank_after_jump_30"]),
               "K96_abs_rank_after_jump_30": float(t.loc[96, "abs_rank_after_jump_30"]),
               "K16_half_gap_games": t.loc[16, "games_to_half_gap"], "K96_half_gap_games": t.loc[96, "games_to_half_gap"],
               "K32_half_gap_games": t.loc[32, "games_to_half_gap"],
               "K16_top10_changed": float(t.loc[16, "top10_changed_in_10_games"]),
               "K96_top10_changed": float(t.loc[96, "top10_changed_in_10_games"]),
               "K32_top10_changed": float(t.loc[32, "top10_changed_in_10_games"]),
               "best_K_by_games": best, "best_K_rank_by_games": best_rank},
           "constants": {"win_prob_scale": 400, "formula_const_400_over_2ln10": r(C / 2, 1), "top10_window_games": [290, 300],
                         "n_jumpers": int(N * BASE["jump_share"])},
           "formula_note": "近似の式：ぶれ（点数と本当の強さの差の標準偏差）≈ √(K×400÷(2×ln10))、強さが変わった差が半分になる試合数 ≈ ln2÷(K×ln10÷400×p(1−p) の平均)",
           "by_k": tab.to_dict("records"),
           "grid_summary": {"n": 9,
                            "steady_over_formula_min_K16plus": r(ratio.min(), 3), "steady_over_formula_max_K16plus": r(ratio.max(), 3),
                            "steady_over_formula_min_K24plus": r(ratio24.min(), 3), "steady_over_formula_max_K24plus": r(ratio24.max(), 3),
                            "best_K_g10": sorted(set(gs.best_K_g10.astype(int).tolist())),
                            "best_K_g30": sorted(set(gs.best_K_g30.astype(int).tolist())),
                            "best_K_g100": sorted(set(gs.best_K_g100.astype(int).tolist())),
                            "best_K_g300": sorted(set(gs.best_K_g300.astype(int).tolist())),
                            "best_K_rank_g10": sorted(set(gs.best_K_rank_g10.astype(int).tolist())),
                            "best_K_rank_g30": sorted(set(gs.best_K_rank_g30.astype(int).tolist())),
                            "best_K_rank_g100": sorted(set(gs.best_K_rank_g100.astype(int).tolist())),
                            "best_K_rank_g300": sorted(set(gs.best_K_rank_g300.astype(int).tolist())),
                            "best_K_rank_after_jump_10": sorted(set(gs.best_K_rank_after_jump_10.astype(int).tolist())),
                            "best_K_rank_after_jump_30": sorted(set(gs.best_K_rank_after_jump_30.astype(int).tolist())),
                            "best_K_rank_after_jump_100": sorted(set(gs.best_K_rank_after_jump_100.astype(int).tolist())),
                            "best_by_case": gs[["true_sd", "jump", "best_K_g10", "best_K_g30", "best_K_g100", "best_K_g300",
                                                "best_K_rank_g10", "best_K_rank_g30", "best_K_rank_g100", "best_K_rank_g300",
                                                "best_K_rank_after_jump_10", "best_K_rank_after_jump_30", "best_K_rank_after_jump_100"]].to_dict("records"),
                            "K96_over_K16_half_gap_min": r((gdf[gdf.K == 16].games_to_half_gap.values / gdf[gdf.K == 96].games_to_half_gap.values).min(), 3),
                            "K96_over_K16_half_gap_max": r((gdf[gdf.K == 16].games_to_half_gap.values / gdf[gdf.K == 96].games_to_half_gap.values).max(), 3)},
           "run_sec": None}

    cols = {8: GRAY, 16: LIGHT, 24: "#7a5fb0", 32: BLUE, 48: GREEN, 64: "#c9a227", 96: ORANGE}
    # 図1：試合数ごとのずれ
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    for i, K in enumerate(KS):
        ax.plot(np.arange(ROUNDS + 1), base["rmse"][:, i], color=cols[int(K)], lw=1.6, label=f"K={int(K)}")
    ax.axvline(JUMP_AT, color=GRAY, lw=0.8, ls=":")
    ax.text(JUMP_AT + 6, 160, "300試合目のあとに1割の人が\n本当に200強くなる", fontsize=8.5, color=INK, va="top")
    ax.set_xlabel("試合数（全員が同じ数だけ対戦）")
    ax.set_ylabel("点数と本当の強さの差（二乗平均の平方根）")
    ax.set_ylim(0, 210)
    ax.set_title("幅Kが大きいほど早く近づくが、近づいたあとのずれが大きい")
    ax.legend(fontsize=8, frameon=False, ncol=4, loc="upper right", bbox_to_anchor=(1.0, 1.0))
    save(fig, "a1066_rmse_curve.png", SRC + "。500人・全員1500から。40回の平均")

    # 図2：近づいたあとのずれ（棒、0から）と近似の式
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(len(KS))
    ax.bar(x, tab.steady_rmse, color=[cols[int(k)] for k in KS], label="乱数で数えた値（201〜300試合目の平均）")
    ax.plot(x, tab.formula_sd, "o", color=INK, ms=5, label="近似の式 √(K×86.9)")
    for xi, v in zip(x, tab.steady_rmse):
        ax.text(xi, v + 2, f"{v:g}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}" + ("\n（300試合で\nまだ近づく途中）" if k == 8 else "") for k in KS], fontsize=9.5)
    ax.set_ylim(0, tab.steady_rmse.max() * 1.25)
    ax.set_ylabel("点数と本当の強さの差（二乗平均の平方根）")
    ax.set_title("近づいたあとのぶれは、おおよそ√Kに比例する")
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    save(fig, "a1066_steady.png", SRC, y=-0.1)

    # 図3：強さが上がった人に点数が追いつく
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    gg = np.arange(JUMP_AT + 1, ROUNDS + 1)
    for i, K in enumerate(KS):
        ax.plot(gg - JUMP_AT, base["gap"][JUMP_AT + 1:, i], color=cols[int(K)], lw=1.6, label=f"K={int(K)}")
    ax.axhline(BASE["jump"] / 2, color=GRAY, lw=0.8, ls=":")
    ax.text(150, BASE["jump"] / 2 + 4, "差が半分（100）", fontsize=8.5, color=INK)
    ax.set_xlabel("強さが上がってからの試合数（1試合目から）")
    ax.set_ylabel("本当の強さ − 点数（強くなった人の平均）")
    ax.set_ylim(0, 230)
    ax.set_title("1割の人が本当に200強くなったとき、点数が追いつく早さ")
    ax.legend(fontsize=8, frameon=False, ncol=4, loc="upper right")
    save(fig, "a1066_jump.png", SRC + "。40回の平均")

    # 図4：順位のずれ（棒、0から）
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    x = np.arange(len(KS))
    for j, (col, lab, c) in enumerate([("abs_rank_g10", "10試合", LIGHT), ("abs_rank_g30", "30試合", BLUE),
                                       ("abs_rank_g100", "100試合", INK)]):
        ax.bar(x + (j - 1) * 0.27, tab[col], 0.27, color=c, label=lab)
    ax.set_xticks(x)
    ax.set_xticklabels([f"K={int(k)}" for k in KS])
    ax.set_ylim(0, tab.abs_rank_g10.max() * 1.25)
    ax.set_ylabel("順位のずれの平均（500人中、位）")
    ax.set_title("全員が同じ数だけ対戦するとき、順位は幅が小さいほうがずれない")
    ax.legend(fontsize=8.5, frameon=False, ncol=3, loc="upper left")
    save(fig, "a1066_rank.png", SRC + "。本当の強さの順位との差。40回の平均")

    with open(RES / "a1066_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=lambda v: v.item() if isinstance(v, np.generic) else v)
    print(tab.to_string())
    print(json.dumps(out["headline"], ensure_ascii=False, default=str))
    print(json.dumps(out["grid_summary"], ensure_ascii=False, default=str))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
