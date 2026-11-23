"""1033 「定時」の決め方（1分・5分）で、定時率はどう変わるのか？（架空のデータ）

架空の路線バス3系統。1か月（30日×40便＝1,200便）の終点に着く時刻の遅れ（秒、早着は負）を作る。
遅れの形は系統ごとに作成者が置いた（A：小さな遅れが多い、B：ほぼ時刻どおりでときどき大きく遅れる、
C：早く着くことが多い）。同じ便の記録から、「定時」の決め方を変えて定時率を出し、系統の順位と、
改善の見え方がどう変わるかを数える。
"""
import json
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1033
SRC = "架空の路線バス3系統の到着の記録（作成者が乱数で作成、seed 1033）"
RUNS = 1200
# 系統ごとの遅れの形（秒）：ふだんの便は正規分布、混ざる便は「ずれ＋指数分布」
ROUTES = {
    "A": dict(name="系統A（小さな遅れが多い）", q=0.20, mu=75.0, sd=45.0, shift=120.0, m=150.0),
    "B": dict(name="系統B（ほぼ時刻どおり・ときどき大きく遅れる）", q=0.25, mu=0.0, sd=25.0, shift=60.0, m=360.0),
    "C": dict(name="系統C（早く着くことが多い）", q=0.45, mu=-70.0, sd=40.0, shift=0.0, m=150.0),
}
COLORS = {"A": ORANGE, "B": BLUE, "C": GREEN}


def draw(rng, P, n):
    mix = rng.random(n) < P["q"]
    normal = rng.normal(P["mu"], P["sd"], n)
    late = P["shift"] + rng.exponential(P["m"], n)
    return np.where(mix, late, normal)


def cdf(P, x):
    """遅れが x 秒未満になる確率（置いた分布からの式の値）"""
    pn = 0.5 * (1 + math.erf((x - P["mu"]) / (P["sd"] * math.sqrt(2))))
    pl = 0.0 if x <= P["shift"] else 1 - math.exp(-(x - P["shift"]) / P["m"])
    return (1 - P["q"]) * pn + P["q"] * pl


# 定時の決め方：(名前, 秒の記録 d に対する判定, 式の値の出し方)
DEFS = [
    ("①遅れ1分未満（秒で記録）", lambda d: d < 60, lambda P: cdf(P, 60)),
    ("②記録が1分以内（分で四捨五入）", lambda d: d < 90, lambda P: cdf(P, 90)),
    ("③記録が1分以内（分で切り捨て）", lambda d: d < 120, lambda P: cdf(P, 120)),
    ("④前後1分以内（1分以上の早着も外す）", lambda d: (d > -60) & (d < 60), lambda P: cdf(P, 60) - cdf(P, -60)),
    ("⑤遅れ3分未満", lambda d: d < 180, lambda P: cdf(P, 180)),
    ("⑥遅れ5分未満", lambda d: d < 300, lambda P: cdf(P, 300)),
]


def rates(rec):
    return {k: [float(f(d).mean()) for _, f, _ in DEFS] for k, d in rec.items()}


