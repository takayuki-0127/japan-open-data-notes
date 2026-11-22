"""904 「〜の人の8割が〜」と「〜の人の8割は〜」は同じなのか？（架空のデータ）

架空のネットショップの客2万人。客ごとに1年の買い物の額を置き、クーポンを使う確率は
買い物の額が多い客ほど高くなるように置く（ロジスティックの形）。
「上位10%の客の8割がクーポンを使った」が成り立つように置いたうえで、
逆向きの割合「クーポンを使った客のうち、上位10%の客は何割か」を数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 904
SRC = "架空のネットショップの客とクーポン（作成者が乱数で作成、seed 904）"
N_MAIN, N_GRID = 20000, 200000
R_BASE, S_BASE, T_BASE = 0.40, 0.10, 0.80   # クーポンを使った客の割合・上位の客の割合・上位の客のうちクーポンを使った割合
KS = [0.01, 0.05, 0.10, 0.20, 0.30, 0.50]


def sig(x):
    return 1 / (1 + np.exp(-x))


def solve_a(z, b, r):
    lo, hi = -40.0, 40.0
    for _ in range(50):
        a = (lo + hi) / 2
        if sig(a + b * z).mean() < r:
            lo = a
        else:
            hi = a
    return (lo + hi) / 2


def calibrate(z, r, s, target):
    """全体の使う割合 r、上位 s の客のうち使う割合 target になる (a, b) を求める（期待値で合わせる）。
    速さのため、z の分布を4,000個の分位点で代表させて合わせる"""
    z = np.quantile(z, (np.arange(4000) + 0.5) / 4000)
    top = z >= np.quantile(z, 1 - s)
    lo, hi = 0.0, 30.0
    for _ in range(40):
        b = (lo + hi) / 2
        a = solve_a(z, b, r)
        if sig(a + b * z)[top].mean() < target:
            lo = b
        else:
            hi = b
    b = (lo + hi) / 2
    return solve_a(z, b, r), b


def rates(z, used, s):
    top = z >= np.quantile(z, 1 - s)
    pba = used[top].mean()
    pab = (top & used).sum() / used.sum()
    return {"top_share": round(float(top.mean()), 4), "coupon_share": round(float(used.mean()), 4),
            "P_coupon_given_top": round(float(pba), 4), "P_top_given_coupon": round(float(pab), 4),
            "P_coupon_given_rest": round(float(used[~top].mean()), 4),
            "lift": round(float(pba / used.mean()), 3)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 基本：客2万人
    z = rng.normal(0, 1, N_MAIN)
    spend = np.round(20000 * np.exp(0.8 * z), -2).astype(int)
    a, b = calibrate(z, R_BASE, S_BASE, T_BASE)
    used = rng.uniform(0, 1, N_MAIN) < sig(a + b * z)
    top = z >= np.quantile(z, 1 - S_BASE)
    pd.DataFrame({"customer_id": np.arange(1, N_MAIN + 1), "spend_yen": spend, "top10": top.astype(int),
                  "coupon": used.astype(int)}).to_csv(DATA / "customers.csv", index=False)
    tab = {"top_and_coupon": int((top & used).sum()), "top_no_coupon": int((top & ~used).sum()),
           "rest_and_coupon": int((~top & used).sum()), "rest_no_coupon": int((~top & ~used).sum())}
    base = rates(z, used, S_BASE)
    base.update(tab)
    base["top_n"], base["coupon_n"] = int(top.sum()), int(used.sum())
    base["model_a"], base["model_b"] = round(a, 4), round(b, 4)
    base["spend_top10_threshold_yen"] = int(np.sort(spend)[int(N_MAIN * (1 - S_BASE))])
    base["max_P_top_given_coupon"] = round(min(1.0, S_BASE / R_BASE), 4)
    base["formula_P_top_given_coupon"] = round(T_BASE * S_BASE / R_BASE, 4)

    # 2) 「上位」の線の引き方（上位 k%）を変える：同じ客で
    zz = rng.normal(0, 1, N_GRID)
    by_k = []
    for lab, tgt in [("弱い", 0.60), ("基本", 0.80), ("強い", 0.95)]:
        aa, bb = calibrate(zz, R_BASE, S_BASE, tgt)
        u = rng.uniform(0, 1, N_GRID) < sig(aa + bb * zz)
        for k in KS:
            d = rates(zz, u, k)
            d.update({"strength": lab, "P_coupon_given_top10_set": tgt, "k": k})
            by_k.append(d)
    by_k = pd.DataFrame(by_k)
    by_k.to_csv(RES / "by_top_definition.csv", index=False)

    # 3) 「8割が」をそろえたまま、使う客の割合 r と上位の客の割合 s を変える
    grid = []
    for r in [0.2, 0.4, 0.6, 0.8]:
        for s in [0.05, 0.10, 0.20]:
            aa, bb = calibrate(zz, r, s, T_BASE)
            u = rng.uniform(0, 1, N_GRID) < sig(aa + bb * zz)
            d = rates(zz, u, s)
            d.update({"r_set": r, "s_set": s, "formula_P_top_given_coupon": round(T_BASE * s / r, 4), "model_b": round(bb, 3)})
            grid.append(d)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "base_rate_grid.csv", index=False)

    # 4) 確かめ：使う客の割合 × つながりの強さ で、上位10%の行
    sens = []
    for r in [0.2, 0.4, 0.6]:
        for lab, tgt in [("弱い", 0.6 if r < 0.6 else 0.7), ("基本", 0.80), ("強い", 0.95)]:
            aa, bb = calibrate(zz, r, S_BASE, tgt)
            u = rng.uniform(0, 1, N_GRID) < sig(aa + bb * zz)
            d = rates(zz, u, S_BASE)
            d.update({"r_set": r, "strength": lab, "P_coupon_given_top10_set": tgt})
            sens.append(d)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_grid.csv", index=False)

    out = {"main": base, "by_top_definition": by_k.to_dict("records"), "base_rate_grid": grid.to_dict("records"),
           "sensitivity": {"rows": sens.to_dict("records"),
                           "P_top_given_coupon_min": float(sens.P_top_given_coupon.min()),
                           "P_top_given_coupon_max": float(sens.P_top_given_coupon.max()),
                           "grid_P_top_given_coupon_min": float(grid.P_top_given_coupon.min()),
                           "grid_P_top_given_coupon_max": float(grid.P_top_given_coupon.max())}}
    json.dump(out, open(RES / "a904_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ表を2つの向きから読む
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    n_top = tab["top_and_coupon"] + tab["top_no_coupon"]
    n_cp = tab["top_and_coupon"] + tab["rest_and_coupon"]
    rows = [("クーポンを使った客\n（" + f"{n_cp:,}" + "人）", tab["top_and_coupon"] / n_cp, "うち上位10%の客"),
            ("上位10%の客\n（" + f"{n_top:,}" + "人）", tab["top_and_coupon"] / n_top, "うちクーポンを使った客")]
    for i, (lab, v, txt) in enumerate(rows):
        ax.barh(i, v * 100, color=ORANGE, height=0.55)
        ax.barh(i, 100 - v * 100, left=v * 100, color=LIGHT, height=0.55)
        ax.text(v * 100 / 2, i, f"{txt}\n{v*100:.0f}%", ha="center", va="center", fontsize=9, color="white" if v > 0.3 else INK)
    ax.set_yticks([0, 1]); ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlim(0, 100); ax.set_xlabel("%（オレンジは、どちらも「上位10%で、クーポンを使った客」の同じ"
                                         + f"{tab['top_and_coupon']:,}人）")
    ax.set_title("同じ客の表でも、どちらを分母にするかで8割にも2割にもなる")
    save(fig, "a904_two_directions.png", SRC, y=-0.07)

    # 図2：上位の線の引き方
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for lab, ls, lw in [("弱い", ":", 1.2), ("基本", "-", 2.2), ("強い", "--", 1.2)]:
        s = by_k[by_k.strength == lab]
        ax.plot(s.k * 100, s.P_coupon_given_top * 100, color=ORANGE, ls=ls, lw=lw, marker="o", ms=3)
        ax.plot(s.k * 100, s.P_top_given_coupon * 100, color=BLUE, ls=ls, lw=lw, marker="o", ms=3)
    ax.text(31, 87, "上位の客のうち、クーポンを使った割合", color=ORANGE, fontsize=9)
    ax.text(21, 12, "クーポンを使った客のうち、上位の客の割合", color=BLUE, fontsize=9)
    ax.text(21, 3, "実線：基本　破線：つながり強い　点線：弱い", color=GRAY, fontsize=8.5)
    ax.set_xlabel("「上位の客」とする範囲（買い物の額の上位 k%）"); ax.set_ylabel("%")
    ax.set_xticks([1, 5, 10, 20, 30, 50]); ax.set_ylim(0, 100)
    ax.set_title("「上位」を狭くすると、片方は上がり、もう片方は下がる")
    save(fig, "a904_top_definition.png", SRC)

    # 図3：「8割が」をそろえたまま、逆向きの割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.26
    rs = [0.2, 0.4, 0.6, 0.8]
    for k, (s, col) in enumerate([(0.05, LIGHT), (0.10, BLUE), (0.20, INK)]):
        g = grid[grid.s_set == s]
        xs = np.arange(4) + (k - 1) * w
        ax.bar(xs, g.P_top_given_coupon * 100, w, color=col, label=f"上位の客が全体の{s*100:.0f}%")
        for xx, v in zip(xs, g.P_top_given_coupon * 100):
            ax.text(xx, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(np.arange(4)); ax.set_xticklabels([f"使った客が全体の{r*100:.0f}%" for r in rs], fontsize=9)
    ax.set_ylabel("クーポンを使った客のうち、上位の客の割合（%）"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title(f"どれも「上位の客の8割が使った」。逆向きは{grid.P_top_given_coupon.min()*100:.0f}〜{grid.P_top_given_coupon.max()*100:.0f}%")
    save(fig, "a904_base_rate.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
