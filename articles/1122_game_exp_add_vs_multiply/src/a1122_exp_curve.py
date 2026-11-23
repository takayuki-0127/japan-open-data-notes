"""1122 レベルごとに要る経験値を足し算で増やすか掛け算で増やすかで、遊んだ時間あたりのレベルはどう変わるのか？（架空のデータ）

架空のゲームで、レベル L から L+1 に上がるのに要る経験値を
  足し算：a + b×(L−1)　　掛け算：a × r^(L−1)
の2つの決まりで置く。最初の1レベルに要る経験値 a と、ふつうの速さの人が Lv50 に着く時間（100時間）を2つの決まりでそろえ、
b と r を求める。1時間に得る経験値は 1000×（1＋レベルごとの増え×(L−1)）×その人の速さ×30分ごとのぶれ。
レベルの上限は置かず、200時間まで遊んだときのレベルを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1122
SRC = "架空のゲームのレベルと経験値（作成者が置いた決まりと乱数、seed 1122）"
E0 = 1000.0           # レベル1で1時間に得る経験値（ふつうの速さの人）
L_REF, H_REF = 50, 100.0   # ふつうの速さの人が Lv50 に着く時間を100時間にそろえる
LMAX = 3000            # 計算のための上限（届かない大きさ）
BASE = {"a": 200.0, "g": 0.0}
GRID_A = [100.0, 200.0, 400.0]
GRID_G = [0.0, 0.05, 0.1]
N_PLAYERS = 3000
SPEED_SD = 0.4        # その人の速さ（中央値1の対数正規、対数の標準偏差）
NOISE_SD = 0.3        # 30分ごとのぶれ（平均1の対数正規、対数の標準偏差）
DT = 0.5
H_END = 200.0
CHECK_H = [1, 2, 5, 10, 25, 50, 75, 100, 150, 200]
RULES = [("add", "足し算"), ("mul", "掛け算")]


def r(x, d=3):
    return round(float(x), d)


def income(L, g):
    return E0 * (1 + g * (L - 1))


def hours_to_ref(need, g):
    L = np.arange(1, L_REF)
    return float(np.sum(need[:L_REF - 1] / income(L, g)))


def needs(rule, a, g):
    """レベル1→2, 2→3, … に要る経験値（長さ LMAX）"""
    L = np.arange(1, LMAX + 1)
    if rule == "add":
        # 時間は b について一次：H(b) = Σ (a + b(L−1)) / income
        Lr = np.arange(1, L_REF)
        h_a = np.sum(a / income(Lr, g)); h_b = np.sum((Lr - 1) / income(Lr, g))
        b = (H_REF - h_a) / h_b
        return a + b * (L - 1), float(b)
    lo, hi = 1.0, 2.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if hours_to_ref(a * mid ** (L - 1), g) > H_REF:
            hi = mid
        else:
            lo = mid
    rr = (lo + hi) / 2
    with np.errstate(over="ignore"):
        need = a * rr ** (L - 1.0)
    need = np.minimum(need, 1e300)
    return need, float(rr)


def level_at(need, g, hours, speed=1.0):
    """ぶれのない人の、時間 hours でのレベル（整数のレベル＋次への進み具合）"""
    L = np.arange(1, LMAX + 1)
    step_h = need / (income(L, g) * speed)
    cum = np.concatenate([[0.0], np.cumsum(step_h)])
    out = []
    for h in np.atleast_1d(hours):
        k = int(np.searchsorted(cum, h, side="right")) - 1   # 終えたステップの数
        frac = (h - cum[k]) / step_h[k]
        out.append(1 + k + frac)
    return np.array(out)


def simulate(rng, need, g, speed):
    n = len(speed)
    L = np.ones(n, dtype=int); prog = np.zeros(n)
    steps = int(round(H_END / DT))
    rec = {}
    for s in range(1, steps + 1):
        noise = np.exp(rng.normal(-NOISE_SD ** 2 / 2, NOISE_SD, n))
        gain = speed * income(L, g) * noise * DT
        prog += gain
        while True:
            up = prog >= need[L - 1]
            if not up.any():
                break
            prog[up] -= need[L[up] - 1]
            L[up] += 1
        h = s * DT
        if h in (10.0, 20.0, 50.0, 100.0, 200.0):
            rec[h] = L.copy()
    return rec


def analyze_rule(rule, a, g, rng=None, speed=None):
    need, par = needs(rule, a, g)
    lv = level_at(need, g, CHECK_H)
    Ls = np.arange(1, LMAX + 1)
    step_h = need / income(Ls, g)
    out = {"param": par, "param_round": r(par, 1 if rule == "add" else 4), "level_at": {str(h): r(np.floor(v), 0) for h, v in zip(CHECK_H, lv)},
           "level_at_frac": {str(h): r(v) for h, v in zip(CHECK_H, lv)},
           "hours_step_1": r(step_h[0]), "hours_step_49": r(step_h[48]), "ratio_49_1": r(step_h[48] / step_h[0]),
           "hours_to_ref": r(np.sum(step_h[:L_REF - 1])),
           "levels_per_hour_0_10": r((lv[CHECK_H.index(10)] - 1) / 10), "levels_per_hour_90_100": r((level_at(need, g, [100])[0] - level_at(need, g, [90])[0]) / 10),
           "levels_per_hour_190_200": r((level_at(need, g, [200])[0] - level_at(need, g, [190])[0]) / 10)}
    if rule == "mul":
        out["gap_x2_formula_log2_logr"] = r(np.log(2) / np.log(par), 2)
    # 速さ2倍の人（ぶれなし）との差
    for h in (20, 50, 100):
        out[f"gap_x2_at_{h}"] = r(level_at(need, g, [h], 2.0)[0] - level_at(need, g, [h], 1.0)[0], 2)
    sim = None
    if rng is not None:
        sim = simulate(rng, need, g, speed)
        for h, Lh in sim.items():
            q = np.percentile(Lh, [10, 50, 90])
            out[f"players_{int(h)}h"] = {"p10": r(q[0], 1), "median": r(q[1], 1), "p90": r(q[2], 1), "spread_10_90": r(q[2] - q[0], 1)}
    return out, need, step_h, sim


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    speed = np.exp(rng.normal(0, SPEED_SD, N_PLAYERS))
    res = {"setup": {"E0": E0, "L_REF": L_REF, "H_REF": H_REF, "a": BASE["a"], "g": BASE["g"], "players": N_PLAYERS,
                     "speed_sd_log": SPEED_SD, "noise_sd_log": NOISE_SD, "dt_hours": DT, "h_end": H_END,
                     "speed_p10_p90": [r(np.percentile(speed, 10)), r(np.percentile(speed, 90))]}}
    base = {}; curves = {}; steps = {}; sims = {}
    for key, name in RULES:
        rng_k = np.random.default_rng(SEED + (0 if key == "add" else 1))
        o, need, sh, sim = analyze_rule(key, BASE["a"], BASE["g"], rng_k, speed)
        base[key] = o; steps[key] = sh; sims[key] = sim
        hh = np.arange(0, H_END + 0.001, 1.0)
        curves[key] = level_at(need, BASE["g"], hh)
    res["base"] = base
    # 足し算の人ごとの差と掛け算の人ごとの差の比
    res["base"]["spread_ratio_50h_add_over_mul"] = r(base["add"]["players_50h"]["spread_10_90"] / base["mul"]["players_50h"]["spread_10_90"], 2)

    # 曲線と1レベルの時間
    pd.DataFrame({"hours": np.arange(0, H_END + 0.001, 1.0), "level_add": np.round(curves["add"], 4),
                  "level_mul": np.round(curves["mul"], 4)}).to_csv(RES / "curve_base.csv", index=False)
    pd.DataFrame({"level_from": np.arange(1, 81), "hours_add": np.round(steps["add"][:80], 4),
                  "hours_mul": np.round(steps["mul"][:80], 4)}).to_csv(RES / "step_hours_base.csv", index=False)

    # 人ごとのデータ
    pd.DataFrame({"player_id": np.arange(1, N_PLAYERS + 1), "speed": np.round(speed, 4),
                  **{f"level_{k}_{int(h)}h": sims[k][h] for k, _ in RULES for h in (10.0, 20.0, 50.0, 100.0, 200.0)}}
                 ).to_csv(DATA / "players.csv", index=False)

    # 置き方を変えた9通り（ぶれなしの式の値と、人ごとの散らばり）
    rows = []
    for a in GRID_A:
        for g in GRID_G:
            row = {"a_first_need": a, "income_growth": g}
            for key, _ in RULES:
                rng_k = np.random.default_rng(SEED + int(a) + int(g * 1000) + (0 if key == "add" else 7))
                o, _, _, _ = analyze_rule(key, a, g, rng_k, speed[:1000])
                row[f"{key}_param"] = r(o["param"], 5)
                row[f"{key}_hours_to_lv50"] = o["hours_to_ref"]
                row[f"{key}_level_10h"] = o["level_at_frac"]["10"]
                row[f"{key}_level_50h"] = o["level_at_frac"]["50"]
                row[f"{key}_level_200h"] = o["level_at_frac"]["200"]
                row[f"{key}_ratio_49_1"] = o["ratio_49_1"]
                row[f"{key}_gap_x2_50h"] = o["gap_x2_at_50"]
                row[f"{key}_gap_x2_100h"] = o["gap_x2_at_100"]
                row[f"{key}_spread_50h"] = o["players_50h"]["spread_10_90"]
                row[f"{key}_spread_100h"] = o["players_100h"]["spread_10_90"]
            rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    rng_sum = {}
    for col in grid.columns[2:]:
        rng_sum[col] = [r(grid[col].min(), 3), r(grid[col].max(), 3)]
    res["grid_range"] = rng_sum
    res["grid_hours_to_lv50_all_100"] = bool(np.allclose(grid[["add_hours_to_lv50", "mul_hours_to_lv50"]].values, H_REF, atol=1e-3))
    res["grid_mul_ahead_50h_all"] = bool((grid["add_level_50h"] < grid["mul_level_50h"]).all())
    res["grid_gap_add_larger_100h_all"] = bool((grid["add_gap_x2_100h"] > grid["mul_gap_x2_100h"]).all())
    res["grid_spread_add_larger_100h_all"] = bool((grid["add_spread_100h"] > grid["mul_spread_100h"]).all())

    # 図1：時間とレベル
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    hh = np.arange(0, H_END + 0.001, 1.0)
    ax.plot(hh, curves["add"], color=BLUE, lw=2.2, label=f"足し算（1レベルごとに +{base['add']['param']:.1f}）")
    ax.plot(hh, curves["mul"], color=ORANGE, lw=2.2, label=f"掛け算（1レベルごとに ×{base['mul']['param']:.4f}）")
    ax.axvline(H_REF, color=GRAY, lw=0.8, ls="--"); ax.axhline(L_REF, color=GRAY, lw=0.8, ls="--")
    ax.text(H_REF + 2, 3, "100時間でLv50にそろえた", color=GRAY, fontsize=9)
    ax.set_xlim(0, H_END); ax.set_ylim(0, None)
    ax.set_xlabel("遊んだ時間（時間）"); ax.set_ylabel("レベル（ふつうの速さの人）")
    ax.set_title("同じ100時間でLv50にそろえても、途中と先のレベルが違う")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1122_curve.png", SRC)

    # 図2：1レベル上げるのに要る時間
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    lv = np.arange(1, 81)
    ax.plot(lv, steps["add"][:80], color=BLUE, lw=2.2, label="足し算")
    ax.plot(lv, steps["mul"][:80], color=ORANGE, lw=2.2, label="掛け算")
    ax.axvline(L_REF, color=GRAY, lw=0.8, ls="--")
    ax.set_ylim(0, None); ax.set_xlim(1, 80)
    ax.set_xlabel("今のレベル"); ax.set_ylabel("次のレベルまでの時間（時間）")
    ax.set_title("1レベル上げる時間：足し算はまっすぐ、掛け算は先で急に伸びる")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "a1122_step_hours.png", SRC)

    # 図3：50時間・100時間の人ごとのレベルの散らばり
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 4.2), sharey=True)
    for ax, h in zip(axes, (50.0, 100.0)):
        bins = np.arange(0, 122, 2)
        ax.hist(sims["add"][h], bins=bins, color=BLUE, alpha=0.6, label="足し算")
        ax.hist(sims["mul"][h], bins=bins, color=ORANGE, alpha=0.6, label="掛け算")
        ax.set_title(f"{int(h)}時間遊んだ{N_PLAYERS:,}人のレベル")
        ax.set_xlabel("レベル"); ax.set_xlim(0, 120)
    axes[0].set_ylabel("人数"); axes[0].legend(frameon=False)
    fig.suptitle("速さの違う人どうしのレベルの開きは、掛け算のほうが小さい", y=1.02)
    save(fig, "a1122_players.png", SRC)

    (RES / "a1122_main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1)[:6000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
