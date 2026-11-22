"""956 2つの拠点の中間に置くと、全体の距離は本当に短くなるのか？（架空のデータ）

架空の町に、2つの住宅地（A地区・B地区）がある。両方の世帯に届ける配送の拠点を1つだけ置く。
「2つの地区の真ん中」に置くと、全世帯までの距離の合計は本当に短くなるかを数える。
世帯の数と場所は作成者が置く。世帯ごとに1か月1回ずつ届けると置き、距離は拠点から世帯までの片道。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 956
SRC = "架空の町の2つの住宅地の世帯（作成者が乱数で作成、seed 956）"
BASE = dict(nA=2000, ratio=2.0, sd=0.8, gap=5.0)
REPS = 200
CA = np.array([2.5, 5.0])   # A地区の中心（km）


def make_town(rng, nA, ratio, sd, gap):
    nB = int(round(nA / ratio))
    cb = CA + np.array([gap, 0.0])
    a = CA + rng.normal(0, sd, (nA, 2))
    b = cb + rng.normal(0, sd, (nB, 2))
    pts = np.vstack([a, b])
    area = np.array(["A"] * nA + ["B"] * nB)
    return pts, area, cb


def dist(pts, p, kind):
    d = pts - p
    return np.hypot(d[:, 0], d[:, 1]) if kind == "straight" else np.abs(d).sum(1)


def best_total(pts, kind):
    """合計の距離がいちばん短い点。まっすぐの距離はワイスフェルトの方法、道のり（碁盤の目）は縦横それぞれの中央値"""
    if kind == "road":
        return np.median(pts, axis=0)
    p = pts.mean(0)
    for _ in range(500):
        d = np.maximum(np.hypot(*(pts - p).T), 1e-9)
        q = (pts / d[:, None]).sum(0) / (1 / d).sum()
        if np.hypot(*(q - p)) < 1e-7:
            p = q
            break
        p = q
    return p


def candidates(pts, cb, kind):
    return {"A地区の中心": CA.copy(), "2つの地区の真ん中": (CA + cb) / 2, "世帯の平均の場所（重心）": pts.mean(0),
            "合計の距離がいちばん短い点": best_total(pts, kind)}


def evaluate(pts, area, cb, kind):
    out = {}
    for name, p in candidates(pts, cb, kind).items():
        d = dist(pts, p, kind)
        out[name] = {"x": float(p[0]), "y": float(p[1]), "mean_km": float(d.mean()), "p95_km": float(np.quantile(d, .95)),
                     "max_km": float(d.max()), "mean_A_km": float(d[area == "A"].mean()),
                     "mean_B_km": float(d[area == "B"].mean()), "over3km": float((d > 3).mean())}
    return out


def p95_grid(pts, cb, kind, step=0.05):
    """95%の世帯が入る距離がいちばん短い点（格子で探す）"""
    xs = np.arange(CA[0] - 0.5, cb[0] + 0.5 + 1e-9, step)
    ys = np.arange(CA[1] - 1.0, CA[1] + 1.0 + 1e-9, step)
    best = (np.inf, None)
    for x in xs:
        P = np.stack([np.full_like(ys, x), ys], 1)
        if kind == "straight":
            D = np.hypot(pts[None, :, 0] - P[:, None, 0], pts[None, :, 1] - P[:, None, 1])
        else:
            D = np.abs(pts[None, :, 0] - P[:, None, 0]) + np.abs(pts[None, :, 1] - P[:, None, 1])
        q = np.quantile(D, .95, axis=1)
        i = int(np.argmin(q))
        if q[i] < best[0]:
            best = (float(q[i]), P[i])
    p = best[1]
    d = dist(pts, p, kind)
    return {"x": float(p[0]), "y": float(p[1]), "mean_km": float(d.mean()), "p95_km": float(np.quantile(d, .95)),
            "max_km": float(d.max()), "over3km": float((d > 3).mean())}


def summarize(rows):
    df = pd.DataFrame(rows)
    return df


def main():
    t0 = time.time()
    res = {"base": BASE, "reps": REPS}

    # 1) 例の町1つ
    rng = np.random.default_rng(SEED)
    pts, area, cb = make_town(rng, **BASE)
    pd.DataFrame({"household_id": np.arange(1, len(pts) + 1), "area": area, "x_km": pts[:, 0], "y_km": pts[:, 1]}) \
        .to_csv(DATA / "households_example_town.csv", index=False, float_format="%.4f")
    ex = {}
    for kind in ["straight", "road"]:
        e = evaluate(pts, area, cb, kind)
        e["95%の世帯が入る距離がいちばん短い点"] = p95_grid(pts, cb, kind)
        ex[kind] = {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in e.items()}
    res["example_town"] = {"households": int(len(pts)), "nA": int((area == "A").sum()), "nB": int((area == "B").sum()),
                           "B_center": cb.tolist(), "placements": ex}
    rows_ex = []
    for kind, e in ex.items():
        for name, v in e.items():
            rows_ex.append({"distance": kind, "placement": name, **v})
    pd.DataFrame(rows_ex).to_csv(RES / "example_town_placements.csv", index=False)

    # 2) 200の町（基本）
    rows = []
    for r in range(REPS):
        p_, a_, c_ = make_town(np.random.default_rng(SEED * 1000 + r), **BASE)
        for kind in ["straight", "road"]:
            e = evaluate(p_, a_, c_, kind)
            best = e["合計の距離がいちばん短い点"]["mean_km"]
            for name, v in e.items():
                rows.append({"rep": r, "distance": kind, "placement": name, **v, "excess_pct": (v["mean_km"] / best - 1) * 100})
    sim = pd.DataFrame(rows)
    tab = sim.groupby(["distance", "placement"], sort=False).agg(
        mean_km=("mean_km", "mean"), p95_km=("p95_km", "mean"), max_km=("max_km", "mean"),
        mean_A_km=("mean_A_km", "mean"), mean_B_km=("mean_B_km", "mean"), over3km=("over3km", "mean"),
        excess_pct=("excess_pct", "mean"), x=("x", "mean")).round(4).reset_index()
    tab.to_csv(RES / "placements_200_towns.csv", index=False)
    res["placements_200_towns"] = tab.to_dict(orient="records")
    st = sim[(sim.distance == "straight")]
    mid = st[st.placement == "2つの地区の真ん中"].set_index("rep")
    aa = st[st.placement == "A地区の中心"].set_index("rep")
    res["straight_mid_vs_A_mean_km_diff"] = round(float((mid.mean_km - aa.mean_km).mean()), 4)
    res["straight_mid_longer_than_A_share"] = round(float((mid.mean_km > aa.mean_km).mean()), 4)
    res["straight_mid_excess_pct_p10_p90"] = [round(float(mid.excess_pct.quantile(.1)), 2), round(float(mid.excess_pct.quantile(.9)), 2)]

    # 3) A→B の線の上で、拠点の場所と平均距離（世帯の数の比ごと）
    prof = []
    for ratio in [1.0, 2.0, 4.0]:
        p_, a_, c_ = make_town(np.random.default_rng(SEED * 3000 + int(ratio * 10)), BASE["nA"], ratio, BASE["sd"], BASE["gap"])
        for t in np.linspace(-0.1, 1.1, 49):
            p = CA + t * (c_ - CA)
            prof.append({"ratio": ratio, "t": round(float(t), 4), "x_km": round(float(p[0]), 4),
                         "mean_km_straight": float(dist(p_, p, "straight").mean()),
                         "mean_km_road": float(dist(p_, p, "road").mean())})
    prof = pd.DataFrame(prof)
    prof.to_csv(RES / "line_profile.csv", index=False, float_format="%.4f")
    pv = {}
    for ratio, d in prof.groupby("ratio"):
        i = d.mean_km_straight.idxmin()
        mid_row = d.iloc[(d.t - 0.5).abs().argmin()]
        a_row = d.iloc[(d.t - 0.0).abs().argmin()]
        pv[str(ratio)] = {"best_t": float(d.loc[i, "t"]), "best_mean_km": round(float(d.loc[i, "mean_km_straight"]), 4),
                          "mid_mean_km": round(float(mid_row.mean_km_straight), 4),
                          "A_mean_km": round(float(a_row.mean_km_straight), 4)}
    res["line_profile_straight"] = pv

    # 4) 確かめ：世帯の数の比 × 散らばり × 地区の間の距離 × 距離の測り方（各30の町）
    grid = []
    k = 0
    for ratio in [1.0, 1.5, 2.0, 4.0]:
        for sd in [0.5, 0.8, 1.5]:
            for gap in [2.0, 5.0, 8.0]:
                rr = [make_town(np.random.default_rng(SEED * 5000 + k * 100 + r), BASE["nA"], ratio, sd, gap) for r in range(30)]
                k += 1
                for kind in ["straight", "road"]:
                    ev = [evaluate(p_, a_, c_, kind) for p_, a_, c_ in rr]
                    best = np.array([e["合計の距離がいちばん短い点"]["mean_km"] for e in ev])
                    m_ = np.array([e["2つの地区の真ん中"]["mean_km"] for e in ev])
                    c_ = np.array([e["世帯の平均の場所（重心）"]["mean_km"] for e in ev])
                    a_ = np.array([e["A地区の中心"]["mean_km"] for e in ev])
                    mp = np.array([e["2つの地区の真ん中"]["p95_km"] for e in ev])
                    bp = np.array([e["合計の距離がいちばん短い点"]["p95_km"] for e in ev])
                    grid.append({"ratio": ratio, "sd": sd, "gap": gap, "distance": kind,
                                 "best_mean_km": round(best.mean(), 4), "mid_mean_km": round(m_.mean(), 4),
                                 "mid_excess_pct": round(float(((m_ / best - 1) * 100).mean()), 2),
                                 "centroid_excess_pct": round(float(((c_ / best - 1) * 100).mean()), 2),
                                 "A_excess_pct": round(float(((a_ / best - 1) * 100).mean()), 2),
                                 "mid_shorter_than_A": round(float((m_ < a_).mean()), 3),
                                 "mid_p95_km": round(mp.mean(), 3), "best_p95_km": round(bp.mean(), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    g1 = grid[grid.ratio > 1]
    res["robustness"] = {
        "combos": int(len(grid)),
        "mid_excess_pct_range_ratio_gt1": [float(g1.mid_excess_pct.min()), float(g1.mid_excess_pct.max())],
        "mid_excess_pct_range_ratio_eq1": [float(grid[grid.ratio == 1].mid_excess_pct.min()), float(grid[grid.ratio == 1].mid_excess_pct.max())],
        "centroid_excess_pct_range_all": [float(grid.centroid_excess_pct.min()), float(grid.centroid_excess_pct.max())],
        "mid_shorter_than_A_combos_ratio_ge2": int((grid[grid.ratio >= 2].mid_shorter_than_A > 0.5).sum()),
        "combos_ratio_ge2": int((grid.ratio >= 2).sum()),
        "mid_p95_minus_best_p95_range": [float((grid.mid_p95_km - grid.best_p95_km).min()), float((grid.mid_p95_km - grid.best_p95_km).max())],
    }

    # 図1：例の町の地図
    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    ax.scatter(pts[area == "A", 0], pts[area == "A", 1], s=4, color=LIGHT, alpha=0.8, lw=0, label=f"A地区の世帯（{(area == 'A').sum():,}）")
    ax.scatter(pts[area == "B", 0], pts[area == "B", 1], s=4, color="#f4b79c", alpha=0.9, lw=0, label=f"B地区の世帯（{(area == 'B').sum():,}）")
    e = ex["straight"]
    marks = [("A地区の中心", "D", INK), ("2つの地区の真ん中", "s", ORANGE), ("世帯の平均の場所（重心）", "^", GREEN),
             ("合計の距離がいちばん短い点", "*", BLUE), ("95%の世帯が入る距離がいちばん短い点", "P", GRAY)]
    for name, mk, c in marks:
        v = e[name]
        ax.scatter(v["x"], v["y"], marker=mk, s=160 if mk == "*" else 80, color=c, edgecolor="white", zorder=5,
                   label=f"{name}：平均{v['mean_km']:.2f}km・95%点{v['p95_km']:.2f}km")
    ax.set_xlim(-0.5, 11); ax.set_ylim(1.5, 8.5)
    ax.set_aspect("equal")
    ax.set_xlabel("東西（km）"); ax.set_ylabel("南北（km）")
    ax.legend(fontsize=8.5, loc="upper left", ncol=1, frameon=False, bbox_to_anchor=(1.01, 1.0), markerscale=1.5)
    ax.set_title("拠点を置く場所の候補と、世帯までのまっすぐの距離（例の町1つ）", fontsize=12, pad=8)
    save(fig, "a956_town_map.png", SRC + "。A地区2,000世帯・B地区1,000世帯、中心の間5km。95%点＝95%の世帯が入る距離")

    # 図2：A→B の線の上
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    for (ratio, d), c in zip(prof.groupby("ratio"), [GRAY, BLUE, ORANGE]):
        lab = {1.0: "1:1", 2.0: "2:1（基本）", 4.0: "4:1"}[ratio]
        ax.plot(d.t, d.mean_km_straight, color=c, lw=2, label=f"A地区:B地区の世帯＝{lab}")
        i = d.mean_km_straight.idxmin()
        ax.scatter(d.loc[i, "t"], d.loc[i, "mean_km_straight"], color=c, s=40, zorder=5)
    ax.axvline(0.5, color=INK, ls=":", lw=1)
    ax.text(0.51, ax.get_ylim()[1] * 0.98, "真ん中", va="top", fontsize=9)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["A地区の中心", "", "真ん中", "", "B地区の中心"])
    ax.set_ylabel("世帯までの平均の距離（km、まっすぐ）")
    ax.set_title("A地区とB地区を結ぶ線の上で、拠点を動かすと（点＝いちばん短い場所）", fontsize=12)
    ax.legend(fontsize=9, frameon=False)
    save(fig, "a956_line_profile.png", SRC + "。散らばり0.8km・中心の間5km。比ごとに町を1つ作った")

    # 図3：確かめ（真ん中に置いたときの余分）
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), sharey=True)
    for ax, kind, ttl in [(axes[0], "straight", "まっすぐの距離"), (axes[1], "road", "道のり（碁盤の目）")]:
        for sd, c, mk in [(0.5, GRAY, "o"), (0.8, BLUE, "s"), (1.5, ORANGE, "^")]:
            d = grid[(grid.distance == kind) & (grid.sd == sd) & (grid.gap == 5.0)].sort_values("ratio")
            ax.plot(d.ratio, d.mid_excess_pct, marker=mk, color=c, label=f"地区の散らばり{sd}km")
        ax.set_xticks([1, 1.5, 2, 4]); ax.set_xticklabels(["1:1", "1.5:1", "2:1", "4:1"])
        ax.set_xlabel("A地区:B地区の世帯の数")
        ax.set_title(ttl, fontsize=11)
        ax.axhline(0, color=GRAY, lw=0.6)
    axes[0].set_ylabel("真ん中に置いたときの平均の距離の余分（%）")
    axes[0].legend(fontsize=9, frameon=False)
    fig.suptitle("世帯の数が偏るほど、真ん中は合計の距離で長くなる\n（合計がいちばん短い点との比べ、中心の間5km、各30の町）", fontsize=12)
    fig.tight_layout()
    save(fig, "a956_excess_robustness.png", SRC + "。各30の町の平均")

    run_sec = round(time.time() - t0, 1)
    with open(RES / "a956_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", run_sec)


if __name__ == "__main__":
    main()
