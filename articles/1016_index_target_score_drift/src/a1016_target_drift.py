"""1016 スコアを狙って動くと、スコアと本当の良さはずれていくのか？（架空のデータ）

架空の飲食チェーン200店。本当の良さ Q ＝ スコアで測る面 M ＋ スコアで測らない面 U（どちらも点）。
店のスコア S ＝ M ＋ 見かけだけの上げ H ＋ 測るときの振れ。0期はスコアを評価に使う前、1〜6期は評価に使う。
各期、店は手間1単位のうち k（店ごとの「スコアに寄せる度合い」）を、見かけだけの上げと測らない面を後回しにすることに回す。
ずれる向きはこの置いた動き方から決まる。何期でどれだけずれ、スコア上位の店がどう入れかわるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1016
SRC = "架空の飲食チェーン200店のスコアと本当の良さ（作成者が乱数で作成、seed 1016）"
N_STORE, T_END, TOP = 200, 6, 20
M0, U0, SD0 = 30.0, 30.0, 4.0     # 0期の測る面・測らない面（平均・標準偏差）
SD_MEAS, SD_SHOCK = 2.0, 1.0      # スコアを測るときの振れ・各期の面の振れ
GAIN = 0.5                        # 正直な手間1単位あたりの面の伸び
G, DELTA = 3.0, 0.5               # 見かけだけの上げの効き（スコアの点/単位）・測らない面の後回し（点/単位）
KA, KB = 2.0, 3.0                 # 寄せる度合い k ～ ベータ分布(2,3)（平均0.4）
HEAVY = 0.6


def simulate(rng, g=G, delta=DELTA, n=N_STORE, t_end=T_END, k=None):
    if k is None:
        k = rng.beta(KA, KB, n)
    M = rng.normal(M0, SD0, n); U = rng.normal(U0, SD0, n); H = np.zeros(n)
    out = []
    for t in range(t_end + 1):
        if t > 0:
            M = M + GAIN + rng.normal(0, SD_SHOCK, n)
            U = U + GAIN * (1 - k) - delta * k + rng.normal(0, SD_SHOCK, n)
            H = H + g * k
        S = M + H + rng.normal(0, SD_MEAS, n)
        out.append((t, M.copy(), U.copy(), H.copy(), S, M + U))
    return k, out


def top_idx(x, k=TOP):
    return np.argsort(-x, kind="stable")[:k]


def stats_period(k, M, U, H, S, Q):
    ts, tq = top_idx(S), top_idx(Q)
    return {"r": float(np.corrcoef(S, Q)[0, 1]),
            "hit_pct": 100 * len(set(ts) & set(tq)) / TOP,
            "top_q_minus_mean": float(Q[ts].mean() - Q.mean()),
            "top_heavy_pct": 100 * float((k[ts] > HEAVY).mean()),
            "all_heavy_pct": 100 * float((k > HEAVY).mean())}


def corr_formula(t, g, delta):
    """置いた式から出る相関（k の分散 v を使う）"""
    v = KA * KB / ((KA + KB) ** 2 * (KA + KB + 1))
    vm = SD0 ** 2 + t * SD_SHOCK ** 2
    vu = SD0 ** 2 + t * SD_SHOCK ** 2 + (t * (GAIN + delta)) ** 2 * v
    vh = (g * t) ** 2 * v
    chu = -(g * t) * (t * (GAIN + delta)) * v
    vs, vq = vm + vh + SD_MEAS ** 2, vm + vu
    return (vm + chu) / np.sqrt(vs * vq)


def run(seed, reps, g=G, delta=DELTA, nogame=False):
    rng = np.random.default_rng(seed)
    rows, rise = [], []
    for r in range(reps):
        k = np.zeros(N_STORE) if nogame else None
        k, out = simulate(rng, g, delta, k=k)
        for t, M, U, H, S, Q in out:
            d = stats_period(k, M, U, H, S, Q); d.update(rep=r, period=t); rows.append(d)
        S0, Q0 = out[0][4], out[0][5]
        S6, Q6 = out[-1][4], out[-1][5]
        dS, dQ = S6 - S0, Q6 - Q0
        ti = top_idx(dS)
        rise.append({"mean_dS": float(dS.mean()), "mean_dQ": float(dQ.mean()),
                     "top_rise_dQ": float(dQ[ti].mean()), "top_rise_dS": float(dS[ti].mean()),
                     "top_rise_heavy_pct": 100 * float((k[ti] > HEAVY).mean()),
                     "top_rise_dQ_below_mean_pct": 100 * float((dQ[ti] < dQ.mean()).mean())})
    per = pd.DataFrame(rows).groupby("period").mean().drop(columns="rep")
    return per, pd.DataFrame(rise).mean()


def main():
    t0 = time.time()
    # 1) 1回分（data に置く）
    rng = np.random.default_rng(SEED)
    k, out = simulate(rng)
    panel = []
    for t, M, U, H, S, Q in out:
        panel.append(pd.DataFrame({"store_id": np.arange(1, N_STORE + 1), "period": t, "k_lean": k.round(3),
                                   "measured_M": M.round(2), "unmeasured_U": U.round(2), "cosmetic_H": H.round(2),
                                   "score_S": S.round(2), "true_Q": Q.round(2)}))
    pd.concat(panel).to_csv(DATA / "stores_panel.csv", index=False)
    one = {f"period{t}": {kk: round(v, 3) for kk, v in stats_period(k, *o[1:]).items()}
           for t, o in [(0, out[0]), (T_END, out[-1])]}

    # 2) 500回の平均（基本と、だれも寄せないとき）
    per, rise = run(SEED * 10, 500)
    per0, rise0 = run(SEED * 10 + 1, 500, nogame=True)
    per["corr_formula"] = [corr_formula(t, G, DELTA) for t in per.index]
    per0["corr_formula"] = [corr_formula(t, 0.0, 0.0) if t == 0 else
                            (SD0 ** 2 + t) / np.sqrt((SD0 ** 2 + t + SD_MEAS ** 2) * (2 * (SD0 ** 2 + t))) for t in per0.index]
    tab = pd.concat([per.add_prefix("base_"), per0.add_prefix("nogame_")], axis=1).round(3)
    tab.to_csv(RES / "by_period.csv")
    fdiff = float(max((per.r - per.corr_formula).abs().max(), (per0.r - per0.corr_formula).abs().max()))

    # 3) 確かめ：見かけの上げの効き g × 測らない面の後回し δ（12通り、各200回）
    grid = []
    for gi, g in enumerate([0.0, 1.0, 3.0, 5.0]):
        for di, d in enumerate([0.0, 0.5, 1.0]):
            p, rs = run(SEED * 100 + gi * 10 + di, 200, g, d)
            grid.append({"g": g, "delta": d, "corr_p0": round(p.r.iloc[0], 3), "corr_p6": round(p.r.iloc[-1], 3),
                         "corr_p6_formula": round(float(corr_formula(T_END, g, d)), 3),
                         "hit_p0": round(p.hit_pct.iloc[0], 2), "hit_p6": round(p.hit_pct.iloc[-1], 2),
                         "top_heavy_p6": round(p.top_heavy_pct.iloc[-1], 2),
                         "mean_dS": round(rs.mean_dS, 2), "mean_dQ": round(rs.mean_dQ, 2),
                         "top_rise_dQ": round(rs.top_rise_dQ, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_g_delta.csv", index=False)
    g_nz = grid[(grid.g > 0)]

    main_json = {
        "seed": SEED, "stores": N_STORE, "periods": T_END, "top": TOP,
        "settings": {"g": G, "delta": DELTA, "k_beta": [KA, KB], "heavy_k_over": HEAVY},
        "one_run": one,
        "reps_500": {
            "corr_p0": round(per.r.iloc[0], 3), "corr_p6": round(per.r.iloc[-1], 3),
            "corr_formula_p0": round(float(per.corr_formula.iloc[0]), 3),
            "corr_formula_p6": round(float(per.corr_formula.iloc[-1]), 3),
            "corr_p6_nogame": round(per0.r.iloc[-1], 3),
            "formula_vs_sim_max_diff": round(fdiff, 3),
            "hit_p0": round(per.hit_pct.iloc[0], 2), "hit_p6": round(per.hit_pct.iloc[-1], 2),
            "hit_p6_nogame": round(per0.hit_pct.iloc[-1], 2),
            "top_q_minus_mean_p0": round(per.top_q_minus_mean.iloc[0], 2),
            "top_q_minus_mean_p6": round(per.top_q_minus_mean.iloc[-1], 2),
            "top_heavy_p0": round(per.top_heavy_pct.iloc[0], 2), "top_heavy_p6": round(per.top_heavy_pct.iloc[-1], 2),
            "all_heavy": round(per.all_heavy_pct.iloc[-1], 2),
            "mean_score_rise": round(rise.mean_dS, 2), "mean_true_rise": round(rise.mean_dQ, 2),
            "mean_score_rise_nogame": round(rise0.mean_dS, 2), "mean_true_rise_nogame": round(rise0.mean_dQ, 2),
            "top_rise_true_rise": round(rise.top_rise_dQ, 2), "top_rise_score_rise": round(rise.top_rise_dS, 2),
            "top_rise_heavy_pct": round(rise.top_rise_heavy_pct, 2),
            "top_rise_true_below_mean_pct": round(rise.top_rise_dQ_below_mean_pct, 2),
            "top_rise_true_rise_nogame": round(rise0.top_rise_dQ, 2),
        },
        "grid_corr_p6_formula_max_diff": round(float((grid.corr_p6 - grid.corr_p6_formula).abs().max()), 3),
        "grid_ranges_g_positive": {
            "corr_p6": [float(g_nz.corr_p6.min()), float(g_nz.corr_p6.max())],
            "hit_p6": [float(g_nz.hit_p6.min()), float(g_nz.hit_p6.max())],
            "top_rise_dQ": [float(g_nz.top_rise_dQ.min()), float(g_nz.top_rise_dQ.max())],
        },
    }

    # 図1：相関の動き
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(per.index, per.r, color=ORANGE, marker="o", lw=2, label="店ごとに寄せる（基本）")
    ax.plot(per0.index, per0.r, color=BLUE, marker="o", lw=2, label="どの店も寄せない")
    ax.plot(per.index, per.corr_formula, color=INK, lw=0, marker="_", ms=14, label="置いた式の値")
    ax.plot(per0.index, per0.corr_formula, color=INK, lw=0, marker="_", ms=14)
    for t in [0, T_END]:
        ax.text(t, per.r.iloc[t] - 0.045, f"{round(per.r.iloc[t], 3):g}", ha="center", fontsize=9, color=INK)
    ax.text(T_END, per0.r.iloc[-1] + 0.025, f"{round(per0.r.iloc[-1], 3):g}", ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(T_END + 1)); ax.set_xticklabels(["0期\n（使う前）"] + [f"{t}期" for t in range(1, T_END + 1)])
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("スコアと本当の良さの相関")
    ax.set_title("スコアを評価に使うと、相関が下がっていく", loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1016_corr.png", SRC + "。500回の平均")

    # 図2：スコア上位20店の中身
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.plot(per.index, per.hit_pct, color=BLUE, marker="o", lw=2, label="本当の上位20店に入っていた割合")
    ax.plot(per.index, per.top_heavy_pct, color=ORANGE, marker="o", lw=2, label="強く寄せる店（k＞0.6）の割合")
    ax.axhline(per.all_heavy_pct.iloc[-1], color=GRAY, lw=0.8, ls="--", label="全店のうち強く寄せる店の割合")
    for t in [0, T_END]:
        ax.text(t, per.hit_pct.iloc[t] + 2.5, f"{per.hit_pct.iloc[t]:.1f}%", ha="center", fontsize=9, color=INK)
        ax.text(t, per.top_heavy_pct.iloc[t] + 2.5, f"{per.top_heavy_pct.iloc[t]:.1f}%", ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(T_END + 1)); ax.set_xticklabels(["0期\n（使う前）"] + [f"{t}期" for t in range(1, T_END + 1)])
    ax.set_ylim(0, 100)
    ax.set_ylabel("スコア上位20店のうち（%）")
    ax.set_title("スコア上位20店が、強く寄せる店に入れかわる", loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1016_top20.png", SRC + "。500回の平均")

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for d, c, lab in [(0.0, GRAY, "測らない面の後回し 0"), (0.5, BLUE, "0.5（基本）"), (1.0, ORANGE, "1.0")]:
        g = grid[grid.delta == d]
        ax.plot(g.g, g.corr_p6, marker="o", color=c, lw=2, label=lab)
    ax.axhline(per.r.iloc[0], color=INK, lw=0.8, ls=":", label="0期の相関（%.2f）" % per.r.iloc[0])
    ax.set_xticks([0, 1, 3, 5])
    ax.set_xlabel("見かけだけの上げの効き（手間1単位あたりのスコアの点）")
    ax.set_ylabel("6期のスコアと本当の良さの相関")
    ax.set_ylim(0, 0.8)
    ax.set_title("ずれの大きさは、見かけの上げやすさで大きく変わる", loc="left")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a1016_grid.png", SRC + "。12通り、各200回")

    with open(RES / "a1016_main.json", "w", encoding="utf-8") as f:
        json.dump(main_json, f, ensure_ascii=False, indent=1)
    print(json.dumps(main_json, ensure_ascii=False, indent=1))
    print(tab.to_string()); print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
