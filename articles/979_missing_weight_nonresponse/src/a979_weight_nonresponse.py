"""979 欠けやすい人に重みを付けると、どこまで戻せるのか？（架空のデータ）

架空の通販の会員2万人。全員の「満足しているか」を作成者が置き、4,000人にアンケートをお願いする。
答えるかどうかは、名簿で分かる利用頻度・会員年数と、名簿では分からない「満足しているか」そのもので決まる。
答えた人に、名簿の区分ごとの回答率の逆数で重みを付け、満足の割合がどこまで本当に戻るかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 979
SRC = "架空の通販の会員アンケート（作成者が乱数で作成、seed 979）"
N_POP, N_INV = 20000, 4000
PF, PT = np.array([.45, .35, .20]), np.array([.30, .40, .30])
METHODS = ["重みなし", "利用頻度（3区分）", "利用頻度×会員年数（9区分）", "9区分×入会した月（108区分）"]
Z95 = 1.959964


def expit(v):
    return 1 / (1 + np.exp(-v))


def p_sat(f, t):
    return expit(-0.3 + 0.7 * f + 0.3 * t)


def calib_c(beta, gamma, rr):
    """全体の回答率の見込みが rr になる定数 c（区分の割合と満足の割合から、二分法）"""
    lo, hi = -10.0, 5.0
    for _ in range(80):
        c = (lo + hi) / 2
        tot = 0.0
        for f in range(3):
            for t in range(3):
                p = p_sat(f, t)
                a = c + beta * (0.8 * f + 0.4 * t)
                tot += PF[f] * PT[t] * (p * expit(a + gamma) + (1 - p) * expit(a))
        lo, hi = (c, hi) if tot < rr else (lo, c)
    return (lo + hi) / 2


def formula(beta, gamma, rr):
    """十分に人数が多いときの、重みなし・3区分・9区分の見積もりの行き先（式）と本当の値"""
    c = calib_c(beta, gamma, rr)
    truth = sum(PF[f] * PT[t] * p_sat(f, t) for f in range(3) for t in range(3))
    num = np.zeros((3, 3)); den = np.zeros((3, 3))
    for f in range(3):
        for t in range(3):
            p = p_sat(f, t); a = c + beta * (0.8 * f + 0.4 * t)
            num[f, t] = PF[f] * PT[t] * p * expit(a + gamma)
            den[f, t] = PF[f] * PT[t] * (p * expit(a + gamma) + (1 - p) * expit(a))
    raw = num.sum() / den.sum()
    w3 = sum(PF[f] * num[f].sum() / den[f].sum() for f in range(3))
    w9 = sum(PF[f] * PT[t] * num[f, t] / den[f, t] for f in range(3) for t in range(3))
    return {"truth": truth, "raw": raw, "w3": w3, "w9": w9}


def make_pop(rng):
    f = rng.choice(3, N_POP, p=PF)
    t = rng.choice(3, N_POP, p=PT)
    mon = rng.integers(0, 12, N_POP)
    y = (rng.random(N_POP) < p_sat(f, t)).astype(int)
    return f, t, mon, y


def survey(rng, beta, gamma, rr, c=None):
    f, t, mon, y = make_pop(rng)
    if c is None:
        c = calib_c(beta, gamma, rr)
    inv = rng.choice(N_POP, N_INV, replace=False)
    r = np.zeros(N_POP, bool)
    pr = expit(c + beta * (0.8 * f[inv] + 0.4 * t[inv]) + gamma * y[inv])
    r[inv] = rng.random(N_INV) < pr
    invm = np.zeros(N_POP, bool); invm[inv] = True
    return f, t, mon, y, r, invm


def poststrat(cell_pop, cell_resp, yresp):
    """区分ごとの名簿の人数で重みを付けた割合と、その標準誤差・Kish の有効な人数・空の区分の数"""
    K = int(max(cell_pop.max(), cell_resp.max() if len(cell_resp) else 0)) + 1
    Np = np.bincount(cell_pop, minlength=K).astype(float)
    nr = np.bincount(cell_resp, minlength=K).astype(float)
    sy = np.bincount(cell_resp, weights=yresp, minlength=K)
    ok = nr > 0
    W = Np[ok] / Np[ok].sum()
    pc = sy[ok] / nr[ok]
    est = float((W * pc).sum())
    se = float(np.sqrt((W ** 2 * pc * (1 - pc) / nr[ok]).sum()))
    w = (Np / np.where(nr > 0, nr, 1))[cell_resp]           # 1人ごとの重み
    neff = float(w.sum() ** 2 / (w ** 2).sum())
    return est, se, neff, int((~ok & (Np > 0)).sum())


def estimates(f, t, mon, y, r):
    truth = y.mean()
    yr = y[r]; n = int(r.sum())
    out = {}
    p = yr.mean()
    out[METHODS[0]] = (p, np.sqrt(p * (1 - p) / n), float(n), 0)
    for mth, cell in [(METHODS[1], f), (METHODS[2], f * 3 + t), (METHODS[3], (f * 3 + t) * 12 + mon)]:
        out[mth] = poststrat(cell, cell[r], yr)
    return truth, n, out


def run(rng, reps, beta, gamma, rr):
    c = calib_c(beta, gamma, rr)
    rows = []
    for k in range(reps):
        f, t, mon, y, r, _ = survey(rng, beta, gamma, rr, c)
        truth, n, out = estimates(f, t, mon, y, r)
        for mth, (est, se, neff, empty) in out.items():
            se_neff = np.sqrt(est * (1 - est) / neff)               # Kish の有効な人数で出した幅
            rows.append({"rep": k, "method": mth, "truth": truth, "n_resp": n, "est": est,
                         "bias": (est - truth) * 100, "neff": neff, "empty": empty,
                         "cover_naive": abs(est - truth) <= Z95 * np.sqrt(est * (1 - est) / n),
                         "cover_neff": abs(est - truth) <= Z95 * se_neff,
                         "cover_strat": abs(est - truth) <= Z95 * se})
    return pd.DataFrame(rows)


def summarize(d):
    g = d.groupby("method", sort=False)
    s = pd.DataFrame({"bias": g.bias.mean(), "sd": g.est.std() * 100,
                      "rmse": np.sqrt(g.bias.apply(lambda v: (v ** 2).mean())),
                      "neff": g.neff.mean(), "empty_cells": g.empty.mean(),
                      "cover_naive": g.cover_naive.mean() * 100, "cover_neff": g.cover_neff.mean() * 100,
                      "cover_strat": g.cover_strat.mean() * 100})
    raw = s.loc[METHODS[0], "bias"]
    s["recovered"] = (1 - s["bias"] / raw) * 100 if abs(raw) > 1e-9 else np.nan
    return s


def main():
    rng = np.random.default_rng(SEED)
    BETA, GAMMA, RR = 1.0, 0.4, 0.25

    # 1回分（data/）
    f, t, mon, y, r, invm = survey(np.random.default_rng(SEED), BETA, GAMMA, RR)
    pop = pd.DataFrame({"member_id": np.arange(1, N_POP + 1), "freq": f, "tenure": t, "join_month": mon + 1,
                        "satisfied": y, "invited": invm.astype(int), "responded": r.astype(int)})
    pop.to_csv(DATA / "members.csv", index=False)
    cells = pop.groupby(["freq", "tenure"]).agg(members=("member_id", "size"), satisfied_true=("satisfied", "mean"),
                                                invited=("invited", "sum"), respondents=("responded", "sum"))
    cells["response_rate"] = cells.respondents / cells.invited
    resp_sat = pop[pop.responded == 1].groupby(["freq", "tenure"]).satisfied.mean()
    cells["satisfied_respondents"] = resp_sat
    cells["weight"] = cells.members / cells.respondents
    cells.round(4).to_csv(DATA / "cells_one_draw.csv")
    truth1, n1, out1 = estimates(f, t, mon, y, r)
    one = {"truth": round(truth1 * 100, 2), "respondents": n1,
           "est": {m: round(v[0] * 100, 2) for m, v in out1.items()},
           "neff": {m: round(v[2], 1) for m, v in out1.items()},
           "empty_cells": {m: v[3] for m, v in out1.items()},
           "weight_min_max_9": [round(float(cells.weight.min()), 2), round(float(cells.weight.max()), 2)],
           "response_rate_min_max_9": [round(float(cells.response_rate.min()) * 100, 2), round(float(cells.response_rate.max()) * 100, 2)],
           "truth_cells_min_max_9": [round(float(cells.satisfied_true.min()) * 100, 2), round(float(cells.satisfied_true.max()) * 100, 2)]}

    # 2) 基本の置き方、500回
    base = run(rng, 500, BETA, GAMMA, RR)
    s = summarize(base)
    s.round(3).to_csv(RES / "methods_base.csv")
    fm = formula(BETA, GAMMA, RR)

    # 3) 確かめ：満足そのものの答えやすさ γ × 名簿で分かる答えやすさの強さ β（各100回）
    grid = []
    for gamma in [0.0, 0.4, 0.8, 1.2]:
        for beta in [0.5, 1.0, 2.0]:
            d = run(np.random.default_rng(SEED * 100 + int(gamma * 10) * 7 + int(beta * 10)), 100, beta, gamma, RR)
            ss = summarize(d)
            fo = formula(beta, gamma, RR)
            for mth in METHODS:
                grid.append({"gamma": gamma, "odds_ratio": round(float(np.exp(gamma)), 3), "beta": beta,
                             "method": mth, "bias": round(ss.loc[mth, "bias"], 3),
                             "recovered": round(ss.loc[mth, "recovered"], 1) if not np.isnan(ss.loc[mth, "recovered"]) else None,
                             "sd": round(ss.loc[mth, "sd"], 3), "cover_strat": round(ss.loc[mth, "cover_strat"], 1)})
            for key, mth in [("raw", METHODS[0]), ("w3", METHODS[1]), ("w9", METHODS[2])]:
                grid[-4 + METHODS.index(mth)]["formula_bias"] = round((fo[key] - fo["truth"]) * 100, 3)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_gamma_beta.csv", index=False)

    # 4) 確かめ：回答率（10%・25%・50%）で、区分を細かくした重みの振れ（基本の γ・β、各200回）
    rrg = []
    for rr in [0.10, 0.25, 0.50]:
        d = run(np.random.default_rng(SEED * 1000 + int(rr * 100)), 200, BETA, GAMMA, rr)
        ss = summarize(d)
        for mth in METHODS:
            rrg.append({"response_rate": rr, "method": mth, "n_resp": round(d.n_resp.mean(), 1),
                        "bias": round(ss.loc[mth, "bias"], 3), "sd": round(ss.loc[mth, "sd"], 3),
                        "rmse": round(ss.loc[mth, "rmse"], 3), "neff": round(ss.loc[mth, "neff"], 1),
                        "empty_cells": round(ss.loc[mth, "empty_cells"], 2),
                        "cover_strat": round(ss.loc[mth, "cover_strat"], 1)})
    rrg = pd.DataFrame(rrg)
    rrg.to_csv(RES / "grid_response_rate.csv", index=False)

    g0 = grid[(grid.gamma == 0)]
    out = {"one_draw": one,
           "base_500reps": {"setting": {"beta": BETA, "gamma": GAMMA, "odds_ratio_satisfied": round(float(np.exp(GAMMA)), 3),
                                        "response_rate": RR},
                            "truth_mean": round(float(base.truth.mean() * 100), 3),
                            "n_resp_mean": round(float(base.n_resp.mean()), 1),
                            "methods": {m: {k: round(float(v), 3) for k, v in s.loc[m].items()} for m in METHODS},
                            "formula_bias": {k: round((fm[k] - fm["truth"]) * 100, 3) for k in ["raw", "w3", "w9"]}},
           "grid": {"recovered_9_range_by_gamma": {str(gm): [float(grid[(grid.gamma == gm) & (grid.method == METHODS[2])].recovered.min()),
                                                             float(grid[(grid.gamma == gm) & (grid.method == METHODS[2])].recovered.max())]
                                                   for gm in [0.0, 0.4, 0.8, 1.2]},
                    "bias_raw_range": [float(grid[grid.method == METHODS[0]].bias.min()), float(grid[grid.method == METHODS[0]].bias.max())],
                    "bias_9_range": [float(grid[grid.method == METHODS[2]].bias.min()), float(grid[grid.method == METHODS[2]].bias.max())],
                    "bias_9_gamma0_range": [float(g0[g0.method == METHODS[2]].bias.min()), float(g0[g0.method == METHODS[2]].bias.max())],
                    "max_abs_gap_sim_vs_formula": round(float((grid.bias - grid.formula_bias).abs().max()), 3)}}
    json.dump(out, open(RES / "a979_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の区分ごとの回答率と、答えた人の満足の割合・本当の割合
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.9))
    cl = cells.reset_index()
    lab = [f"{['少', '中', '多'][a]}・{['1年未満', '1〜3年', '3年以上'][b]}" for a, b in zip(cl.freq, cl.tenure)]
    ax = axes[0]
    ax.barh(range(9)[::-1], cl.response_rate * 100, color=BLUE)
    ax.set_yticks(range(9)[::-1]); ax.set_yticklabels(lab, fontsize=8.5)
    ax.set_xlabel("回答率（%、お願いした人のうち）"); ax.set_title("利用頻度・会員年数ごとの回答率", fontsize=10)
    ax = axes[1]
    ax.plot(cl.satisfied_true * 100, range(9)[::-1], "o", color=INK, label="会員全員（本当）")
    ax.plot(cl.satisfied_respondents * 100, range(9)[::-1], "o", color=ORANGE, label="答えた人")
    ax.set_yticks(range(9)[::-1]); ax.set_yticklabels([])
    ax.set_xlabel("満足の割合（%）"); ax.set_title("同じ区分の中でも、答えた人のほうが高い", fontsize=10)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    fig.suptitle("名簿の区分で回答率は大きく違い、区分の中にもずれが残る（1回分）", fontsize=12)
    fig.tight_layout()
    save(fig, "a979_cells.png", SRC)

    # 図2：γ ごとの、重みなし・3区分・9区分のずれ（β=1）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    gb = grid[grid.beta == 1.0]
    xs = np.arange(4); wdt = 0.26
    for i, (mth, col) in enumerate(zip(METHODS[:3], [GRAY, LIGHT, BLUE])):
        v = gb[gb.method == mth].bias.values
        ax.bar(xs + (i - 1) * wdt, v, wdt, color=col, label=mth)
        for xx, vv in zip(xs + (i - 1) * wdt, v):
            ax.text(xx, vv + 0.15, f"{vv:.1f}", ha="center", fontsize=7.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{np.exp(gm):.2f}倍" + ("\n（名簿の区分だけで決まる）" if gm == 0 else "") for gm in [0, .4, .8, 1.2]])
    ax.set_xlabel("満足している人の答えやすさ（同じ区分の中での回答のオッズの倍率、作成者が置いた値）")
    ax.set_ylabel("満足の割合のずれ（ポイント）")
    ax.axhline(0, color=INK, lw=.8)
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("重みで戻せるのは名簿の区分で説明できる分だけ（100回の平均）", fontsize=11)
    save(fig, "a979_by_gamma.png", SRC, y=-0.06)

    # 図3：回答率と区分の細かさ：ずれと振れ
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    for mth, col in zip(METHODS, [GRAY, LIGHT, BLUE, ORANGE]):
        q = rrg[rrg.method == mth]
        axes[0].plot(q.response_rate * 100, q.sd, "o-", color=col, label=mth)
        axes[1].plot(q.response_rate * 100, q.neff, "o-", color=col, label=mth)
    axes[0].set_xlabel("回答率（%）"); axes[0].set_ylabel("見積もりの振れ（標準偏差、ポイント）")
    axes[1].set_xlabel("回答率（%）"); axes[1].set_ylabel("重みを付けたあとの有効な人数（人）")
    axes[0].set_title("区分を細かくすると振れが大きくなる", fontsize=10)
    axes[1].set_title("重みのばらつきで、使える人数が減る", fontsize=10)
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("回答率と区分の細かさ（200回）", fontsize=12)
    fig.tight_layout()
    save(fig, "a979_rate.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
