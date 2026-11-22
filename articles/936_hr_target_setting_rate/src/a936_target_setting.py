"""936 目標達成率は、目標の置き方でどれだけ変わるのか？（架空のデータ）

架空の会社の営業200人。人ごとに「本当の力」（その人が平均的な年に上げる売上）を置き、
前年と今年の売上は、本当の力に年ごとの振れを掛けたものとする。
同じ今年の売上を、4つの目標の置き方で割って達成率を出し、達成率の順位が本当の力の順位とどれだけ合うかを数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 936
SRC = "架空の会社の営業200人の目標と売上（作成者が乱数で作成、seed 936）"
N = 200
BASE = {"s_a": 0.25, "s_y": 0.15, "k_prev": 1.10, "s_m": 0.10, "u_max": 0.30}
MED = 1000.0  # 本当の力の中央値（万円）
METHODS = ["一律の目標", "前年実績×1.1", "上司の見立て", "自己申告"]


def ranks(x):
    r = np.empty_like(x)
    r[np.argsort(x, axis=-1)] = np.arange(x.shape[-1])
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def make(rng, n=N, s_a=BASE["s_a"], s_y=BASE["s_y"], k_prev=BASE["k_prev"], s_m=BASE["s_m"], u_max=BASE["u_max"]):
    a = MED * np.exp(rng.normal(0, s_a, n))           # 本当の力
    e_last, e_this = rng.normal(0, s_y, n), rng.normal(0, s_y, n)
    last = a * np.exp(e_last)                         # 前年の売上
    this = a * np.exp(e_this)                         # 今年の売上
    u = rng.uniform(0, u_max, n)                      # 自己申告で低めにする幅
    e_m = rng.normal(0, s_m, n)                       # 上司の見立ての外れ
    t = {"一律の目標": np.full(n, np.median(last)),
         "前年実績×1.1": k_prev * last,
         "上司の見立て": a * np.exp(e_m),
         "自己申告": a * np.exp(-u)}
    e = {"this": e_this, "last": e_last, "m": e_m, "u": u}
    return a, last, this, e, t


def metrics(a, this, e, t):
    out = {}
    u = e["u"]
    top_a = set(np.argsort(-a)[:N // 5])
    for m in METHODS:
        r = this / t[m]
        top_r = set(np.argsort(-r)[:N // 5])
        out[m] = {"rho_rate_ability": spearman(r, a), "rho_rate_sales": spearman(r, this),
                  "share_ge_100": float((r >= 1).mean()), "top20_hit": len(top_a & top_r) / (N // 5),
                  "rho_rate_u": spearman(r, u), "rho_rate_luck_this": spearman(r, e["this"]),
                  "rho_rate_luck_last": spearman(r, e["last"]), "rho_rate_manager_err": spearman(r, e["m"])}
    out["売上そのもの"] = {"rho_rate_ability": spearman(this, a), "rho_rate_sales": 1.0,
                       "share_ge_100": float("nan"),
                       "top20_hit": len(top_a & set(np.argsort(-this)[:N // 5])) / (N // 5),
                       "rho_rate_u": spearman(this, u), "rho_rate_luck_this": spearman(this, e["this"]),
                       "rho_rate_luck_last": spearman(this, e["last"]), "rho_rate_manager_err": spearman(this, e["m"])}
    return out


def run(seed0, reps, **kw):
    acc = []
    for r in range(reps):
        rng = np.random.default_rng(seed0 + r)
        a, last, this, e, t = make(rng, **kw)
        acc.append(metrics(a, this, e, t))
    keys = METHODS + ["売上そのもの"]
    return {m: {k: float(np.mean([x[m][k] for x in acc])) for k in acc[0][m]} for m in keys}


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1回分のデータ
    a, last, this, e, t = make(rng)
    u = e["u"]
    df = pd.DataFrame({"person": np.arange(1, N + 1), "ability": a, "sales_last": last, "sales_this": this,
                       "self_lower": u})
    cols = {"一律の目標": "flat", "前年実績×1.1": "prev110", "上司の見立て": "manager", "自己申告": "self"}
    for m in METHODS:
        df[f"target_{cols[m]}"] = t[m]
        df[f"rate_{cols[m]}"] = this / t[m]
    df.round(4).to_csv(DATA / "sales_people.csv", index=False)
    one = metrics(a, this, e, t)

    # 2) 基本の置き方：200回の平均
    base = run(SEED * 1000, 200)
    rows = [{"method": m, **{k: round(v, 3) for k, v in base[m].items()}} for m in METHODS + ["売上そのもの"]]
    pd.DataFrame(rows).to_csv(RES / "methods_base.csv", index=False)

    # 3) 確かめ：人の力の差 s_a × 年の振れ s_y（9通り、各100回）
    grid = []
    for i, s_a in enumerate([0.15, 0.25, 0.40]):
        for j, s_y in enumerate([0.08, 0.15, 0.25]):
            g = run(SEED * 10000 + 1000 * (3 * i + j), 100, s_a=s_a, s_y=s_y)
            for m in METHODS + ["売上そのもの"]:
                grid.append({"s_a": s_a, "s_y": s_y, "method": m,
                             "rho_rate_ability": round(g[m]["rho_rate_ability"], 3),
                             "share_ge_100": round(g[m]["share_ge_100"], 3),
                             "top20_hit": round(g[m]["top20_hit"], 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_spread_noise.csv", index=False)

    # 4) 確かめ：前年に掛ける倍率（達成した人の割合と式）
    kk = []
    for i, k in enumerate([1.00, 1.05, 1.10, 1.20]):
        g = run(SEED * 20000 + 1000 * i, 100, k_prev=k)
        f = 1 - phi(math.log(k) / (BASE["s_y"] * math.sqrt(2)))
        kk.append({"k_prev": k, "share_ge_100": round(g["前年実績×1.1"]["share_ge_100"], 3),
                   "formula": round(f, 3), "rho_rate_ability": round(g["前年実績×1.1"]["rho_rate_ability"], 3)})
    kk = pd.DataFrame(kk)
    kk.to_csv(RES / "by_prev_multiplier.csv", index=False)

    # 5) 確かめ：上司の見立ての外れ s_m
    mm = []
    for i, s_m in enumerate([0.0, 0.05, 0.10, 0.20, 0.40]):
        g = run(SEED * 30000 + 1000 * i, 100, s_m=s_m)
        mm.append({"s_m": s_m, "rho_rate_ability": round(g["上司の見立て"]["rho_rate_ability"], 3),
                   "top20_hit": round(g["上司の見立て"]["top20_hit"], 3)})
    mm = pd.DataFrame(mm)
    mm.to_csv(RES / "by_manager_error.csv", index=False)

    # 5b) 確かめ：目標が本当の力をどれだけ映すか w（0＝一律、1＝上司の見立て）× 年の振れ
    ww = []
    for j, s_y in enumerate([0.08, 0.15, 0.25]):
        for i, w in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
            vals = []
            for r in range(100):
                g = np.random.default_rng(SEED * 40000 + 1000 * (5 * j + i) + r)
                a2, l2, th2, e2, t2 = make(g, s_y=s_y)
                tw = np.median(l2) ** (1 - w) * t2["上司の見立て"] ** w
                vals.append(spearman(th2 / tw, a2))
            ww.append({"s_y": s_y, "w": w, "rho_rate_ability": round(float(np.mean(vals)), 3)})
    ww = pd.DataFrame(ww)
    ww.to_csv(RES / "by_target_weight.csv", index=False)

    # 6) 同じ売上でも達成率の順が逆になる組の割合（基本、1回分）
    def reversed_pairs(r):
        i, j = np.triu_indices(N, 1)
        return float((np.sign(this[i] - this[j]) != np.sign(r[i] - r[j])).mean())
    rev = {m: round(reversed_pairs(this / t[m]), 3) for m in METHODS}

    rf = grid[grid.method != "売上そのもの"]
    out = {"base_200reps": rows,
           "grid_range": {m: {"rho_min": float(rf[rf.method == m].rho_rate_ability.min()),
                              "rho_max": float(rf[rf.method == m].rho_rate_ability.max()),
                              "share_min": float(rf[rf.method == m].share_ge_100.min()),
                              "share_max": float(rf[rf.method == m].share_ge_100.max())} for m in METHODS},
           "by_prev_multiplier": kk.to_dict("records"), "by_manager_error": mm.to_dict("records"),
           "by_target_weight": ww.to_dict("records"),
           "one_draw": {m: {k: round(v, 3) for k, v in one[m].items()} for m in one},
           "one_draw_reversed_pairs_vs_sales": rev,
           "one_draw_flat_target": round(float(np.median(last)), 1),
           "params": {**BASE, "n": N, "median_ability": MED}}
    # 図1：達成率が何と順位が合うか（本当の力・今年の運）
    b = pd.DataFrame(rows).set_index("method")
    labels = ["売上そのもの"] + METHODS
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    y = np.arange(len(labels))[::-1]
    v1 = [b.loc[m, "rho_rate_ability"] for m in labels]
    v2 = [b.loc[m, "rho_rate_luck_this"] for m in labels]
    ax.barh(y + 0.2, v1, height=0.38, color=BLUE, label="本当の力")
    ax.barh(y - 0.2, v2, height=0.38, color=ORANGE, label="今年の売上の振れ（運）")
    for yy, a1, a2 in zip(y, v1, v2):
        ax.text(max(a1, 0) + 0.02, yy + 0.2, f"{0 if abs(a1) < 0.005 else a1:.2f}", va="center", fontsize=8.5)
        ax.text(max(a2, 0) + 0.02, yy - 0.2, f"{a2:.2f}", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_xlim(-0.1, 1.45); ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_xlabel("達成率（売上そのものは売上）との順位相関（200回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="center right", title="順位相関の相手", title_fontsize=9)
    ax.set_title("目標が力に合わせてあると、達成率は力ではなく運の順に並ぶ")
    save(fig, "a936_rank_corr.png", SRC)

    # 図2：1回分の散布図（4つの置き方）
    fig, axs = plt.subplots(2, 2, figsize=(7.6, 6.2), sharex=True, sharey=True)
    for ax, m in zip(axs.ravel(), METHODS):
        r = this / t[m] * 100
        ax.scatter(a, r, s=8, color=BLUE, alpha=.5, lw=0)
        ax.axhline(100, color=ORANGE, lw=1, ls="--")
        ax.set_xscale("log")
        ax.set_xticks([600, 800, 1000, 1500, 2000]); ax.set_xticklabels(["600", "800", "1000", "1500", "2000"])
        ax.minorticks_off()
        ax.set_title(f"{m}（順位相関 {one[m]['rho_rate_ability']:.2f}）", fontsize=11)
    for ax in axs[1]:
        ax.set_xlabel("本当の力（万円、対数の目盛り）")
    for ax in axs[:, 0]:
        ax.set_ylabel("目標達成率（%）")
    fig.suptitle("同じ200人・同じ今年の売上を、4つの目標で割った達成率（1回分）", fontsize=12)
    fig.tight_layout()
    save(fig, "a936_scatter.png", SRC)

    # 図3：目標が本当の力をどれだけ映すか（w）と年の振れ
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for s_y, c, ls in zip([0.08, 0.15, 0.25], [BLUE, ORANGE, GREEN], ["-", "--", "-."]):
        g = ww[ww.s_y == s_y]
        ax.plot(g.w, g.rho_rate_ability, marker="o", color=c, ls=ls, label=f"年ごとの振れ {s_y}")
    ax.axhline(0, color=GRAY, lw=.6)
    ax.set_xticks([0, .25, .5, .75, 1])
    ax.set_xticklabels(["0\n（一律）", "0.25", "0.5", "0.75", "1\n（上司の見立て）"])
    ax.set_xlabel("目標に本当の力をどれだけ映すか（w）")
    ax.set_ylabel("達成率と本当の力の順位相関")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("目標が力を映すほど、達成率から力の差は消える（各100回の平均）")
    save(fig, "a936_weight.png", SRC, y=-0.1)

    json.dump(out, open(RES / "a936_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
