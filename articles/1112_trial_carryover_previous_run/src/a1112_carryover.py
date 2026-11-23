"""1112 前の試作の残りが次の結果にまざると、何がずれるのか？（架空のデータ）

架空の染め工房が、4つの染め液の配合（A〜D）を試し染めして「色落ちの値」（洗ったあとに落ちた色の量を機械で測った値、小さいほど良い）を比べる。
同じ槽で続けて染めるので、前の回の液が少し残り、次の回にまざる。槽の中身＝（1−残る割合）×今回の配合＋残る割合×前の回の槽の中身。
測る色落ちの値＝槽の中身の配合ごとの本当の値の加重平均＋1回ごとのぶれ。
4つの配合を8回ずつ（32回）染める並べ方を変え、配合ごとの平均がどれだけずれるか、差がどれだけ縮むか、いちばん良い配合を当てる割合を数える。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1112
SRC = "架空の染め工房の試し染め（作成者が置いた本当の値と残り方からの乱数、seed 1112）"
NAMES = ["A", "B", "C", "D"]
TRUE = np.array([10.0, 9.2, 8.6, 8.2])          # 色落ちの本当の値（小さいほど良い）
K, R = 4, 8                                      # 配合の数、1つあたりの回数
BASE = {"lam": 0.3, "sigma": 0.4, "drift": 0.0}
REPS = 5000
GRID_LAM = [0.1, 0.3, 0.5]
GRID_SIGMA = [0.2, 0.4, 0.8]
GRID_DRIFT = [0.0, 0.01]
GRID_REPS = 2000
BALANCED_ROWS = [[0, 1, 3, 2], [1, 2, 0, 3], [2, 3, 1, 0], [3, 0, 2, 1]]   # どの配合の前にも、ほかの3つが1回ずつ来る4行
COLORS = [GRAY, BLUE, GREEN, ORANGE]


def r(x, d=3):
    return round(float(x), d)


def designs():
    """（名前, 並べ方を作る関数（rng → [(配合, 測るか)]）, 捨て染めの回数）"""
    cyc = lambda rng: [(c, True) for _ in range(R) for c in range(K)]
    cyc_rev = lambda rng: [(c, True) for _ in range(R) for c in range(K)[::-1]]
    rnd = lambda rng: [(int(c), True) for c in rng.permutation(np.repeat(np.arange(K), R))]
    bal = lambda rng: [(c, True) for _ in range(R // K) for row in BALANCED_ROWS for c in row]

    def blk(n_discard):
        def f(rng):
            seq = []
            for i, c in enumerate(range(K)):
                if i > 0:
                    seq += [(c, False)] * n_discard
                seq += [(c, True)] * R
            return seq
        return f
    return [("①順に回す（ABCD を8回）", cyc, 0), ("②逆の順に回す（DCBA を8回）", cyc_rev, 0), ("③でたらめに並べる", rnd, 0),
            ("④前に来る配合をそろえる", bal, 0), ("⑤まとめて染める（A8回→B8回→…）", blk(0), 0),
            ("⑥まとめて＋切りかえ後に1回捨て染め", blk(1), 1), ("⑦まとめて＋切りかえ後に2回捨て染め", blk(2), 2)]


def run_design(rng, make_seq, reps, lam, sigma, drift, keep_example=False):
    """reps 回をまとめて流す（並べ方は回ごとに make_seq で作る）"""
    seqs = [make_seq(rng) for _ in range(reps)]
    C = np.array([[c for c, _ in s] for s in seqs])            # (reps,T)
    M = np.array([[mm for _, mm in s] for s in seqs])          # (reps,T)
    T = C.shape[1]
    eye = np.eye(K)
    noise = rng.normal(0, sigma, (reps, T))
    m = eye[C[:, 0]]                                           # はじめは洗った槽に最初の配合
    Y = np.zeros((reps, T)); MS = np.zeros((reps, T, K))
    for t in range(T):
        if t > 0:
            m = (1 - lam) * eye[C[:, t]] + lam * m
        Y[:, t] = m @ TRUE + drift * t + noise[:, t]
        MS[:, t] = m
    est = np.zeros((reps, K))
    for c in range(K):
        w = (C == c) & M
        est[:, c] = (Y * w).sum(1) / w.sum(1)
    example = None
    if keep_example:
        example = [{"run": t + 1, "recipe": NAMES[C[0, t]], "measured": int(M[0, t]), "value": round(float(Y[0, t]), 4),
                    **{f"vat_{NAMES[j]}": round(float(MS[0, t, j]), 4) for j in range(K)},
                    "true_pure": float(TRUE[C[0, t]])} for t in range(T)]
    return est, example


def summarize(est, n_runs):
    tc = TRUE - TRUE.mean()
    ec = est - est.mean(1, keepdims=True)
    slope = (ec @ tc) / (tc @ tc)                            # 4つの差がどれだけ縮んだか（1＝縮まない）
    d_da = est[:, 3] - est[:, 0]
    return {"runs_total": n_runs,
            **{f"mean_{n}": r(est[:, i].mean()) for i, n in enumerate(NAMES)},
            **{f"bias_{n}": r(est[:, i].mean() - TRUE[i]) for i, n in enumerate(NAMES)},
            "shrink": r(slope.mean()),
            "diff_DA": r(d_da.mean()), "diff_DA_ratio": r(d_da.mean() / (TRUE[3] - TRUE[0])),
            "diff_DC": r((est[:, 3] - est[:, 2]).mean()),
            "diff_CB": r((est[:, 2] - est[:, 1]).mean()),
            "sd_diff_DA": r(d_da.std()),
            "pick_D_pct": r((est.argmin(1) == 3).mean() * 100, 2),
            "order_all_right_pct": r((np.all(np.diff(est, axis=1) < 0, axis=1)).mean() * 100, 2)}


def main():
    t0 = time.time()
    b = BASE
    D = designs()

    # 1) 基本の置き方で6つの並べ方（各5,000回）
    rows, examples = [], {}
    for di, (name, f, nd) in enumerate(D):
        est, ex = run_design(np.random.default_rng(SEED * 10 + di), f, REPS, b["lam"], b["sigma"], b["drift"], keep_example=True)
        n_runs = K * R + nd * (K - 1)
        rows.append({"design": name, **summarize(est, n_runs)})
        examples[name] = ex
    main_df = pd.DataFrame(rows)
    main_df.to_csv(RES / "designs_base.csv", index=False)
    ex_df = pd.concat([pd.DataFrame(v).assign(design=k) for k, v in examples.items()], ignore_index=True)
    ex_df = ex_df[["design"] + [c for c in ex_df.columns if c != "design"]]
    ex_df.to_csv(DATA / "example_sequences.csv", index=False)

    # 式の値：でたらめ（前の配合が4つから同じ割合で来る）なら (1−λ)、前に同じ配合が来ないなら (1−λ)/(1+λ/(K−1))
    lam = b["lam"]
    formula = {"shrink_random_iid": r(1 - lam), "shrink_no_self": r((1 - lam) / (1 + lam / (K - 1))),
               "block_first_run_residue": r(lam), "block_mean_residue_8runs": r(sum(lam ** j for j in range(1, R + 1)) / R),
               "block_mean_residue_8runs_after1discard": r(sum(lam ** j for j in range(2, R + 2)) / R),
               "block_mean_residue_8runs_after2discard": r(sum(lam ** j for j in range(3, R + 3)) / R),
               "block_bias_formula": {NAMES[i]: r(sum(lam ** j for j in range(1, R + 1)) / R * (TRUE[i - 1] - TRUE[i])) for i in range(1, K)}}

    # 2) 確かめ：残る割合 × 1回のぶれ × だんだん変わる分（18通り、各2,000回）
    grid = []
    for gi, (lm, sg, dr) in enumerate(itertools.product(GRID_LAM, GRID_SIGMA, GRID_DRIFT)):
        for di, (name, f, nd) in enumerate(D):
            est, _ = run_design(np.random.default_rng(SEED * 1000 + gi * 10 + di), f, GRID_REPS, lm, sg, dr)
            s = summarize(est, K * R + nd * (K - 1))
            grid.append({"lam": lm, "sigma": sg, "drift_per_run": dr, "design": name,
                         "shrink": s["shrink"], "diff_DA_ratio": s["diff_DA_ratio"], "pick_D_pct": s["pick_D_pct"],
                         **{f"bias_{n}": s[f"bias_{n}"] for n in NAMES}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    dn = [d[0] for d in D]
    g0 = grid[grid.drift_per_run == 0]; g1 = grid[grid.drift_per_run > 0]
    rng_of = lambda g, name, col: [r(g[g.design == name][col].min()), r(g[g.design == name][col].max())]
    out = {"base": BASE, "true": dict(zip(NAMES, TRUE.tolist())), "runs_per_recipe": R, "reps": REPS,
           "formula": formula,
           "designs": main_df.to_dict(orient="records"),
           "grid_no_drift_shrink_range": {n: rng_of(g0, n, "shrink") for n in dn},
           "grid_drift_shrink_range": {n: rng_of(g1, n, "shrink") for n in dn},
           "grid_no_drift_pick_D_range": {n: rng_of(g0, n, "pick_D_pct") for n in dn},
           "grid_drift_pick_D_range": {n: rng_of(g1, n, "pick_D_pct") for n in dn},
           "grid_drift_bias_D_range": {n: rng_of(g1, n, "bias_D") for n in dn},
           "grid_drift_bias_A_range": {n: rng_of(g1, n, "bias_A") for n in dn},
           "grid_random_shrink_minus_formula_maxabs": r((grid[grid.design == dn[2]].shrink - (1 - grid[grid.design == dn[2]].lam)).abs().max()),
           "grid_by_lam_formula": {str(lm): {"random_formula": r(1 - lm), "no_self_formula": r((1 - lm) / (1 + lm / (K - 1))),
                                              "random_mean": r(g0[(g0.design == dn[2]) & (g0.lam == lm)].shrink.mean()),
                                              "balanced_mean": r(g0[(g0.design == dn[3]) & (g0.lam == lm)].shrink.mean())} for lm in GRID_LAM},
           "grid_count": int(len(grid) / len(D))}
    json.dump(out, open(RES / "a1112_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の並べ方（①と④）の1回分
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
    for ax, name in zip(axes, [dn[0], dn[4]]):
        e = pd.DataFrame(examples[name])
        for j, n in enumerate(NAMES):
            ee = e[e.recipe == n]
            ax.scatter(ee.run, ee.value, color=COLORS[j], s=22, label=f"{n}（本当 {TRUE[j]:g}）")
            ax.axhline(TRUE[j], color=COLORS[j], lw=0.8, ls=":")
        ax.set_title(name, loc="left", fontsize=11)
        ax.set_xlabel("染めた順（回目）")
    axes[0].set_ylabel("色落ちの値（小さいほど良い）")
    axes[1].legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.suptitle("例の1回分：点線が本当の値。前の配合の残りで、値が前の配合の側へ引っぱられる", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1112_example.png", SRC)

    # 図2：並べ方ごとの差の縮みと、いちばん良い配合（D）を当てた割合
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    y = np.arange(len(dn))[::-1]
    short = ["①順に回す（ABCD）", "②逆の順に回す（DCBA）", "③でたらめ", "④前の配合をそろえる", "⑤まとめて", "⑥まとめて＋捨て1回", "⑦まとめて＋捨て2回"]
    axes[0].barh(y, main_df.shrink, color=BLUE)
    for yy, v in zip(y, main_df.shrink):
        axes[0].text(max(v, 1.0) + 0.012, yy, f"{v:.3f}", va="center", fontsize=9)
    axes[0].axvline(1, color=INK, lw=0.8)
    axes[0].set_yticks(y); axes[0].set_yticklabels(short)
    axes[0].set_xlim(0, 1.18)
    axes[0].set_xlabel("見かけの差÷本当の差（4配合の平均、1＝縮まない）")
    axes[0].set_title("差の縮み", loc="left", fontsize=11)
    axes[1].barh(y, main_df.pick_D_pct, color=ORANGE)
    for yy, v in zip(y, main_df.pick_D_pct):
        axes[1].text(v + 1, yy, f"{v:.2f}%", va="center", fontsize=9)
    axes[1].set_yticks(y); axes[1].set_yticklabels([])
    axes[1].set_xlim(0, 110)
    axes[1].set_xlabel("いちばん良い D を選べた割合（%）")
    axes[1].set_title("いちばん良い配合を当てた割合", loc="left", fontsize=11)
    fig.suptitle(f"残る割合 {b['lam']}・1回のぶれ {b['sigma']} で、7つの並べ方（各{REPS:,}回の平均）", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1112_designs.png", SRC)

    # 図3：確かめ（18通り）
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, dr in zip(axes, GRID_DRIFT):
        g = grid[(grid.drift_per_run == dr) & (grid.sigma == b["sigma"])]
        for name, sh, col, mk in zip(dn, short, [GRAY, "#8c6bb1", BLUE, GREEN, ORANGE, INK, LIGHT], ["o", "X", "s", "^", "D", "v", "P"]):
            gg = g[g.design == name]
            ax.plot(gg.lam, gg.diff_DA_ratio, marker=mk, color=col, lw=1.3, label=sh)
        ax.axhline(1, color=INK, lw=0.6, ls=":")
        ax.set_xticks(GRID_LAM); ax.set_xlabel("前の回の液が残る割合")
        ax.set_title("だんだん変わる分なし" if dr == 0 else f"1回ごとに色落ちが {dr} ずつ増える", loc="left", fontsize=11)
        ax.set_ylim(0, None)
    axes[0].set_ylabel("見かけの D−A ÷ 本当の D−A")
    axes[1].legend(frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.suptitle("確かめ（1回のぶれ0.4）：残りが多いほど縮み、だんだん変わる分があると、まとめて染める並べ方もずれる", x=0.01, y=1.04, ha="left", fontsize=12)
    save(fig, "a1112_robust.png", SRC)

    print(main_df.to_string()); print(formula)
    pd.set_option("display.width", 250)
    print(grid[["lam", "sigma", "drift_per_run", "design", "shrink", "diff_DA_ratio", "pick_D_pct", "bias_A", "bias_D"]].to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