def main():
    rng = np.random.default_rng(SEED)
    out = {"routes": ROUTES, "runs_per_month": RUNS}

    # 1) 1か月の記録（data）と、2,000か月の平均・1か月ごとの1位
    one = {k: draw(rng, P, RUNS) for k, P in ROUTES.items()}
    rows = []
    for k, d in one.items():
        for i, x in enumerate(d):
            rows.append({"route": k, "day": i // 40 + 1, "run": i % 40 + 1, "delay_sec": round(float(x), 1)})
    pd.DataFrame(rows).to_csv(DATA / "one_month_runs.csv", index=False)
    out["one_month"] = {k: {"mean_delay_sec": round(float(d.mean()), 2),
                            "rates": [round(v * 100, 2) for v in r]} for (k, d), r in zip(one.items(), rates(one).values())}

    NM = 2000
    mon = {k: np.zeros((NM, len(DEFS))) for k in ROUTES}
    for t in range(NM):
        rec = {k: draw(rng, P, RUNS) for k, P in ROUTES.items()}
        r = rates(rec)
        for k in ROUTES:
            mon[k][t] = r[k]
    tab = []
    first = {}
    for j, (dn, _, fx) in enumerate(DEFS):
        M = np.stack([mon[k][:, j] for k in ROUTES], 1)
        # 同じ値は A→B→C の順にせず、乱数で順を決める
        jitter = rng.random(M.shape) * 1e-9
        top = np.argmax(M + jitter, 1)
        row = {"definition": dn}
        for i, k in enumerate(ROUTES):
            row[f"{k}_mean"] = round(float(M[:, i].mean()) * 100, 2)
            row[f"{k}_formula"] = round(fx(ROUTES[k]) * 100, 2)
            row[f"{k}_p10"] = round(float(np.quantile(M[:, i], .1)) * 100, 2)
            row[f"{k}_p90"] = round(float(np.quantile(M[:, i], .9)) * 100, 2)
            row[f"{k}_first"] = round(float((top == i).mean()) * 100, 2)
        first[dn] = top
        tab.append(row)
    tab = pd.DataFrame(tab)
    tab.to_csv(RES / "routes_by_definition.csv", index=False)
    out["by_definition"] = tab.to_dict("records")
    names = [d[0] for d in DEFS]
    out["first_differs_share"] = {
        "def1_vs_def6": round(float((first[names[0]] != first[names[5]]).mean()) * 100, 2),
        "def1_vs_def3": round(float((first[names[0]] != first[names[2]]).mean()) * 100, 2),
        "def1_vs_def4": round(float((first[names[0]] != first[names[3]]).mean()) * 100, 2),
    }
    out["max_formula_gap_points"] = round(float(max(
        abs(tab[f"{k}_mean"] - tab[f"{k}_formula"]).max() for k in ROUTES)), 3)
    out["def1_B_minus_A_points"] = round(float(tab.loc[0, "B_mean"] - tab.loc[0, "A_mean"]), 2)
    out["mean_delay_sec"] = {k: round(float((1 - P["q"]) * P["mu"] + P["q"] * (P["shift"] + P["m"])), 2)
                             for k, P in ROUTES.items()}

    # 2) 「定時」の幅を0〜10分で動かしたときの定時率（式の値）
    ths = np.arange(0, 601, 15)
    curve = pd.DataFrame({"threshold_sec": ths, **{k: [round(cdf(P, float(x)) * 100, 3) for x in ths]
                                                     for k, P in ROUTES.items()}})
    curve.to_csv(RES / "rate_by_threshold.csv", index=False)
    # 系統Aと系統Bの順が入れかわる幅
    fine = np.arange(0, 600.5, 0.5)
    diff = np.array([cdf(ROUTES["A"], x) - cdf(ROUTES["B"], x) for x in fine])
    cross = fine[np.where(np.diff(np.sign(diff)) != 0)[0] + 1]
    out["A_B_cross_sec"] = [float(c) for c in cross]

    # 3) 改善の見え方：系統Aで、平均の遅れが同じくらい縮む2つの改善
    PA = ROUTES["A"]
    imp = []
    rB = np.random.default_rng(SEED + 2)
    mixA = rB.random(200000) < PA["q"]
    nrm = rB.normal(PA["mu"], PA["sd"], 200000)
    lat = PA["shift"] + rB.exponential(PA["m"], 200000)
    cases = {
        "改善前": np.where(mixA, lat, nrm),
        "改善ア：ふだんの便の遅れを30秒縮める": np.where(mixA, lat, nrm - 30),
        "改善イ：大きく遅れる便の遅れを半分に": np.where(mixA, lat / 2, nrm),
    }
    for nm, d in cases.items():
        r = {"case": nm, "mean_delay_sec": round(float(d.mean()), 2)}
        for dn, f, _ in DEFS:
            r[dn] = round(float(f(d).mean()) * 100, 2)
        imp.append(r)
    imp = pd.DataFrame(imp)
    for dn, _, _ in DEFS:
        imp[dn + "_change"] = (imp[dn] - imp.loc[0, dn]).round(2)
    imp["mean_change_sec"] = (imp.mean_delay_sec - imp.loc[0, "mean_delay_sec"]).round(2)
    imp.to_csv(RES / "improvement_routeA.csv", index=False)
    out["improvementA_formula_mean_change_sec"] = round(-(1 - PA["q"]) * 30, 2)
    out["improvement_routeA"] = imp.to_dict("records")

    # 4) 確かめ：系統Aのふだんの遅れ × 系統Bの大きく遅れる便の割合 × その遅れの平均（27通り）
    grid = []
    gi = 0
    for muA in [45.0, 75.0, 105.0]:
        for qB in [0.15, 0.25, 0.35]:
            for mB in [240.0, 360.0, 480.0]:
                A = dict(ROUTES["A"], mu=muA)
                B = dict(ROUTES["B"], q=qB, m=mB)
                a1, b1 = cdf(A, 60) * 100, cdf(B, 60) * 100
                a5, b5 = cdf(A, 300) * 100, cdf(B, 300) * 100
                # 1か月1,200便での振れ：Aが上と出た月の割合（各300か月）
                g = np.random.default_rng(SEED * 100 + gi)
                gi += 1
                up1 = up5 = 0
                for _ in range(300):
                    da, db = draw(g, A, RUNS), draw(g, B, RUNS)
                    up1 += (da < 60).mean() > (db < 60).mean()
                    up5 += (da < 300).mean() > (db < 300).mean()
                grid.append({"A_mu_sec": muA, "B_q": qB, "B_m_sec": mB,
                             "A_1min": round(a1, 2), "B_1min": round(b1, 2), "A_5min": round(a5, 2), "B_5min": round(b5, 2),
                             "diff_1min": round(a1 - b1, 2), "diff_5min": round(a5 - b5, 2),
                             "order_flips": bool((a1 - b1) * (a5 - b5) < 0),
                             "months_A_higher_1min": round(up1 / 3, 2), "months_A_higher_5min": round(up5 / 3, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_shapes.csv", index=False)
    out["grid_summary"] = {
        "n": int(len(grid)), "n_flips": int(grid.order_flips.sum()),
        "diff_1min_min": float(grid.diff_1min.min()), "diff_1min_max": float(grid.diff_1min.max()),
        "diff_5min_min": float(grid.diff_5min.min()), "diff_5min_max": float(grid.diff_5min.max()),
        "n_A_lower_1min": int((grid.diff_1min < 0).sum()), "n_A_higher_5min": int((grid.diff_5min > 0).sum()),
        "nonflip_cases": grid[~grid.order_flips][["A_mu_sec", "B_q", "B_m_sec", "diff_1min", "diff_5min"]].to_dict("records"),
    }

    # 5) 確かめ：1か月の便の数と、①の1か月ごとの振れ（系統B、各2,000か月）
    sp = []
    for n in [120, 300, 1200, 4800]:
        g = np.random.default_rng(SEED * 7 + n)
        v = np.array([(draw(g, ROUTES["B"], n) < 60).mean() for _ in range(2000)]) * 100
        sp.append({"runs": n, "mean": round(float(v.mean()), 2), "p10": round(float(np.quantile(v, .1)), 2),
                   "p90": round(float(np.quantile(v, .9)), 2)})
    sp = pd.DataFrame(sp)
    sp.to_csv(RES / "monthly_spread_by_runs.csv", index=False)
    out["monthly_spread_routeB_def1"] = sp.to_dict("records")

    json.dump(out, open(RES / "a1033_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：定時の幅と定時率（式の値）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for k, P in ROUTES.items():
        ax.plot(curve.threshold_sec / 60, curve[k], color=COLORS[k], lw=2, label=P["name"])
    for x, lab, yy in [(1, "1分", 8), (5, "5分", 50)]:
        ax.axvline(x, color=GRAY, lw=1, ls="--")
        ax.text(x + 0.08, yy, lab, color=GRAY, fontsize=9)
    ax.set_xlim(0, 10); ax.set_ylim(0, 100)
    ax.set_xlabel("「定時」とみなす遅れの幅（分。この幅未満の遅れを定時とする）"); ax.set_ylabel("定時率（%）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("1分で区切ると系統Bが上、5分で区切ると系統Aが上")
    save(fig, "a1033_threshold.png", SRC)

    # 図2：6つの決め方ごとの定時率（2,000か月の平均）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    y = np.arange(len(DEFS))
    h = 0.26
    for i, k in enumerate(ROUTES):
        vals = tab[f"{k}_mean"].values
        ax.barh(y + (i - 1) * h, vals, height=h, color=COLORS[k], label=ROUTES[k]["name"])
        for yy, v in zip(y + (i - 1) * h, vals):
            ax.text(v + 0.8, yy, f"{v:.1f}%", va="center", fontsize=7.5)
    ax.set_yticks(y); ax.set_yticklabels(tab.definition, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, 112); ax.set_xlabel("定時率（%、2,000か月の平均）")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    ax.set_title("同じ便の記録でも、決め方で定時率と順位が変わる")
    save(fig, "a1033_definitions.png", SRC, y=-0.08)

    # 図3：改善の見え方
    sel = [names[0], names[4], names[5]]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    x = np.arange(len(sel))
    for i, (c, col) in enumerate(zip([1, 2], [LIGHT, BLUE])):
        vals = [imp.loc[c, s + "_change"] for s in sel]
        ax.bar(x + (i - 0.5) * 0.36, vals, width=0.36, color=col,
               label=f"{imp.loc[c, 'case']}（平均の遅れ {imp.loc[c, 'mean_change_sec']:+.1f}秒）")
        for xx, v in zip(x + (i - 0.5) * 0.36, vals):
            ax.text(xx, v + 0.4, f"+{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(["①遅れ1分未満", "⑤遅れ3分未満", "⑥遅れ5分未満"])
    ax.set_ylabel("定時率の上がり（ポイント）")
    ax.set_ylim(0, max(imp[[s + "_change" for s in sel]].max()) * 1.25)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("系統Aの2つの改善：どちらが効いて見えるかは、決め方で入れかわる")
    save(fig, "a1033_improvement.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])


if __name__ == "__main__":
    main()
