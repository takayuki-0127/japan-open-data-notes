"""1102 試す順番を決めて並べると、時間とともに変わる分はどうまざるのか？（架空のデータ）

架空の焼き付けの工房で、小さな板に色を焼き付ける時間（4・5・6・7分）を変えて、1日に24枚（各6枚）を1枚ずつ焼く。
焼き色の濃さ（色を測る機械の値）は、焼く時間1分ごとに1.0濃くなると作成者が置く（7分と4分の本当の差は3.0）。
窯が1日のうちにだんだん温まり、同じ時間でも焼き色が濃くなっていく分（時間とともに変わる分）を置き、
5つの並べ方で24枚を焼いたとき、7分と4分の差の見積もりにどれだけまざるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1102
SRC = "架空の焼き付けの工房の焼き色（作成者が置いた効き目と窯の温まり方からの乱数、seed 1102）"
LEVELS = np.array([4, 5, 6, 7])
N = 24
EFFECT = 1.0            # 1分あたり
TRUE_DIFF = 3.0 * EFFECT
BASE = {"drift_total": 3.0, "shape": "linear", "wiggle_sd": 0.5, "wiggle_phi": 0.8, "noise_sd": 0.5, "tau": 5.0, "level": 50.0}
REPS = 10000
GRID_REPS = 4000
ORDERS = {"sorted": "①順に（4分を6枚→5分→6分→7分）", "cycle": "②1周ずつくり返す（4567 4567…）",
          "zigzag": "③往復（4567 7654…）", "random": "④全体をでたらめに", "block": "⑤4枚ごとの組の中ででたらめに"}
SHAPES = {"linear": "まっすぐ", "early": "はじめに急"}


def r(x, d=4):
    return round(float(x), d)


def drift_curve(total, shape, tau):
    t = np.arange(N)
    if shape == "linear":
        return total * t / (N - 1)
    return total * (1 - np.exp(-t / tau)) / (1 - np.exp(-(N - 1) / tau))


def orders(rng, reps):
    """各回の24枚の焼く時間（reps×24、段階の番号0〜3）"""
    o = {}
    o["sorted"] = np.tile(np.repeat(np.arange(4), 6), (reps, 1))
    o["cycle"] = np.tile(np.tile(np.arange(4), 6), (reps, 1))
    o["zigzag"] = np.tile(np.tile(np.r_[np.arange(4), np.arange(4)[::-1]], 3), (reps, 1))
    base = np.repeat(np.arange(4), 6)
    o["random"] = np.array([rng.permutation(base) for _ in range(reps)])
    o["block"] = np.concatenate([np.array([rng.permutation(4) for _ in range(reps * 6)]).reshape(reps, 6, 4)], axis=1).reshape(reps, 24)
    return o


def wiggle(rng, reps, sd, phi):
    w = np.zeros((reps, N))
    if sd == 0:
        return w
    w[:, 0] = sd * rng.standard_normal(reps)
    e = sd * np.sqrt(1 - phi ** 2)
    for t in range(1, N):
        w[:, t] = phi * w[:, t - 1] + e * rng.standard_normal(reps)
    return w


def estimate(lv, y, detrend):
    """7分−4分の差。detrend=True なら、焼いた順番（何枚目か）の直線も一緒に当てはめて引く"""
    reps = y.shape[0]
    t = np.arange(N) - (N - 1) / 2
    if not detrend:
        m3 = (y * (lv == 3)).sum(1) / 6
        m0 = (y * (lv == 0)).sum(1) / 6
        return m3 - m0
    Xd = np.stack([np.ones_like(y), lv == 1, lv == 2, lv == 3, np.broadcast_to(t, y.shape)], axis=2).astype(float)
    XtX = np.einsum("rni,rnj->rij", Xd, Xd)
    Xty = np.einsum("rni,rn->ri", Xd, y)
    out = np.linalg.solve(XtX, Xty[..., None])[:, 3, 0]
    return out


def simulate(rng, reps, drift_total, shape, wiggle_sd, noise_sd, detrend=True):
    od = orders(rng, reps)
    dc = drift_curve(drift_total, shape, BASE["tau"])
    res = {}
    for k, lv in od.items():
        y = BASE["level"] + EFFECT * LEVELS[lv] + dc[None, :] + wiggle(rng, reps, wiggle_sd, BASE["wiggle_phi"]) + noise_sd * rng.standard_normal((reps, N))
        est = {"raw": estimate(lv, y, False)}
        if detrend:
            est["detrend"] = estimate(lv, y, True)
        res[k] = {a: {"mean": r(e.mean(), 3), "bias": r(e.mean() - TRUE_DIFF, 3), "sd": r(e.std(), 3),
                      "p_within05": r(100 * np.mean(np.abs(e - TRUE_DIFF) <= 0.5), 2),
                      "p10": r(np.quantile(e, 0.1), 3), "p90": r(np.quantile(e, 0.9), 3)} for a, e in est.items()}
        res[k]["_y0"] = y[0]; res[k]["_lv0"] = lv[0]
    return res


def formula_bias(drift_total, shape):
    """時間とともに変わる分だけからの、並べ方ごとの差のずれ（式：7分の枚の平均の温まり−4分の枚の平均の温まり）"""
    dc = drift_curve(drift_total, shape, BASE["tau"])
    rng = np.random.default_rng(0)
    od = orders(rng, 1)
    f = {}
    for k in ["sorted", "cycle", "zigzag"]:
        lv = od[k][0]
        f[k] = r(dc[lv == 3].mean() - dc[lv == 0].mean(), 3)
    f["random"] = 0.0; f["block"] = 0.0
    return f


def main():
    rng = np.random.default_rng(SEED)
    base = simulate(rng, REPS, BASE["drift_total"], "linear", BASE["wiggle_sd"], BASE["noise_sd"])
    rows = []
    for k in ORDERS:
        for a in ["raw", "detrend"]:
            rows.append({"order": ORDERS[k], "analysis": "そのまま" if a == "raw" else "焼いた順番の直線も当てはめて引く", **base[k][a]})
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "orders_base.csv", index=False)

    # 1日分の例
    ex = []
    for k in ORDERS:
        for t in range(N):
            ex.append({"order": k, "position": t + 1, "minutes": int(LEVELS[base[k]["_lv0"][t]]), "color": r(base[k]["_y0"][t], 3)})
    pd.DataFrame(ex).to_csv(DATA / "one_day_each_order.csv", index=False)

    # 温まり方の形を変える（基本の量3.0、はじめに急）
    early = simulate(rng, REPS, BASE["drift_total"], "early", BASE["wiggle_sd"], BASE["noise_sd"])
    # 時間とともに変わる分がないとき
    none = simulate(rng, REPS, 0.0, "linear", BASE["wiggle_sd"], BASE["noise_sd"], detrend=False)

    grid = []
    for dt in [-3.0, 0.0, 3.0, 6.0]:
        for shape in ["linear", "early"]:
            for ws in [0.0, 0.5, 1.0]:
                o = simulate(rng, GRID_REPS, dt, shape, ws, BASE["noise_sd"])
                fb = formula_bias(dt, shape)
                row = {"drift_total": dt, "shape": shape, "wiggle_sd": ws}
                for k in ORDERS:
                    row[f"{k}_bias"] = o[k]["raw"]["bias"]; row[f"{k}_sd"] = o[k]["raw"]["sd"]
                    row[f"{k}_p_within05"] = o[k]["raw"]["p_within05"]
                    row[f"{k}_detrend_bias"] = o[k]["detrend"]["bias"]; row[f"{k}_detrend_sd"] = o[k]["detrend"]["sd"]
                    row[f"{k}_formula_bias"] = fb[k]
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    clean = lambda d: {k: {a: v for a, v in d[k].items() if not a.startswith("_")} for k in ORDERS}
    gl = grid[grid["shape"] == "linear"]
    ge = grid[(grid["shape"] == "early") & (grid.drift_total != 0)]
    out = {"setting": BASE, "true_diff": TRUE_DIFF, "reps": REPS, "grid_reps": GRID_REPS,
           "base_linear": clean(base), "early_shape": clean(early), "no_drift": clean(none),
           "formula_bias_base": formula_bias(BASE["drift_total"], "linear"),
           "formula_bias_early": formula_bias(BASE["drift_total"], "early"),
           "grid_max_abs_sim_minus_formula": r(max((grid[f"{k}_bias"] - grid[f"{k}_formula_bias"]).abs().max() for k in ORDERS), 3),
           "grid_sorted_bias_range": [r(grid.sorted_bias.min(), 3), r(grid.sorted_bias.max(), 3)],
           "grid_cycle_bias_range": [r(grid.cycle_bias.min(), 3), r(grid.cycle_bias.max(), 3)],
           "grid_zigzag_bias_linear_range": [r(gl.zigzag_bias.min(), 3), r(gl.zigzag_bias.max(), 3)],
           "grid_zigzag_bias_early_range": [r(ge.zigzag_bias.min(), 3), r(ge.zigzag_bias.max(), 3)],
           "grid_random_bias_range": [r(grid.random_bias.min(), 3), r(grid.random_bias.max(), 3)],
           "grid_block_bias_range": [r(grid.block_bias.min(), 3), r(grid.block_bias.max(), 3)],
           "grid_random_sd_range": [r(grid.random_sd.min(), 3), r(grid.random_sd.max(), 3)],
           "grid_block_sd_range": [r(grid.block_sd.min(), 3), r(grid.block_sd.max(), 3)],
           "grid_sorted_p_within05_range": [r(grid.sorted_p_within05.min(), 2), r(grid.sorted_p_within05.max(), 2)],
           "grid_block_p_within05_range": [r(grid.block_p_within05.min(), 2), r(grid.block_p_within05.max(), 2)],
           "grid_random_p_within05_range": [r(grid.random_p_within05.min(), 2), r(grid.random_p_within05.max(), 2)],
           "grid_n_block_sd_le_random_sd": int((grid.block_sd <= grid.random_sd).sum()),
           "grid_sorted_detrend_sd_range": [r(grid.sorted_detrend_sd.min(), 3), r(grid.sorted_detrend_sd.max(), 3)],
           "grid_zigzag_detrend_bias_early_range": [r(ge.zigzag_detrend_bias.min(), 3), r(ge.zigzag_detrend_bias.max(), 3)],
           "grid_sorted_detrend_bias_early_range": [r(ge.sorted_detrend_bias.min(), 3), r(ge.sorted_detrend_bias.max(), 3)],
           "grid_n_cases": int(len(grid))}
    json.dump(out, open(RES / "a1102_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：並べ方ごとの差の見積もり（平均）と散らばり（基本）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.25, 1]})
    keys = list(ORDERS)
    yy = np.arange(5)[::-1]
    m = [base[k]["raw"]["mean"] for k in keys]
    ax = axes[0]
    ax.barh(yy, m, color=[ORANGE, ORANGE, BLUE, BLUE, BLUE])
    ax.axvline(TRUE_DIFF, color=INK, ls="--", lw=1)
    ax.text(TRUE_DIFF, 4.55, " 本当の差 3.0", fontsize=9, va="bottom")
    for y_, v in zip(yy, m):
        ax.text(v + 0.08, y_, f"{v}", va="center", fontsize=9.5)
    ax.set_yticks(yy); ax.set_yticklabels([ORDERS[k] for k in keys]); ax.set_xlim(0, 6.2)
    ax.set_xlabel("7分と4分の焼き色の差（10,000日の平均）"); ax.set_ylim(-0.6, 5.0)
    ax = axes[1]
    s = [base[k]["raw"]["sd"] for k in keys]
    ax.barh(yy, s, color=GRAY)
    for y_, v in zip(yy, s):
        ax.text(v + 0.01, y_, f"{v}", va="center", fontsize=9.5)
    ax.set_yticks(yy); ax.set_yticklabels([]); ax.set_xlim(0, max(s) * 1.25); ax.set_ylim(-0.6, 5.0)
    ax.set_xlabel("1日ごとの差の散らばり（標準偏差）")
    fig.suptitle(f"窯がまっすぐ温まると置いたとき（1日で+3.0）：順に並べると差に{base['sorted']['raw']['bias']:+}がまざった（式どおりなら{formula_bias(BASE['drift_total'], 'linear')['sorted']:+}）", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "a1102_orders.png", SRC, y=-0.03)

    # 図2：1日分の例（①と⑤）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    cols = [LIGHT, BLUE, "#f2b38f", ORANGE]
    dc = drift_curve(BASE["drift_total"], "linear", BASE["tau"])
    for ax, k in zip(axes, ["sorted", "block"]):
        lv = base[k]["_lv0"]; y = base[k]["_y0"]
        for j in range(4):
            sel = lv == j
            ax.scatter(np.arange(1, N + 1)[sel], y[sel], color=cols[j], s=36, label=f"{LEVELS[j]}分", zorder=3, edgecolor="white", linewidth=0.5)
        ax.set_title(ORDERS[k], fontsize=10.5, loc="left")
        ax.set_xlabel("焼いた順番（何枚目か）"); ax.grid(axis="y", color="#eeeeee")
    axes[0].set_ylabel("焼き色の濃さ（機械の値）")
    axes[0].legend(fontsize=8.5, ncol=4, loc="upper left")
    fig.suptitle("1日分の例：順に並べると、焼く時間の差と窯の温まりが重なる", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    save(fig, "a1102_one_day.png", SRC, y=-0.03)

    # 図3：温まり方の形で、往復の打ち消しがどう変わるか
    fig, ax = plt.subplots(figsize=(9, 4.3))
    w = 0.38
    bl = [base[k]["raw"]["bias"] for k in keys]
    be = [early[k]["raw"]["bias"] for k in keys]
    ax.barh(yy + w / 2, bl, height=w, color=BLUE, label="まっすぐ温まる（基本）")
    ax.barh(yy - w / 2, be, height=w, color=ORANGE, label="はじめに急に温まる")
    for y_, a, b in zip(yy, bl, be):
        ax.text(max(a, 0) + 0.05, y_ + w / 2, f"{a:+}", va="center", fontsize=9)
        ax.text(max(b, 0) + 0.05, y_ - w / 2, f"{b:+}", va="center", fontsize=9)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(yy); ax.set_yticklabels([ORDERS[k] for k in keys])
    ax.set_xlim(-0.5, 3.4); ax.set_xlabel("差のずれ（見積もりの平均−本当の差3.0）")
    ax.legend(fontsize=9, loc="lower right")
    ax.set_title("1日の温まりの合計は同じ+3.0：往復で消えるのは、まっすぐの分だけ", loc="left", fontsize=12)
    save(fig, "a1102_shape.png", SRC, y=-0.04)

    print(tab.to_string())
    print(json.dumps({k: v for k, v in out.items() if k not in ("base_linear",)}, ensure_ascii=False, indent=1))
    print(grid[[c for c in grid.columns if "bias" in c and "detrend" not in c or c in ("drift_total", "shape", "wiggle_sd")]].to_string())


if __name__ == "__main__":
    main()
