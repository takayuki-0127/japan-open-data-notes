"""952 配送の時間は、距離に比例するのか？（架空のデータ）

架空の町（6,000m×6,000m、碁盤の目の道）。拠点から届け先まで、縦横の道を通って運ぶ。
1件の時間＝走る時間（町の中ほどの混む区域は遅い）＋停めて渡す時間（距離によらない）。
作成者が置いたこの決まりで配送を作り、「時間は距離に比例する」と見て見積もると、
どの距離の配送がどれだけ外れるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 952
SRC = "架空の町の配送（作成者が乱数で作成、seed 952）"
L = 6000.0
CENTER, R_CENTER = (3500.0, 3500.0), 1200.0
DEPOTS = {"西南寄り": (1500.0, 1500.0), "真ん中": (3000.0, 3000.0)}
BASE = {"n": 1000, "fixed_median": 5.0, "fixed_sd": 0.5, "speed": 400.0, "center_speed": 200.0,
        "travel_sd": 0.15, "dest_center_share": 0.5, "depot": "西南寄り"}
BANDS = [(0, 500), (500, 1000), (1000, 2000), (2000, 3000), (3000, 4000), (4000, 9000)]


def leg_center_len(p0, p1, k=200):
    """p0→p1 のまっすぐな区間（縦か横）のうち、混む区域の中を通る長さ（m）"""
    t = (np.arange(k) + 0.5) / k
    xs = p0[0][:, None] + (p1[0] - p0[0])[:, None] * t
    ys = p0[1][:, None] + (p1[1] - p0[1])[:, None] * t
    inside = np.hypot(xs - CENTER[0], ys - CENTER[1]) <= R_CENTER
    return inside.mean(1) * np.hypot(p1[0] - p0[0], p1[1] - p0[1])


def make(rng, n=1000, fixed_median=5.0, fixed_sd=0.5, speed=400.0, center_speed=200.0, travel_sd=0.15,
         dest_center_share=0.5, depot="西南寄り"):
    dx, dy = DEPOTS[depot]
    nc = rng.binomial(n, dest_center_share)
    pts = np.vstack([np.array(CENTER) + rng.normal(0, 900, (nc, 2)), rng.uniform(0, L, (n - nc, 2))])
    pts = np.clip(pts, 0, L)
    pts = pts[rng.permutation(n)]
    x, y = pts[:, 0], pts[:, 1]
    X0, Y0 = np.full(n, dx), np.full(n, dy)
    road = np.abs(x - dx) + np.abs(y - dy)
    # 2通りのL字の道（先に東西／先に南北）のうち、速いほうを通る
    c1 = leg_center_len((X0, Y0), (x, Y0)) + leg_center_len((x, Y0), (x, y))
    c2 = leg_center_len((X0, Y0), (X0, y)) + leg_center_len((X0, y), (x, y))
    t1 = (road - c1) / speed + c1 / center_speed
    t2 = (road - c2) / speed + c2 / center_speed
    center_len = np.where(t1 <= t2, c1, c2)
    travel = np.minimum(t1, t2) * np.exp(rng.normal(0, travel_sd, n))
    fixed = fixed_median * np.exp(rng.normal(0, fixed_sd, n)) if fixed_median > 0 else np.zeros(n)
    return pd.DataFrame({"x": x, "y": y, "straight_m": np.hypot(x - dx, y - dy), "road_m": road,
                         "center_m": center_len, "travel_min": travel, "fixed_min": fixed,
                         "total_min": travel + fixed})


def fit(train):
    d, t = train.straight_m.values / 1000, train.total_min.values
    rate = t.sum() / d.sum()                       # 比例：1km あたり◯分（合計÷合計）
    b, a = np.polyfit(d, t, 1)                     # 切片のある直線
    A = np.c_[np.ones(len(d)), train.road_m.values / 1000, train.center_m.values / 1000]
    coef = np.linalg.lstsq(A, t, rcond=None)[0]    # 道のり＋混む区域を通る長さ
    return {"rate": rate, "a": a, "b": b, "coef": coef}


def predict(m, df):
    d = df.straight_m.values / 1000
    A = np.c_[np.ones(len(d)), df.road_m.values / 1000, df.center_m.values / 1000]
    return {"比例（1kmあたり◯分）": m["rate"] * d, "直線（決まった時間＋1kmあたり◯分）": m["a"] + m["b"] * d,
            "道のり＋混む区域": A @ m["coef"]}


METHODS = ["比例（1kmあたり◯分）", "直線（決まった時間＋1kmあたり◯分）", "道のり＋混む区域"]


def evaluate(m, test):
    pr = predict(m, test)
    t = test.total_min.values
    d = test.straight_m.values
    out = {}
    for k in METHODS:
        p = pr[k]
        row = {"mae_min": float(np.abs(p - t).mean())}
        for lo, hi in BANDS:
            s = (d >= lo) & (d < hi)
            row[f"bias_{lo}_{hi}"] = float(p[s].sum() / t[s].sum() - 1) if s.any() else np.nan
        out[k] = row
    return out


def ratio_2_1(df):
    d = df.straight_m.values
    a = df.total_min.values[(d >= 800) & (d < 1200)].mean()
    b = df.total_min.values[(d >= 1800) & (d < 2200)].mean()
    return float(b / a)


def run(seed, **p):
    rng = np.random.default_rng(seed)
    train, test = make(rng, **p), make(rng, **p)
    m = fit(train)
    ev = evaluate(m, test)
    both = pd.concat([train, test])
    return train, test, m, ev, ratio_2_1(both)


def main():
    train, test, m, ev, r21 = run(SEED, **BASE)
    data = train.assign(month="先月").pipe(lambda a: pd.concat([a, test.assign(month="今月")]))
    data.insert(0, "delivery_id", np.arange(1, len(data) + 1))
    data.round({"x": 1, "y": 1, "straight_m": 1, "road_m": 1, "center_m": 1, "travel_min": 2, "fixed_min": 2,
                "total_min": 2}).to_csv(DATA / "deliveries.csv", index=False)
    both = pd.concat([train, test])
    bands = []
    for lo, hi in BANDS:
        s = both[(both.straight_m >= lo) & (both.straight_m < hi)]
        bands.append({"band_m": f"{lo}〜{hi}", "n": int(len(s)), "mean_min": round(float(s.total_min.mean()), 2),
                      "fixed_share": round(float(s.fixed_min.sum() / s.total_min.sum()), 4),
                      "min_per_km": round(float(s.total_min.sum() / (s.straight_m.sum() / 1000)), 2)})
    bands = pd.DataFrame(bands)
    bands.to_csv(RES / "distance_bands.csv", index=False)
    ev_rows = []
    for k in METHODS:
        ev_rows.append({"method": k, **{kk: round(v, 4) for kk, v in ev[k].items()}})
    pd.DataFrame(ev_rows).to_csv(RES / "methods_test_month.csv", index=False)
    # 同じ距離（2.5〜3.5km）で、混む区域を通るかどうか
    mid = both[(both.straight_m >= 2500) & (both.straight_m < 3500)]
    thru = mid.center_m > 500
    same_dist = {"n_through": int(thru.sum()), "n_not": int((~thru).sum()),
                 "mean_through": round(float(mid.total_min[thru].mean()), 2),
                 "mean_not": round(float(mid.total_min[~thru].mean()), 2)}
    base = {"n_train": int(len(train)), "n_test": int(len(test)), "rate_min_per_km": round(float(m["rate"]), 3),
            "linear_intercept_min": round(float(m["a"]), 3), "linear_slope_min_per_km": round(float(m["b"]), 3),
            "fixed_mean_set": round(float(both.fixed_min.mean()), 3),
            "fixed_mean_formula": round(float(BASE["fixed_median"] * np.exp(BASE["fixed_sd"] ** 2 / 2)), 3),
            "ratio_2km_1km": round(r21, 4), "fixed_share_all": round(float(both.fixed_min.sum() / both.total_min.sum()), 4),
            "road_over_straight": round(float(both.road_m.sum() / both.straight_m.sum()), 4),
            "same_distance_2500_3500": same_dist,
            "test_eval": {k: {kk: round(v, 4) for kk, v in ev[k].items()} for k in METHODS}}

    # 確かめ：置き方を1つずつ変える（各10回、先月で当てはめ今月で数える）
    grid = ([("停めて渡す時間（中央値・分）", "fixed_median", v) for v in [0.0, 2.0, 5.0, 10.0]] +
            [("混む区域の速さ（m/分）", "center_speed", v) for v in [400.0, 200.0, 133.0]] +
            [("拠点の場所", "depot", v) for v in ["西南寄り", "真ん中"]] +
            [("中ほどに届ける割合", "dest_center_share", v) for v in [0.0, 0.5, 0.8]])
    rob = []
    for k, (lab, key, val) in enumerate(grid):
        p = dict(BASE); p[key] = val
        rs = []
        for i in range(10):
            _, _, mm, e, r = run(SEED * 1000 + k * 100 + i, **p)
            rs.append({"ratio_2km_1km": r, "intercept": mm["a"], "rate": mm["rate"],
                       "prop_bias_short": e[METHODS[0]]["bias_0_500"],
                       "prop_bias_0500_1000": e[METHODS[0]]["bias_500_1000"],
                       "prop_bias_long": e[METHODS[0]]["bias_4000_9000"],
                       "mae_prop": e[METHODS[0]]["mae_min"], "mae_lin": e[METHODS[1]]["mae_min"],
                       "mae_road": e[METHODS[2]]["mae_min"]})
        rs = pd.DataFrame(rs).mean()
        rob.append({"factor": lab, "key": key, "value": val, "is_base": val == BASE[key],
                    **{c: round(float(rs[c]), 4) for c in rs.index}})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    nz = rob[rob.key != "fixed_median"]
    out = {"settings_base": BASE, "center": CENTER, "center_radius_m": R_CENTER, "depots": DEPOTS,
           "base": base, "distance_bands": bands.to_dict("records"),
           "robustness_ratio_range": {"min": float(rob.ratio_2km_1km.min()), "max": float(rob.ratio_2km_1km.max())},
           "robustness_prop_bias_short_range": {"min": float(rob.prop_bias_short.min()), "max": float(rob.prop_bias_short.max())},
           "robustness_prop_bias_short_range_fixed_gt0": {
               "min": float(rob[rob.value.astype(str) != "0.0"].prop_bias_short.min()),
               "max": float(rob[rob.value.astype(str) != "0.0"].prop_bias_short.max())},
           "robustness_prop_bias_0500_1000_range_fixed_gt0": {
               "min": float(rob[rob.value.astype(str) != "0.0"].prop_bias_0500_1000.min()),
               "max": float(rob[rob.value.astype(str) != "0.0"].prop_bias_0500_1000.max())},
           "robustness_ratio_range_fixed_gt0": {
               "min": float(rob[rob.value.astype(str) != "0.0"].ratio_2km_1km.min()),
               "max": float(rob[rob.value.astype(str) != "0.0"].ratio_2km_1km.max())}}
    json.dump(out, open(RES / "a952_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：架空の町と届け先
    fig, ax = plt.subplots(figsize=(6.8, 5.9))
    for v in np.arange(0, L + 1, 500):
        ax.axvline(v, color=LIGHT, lw=.4, zorder=0); ax.axhline(v, color=LIGHT, lw=.4, zorder=0)
    ax.add_patch(Circle(CENTER, R_CENTER, color=ORANGE, alpha=.12, lw=0))
    ax.add_patch(Circle(CENTER, R_CENTER, fill=False, ec=ORANGE, lw=1.2, ls="--"))
    sc = ax.scatter(test.x, test.y, c=test.total_min, cmap="Blues", s=9, vmin=0, vmax=np.quantile(test.total_min, .98),
                    ec=GRAY, lw=.2)
    cb = fig.colorbar(sc, ax=ax, shrink=.8, pad=.03); cb.set_label("1件の時間（分）")
    dx, dy = DEPOTS[BASE["depot"]]
    ax.scatter([dx], [dy], marker="s", s=90, color=INK, zorder=5)
    ax.text(dx + 120, dy - 260, "拠点", fontsize=10, color=INK)
    ax.text(CENTER[0], CENTER[1] + R_CENTER + 120, "混む区域（速さ半分）", ha="center", va="bottom", fontsize=9, color=ORANGE,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=.9), zorder=6)
    ax.set_xlim(0, L); ax.set_ylim(0, L); ax.set_aspect("equal")
    ax.set_xlabel("東西（m）。細い線は道（500mごと）"); ax.set_ylabel("南北（m）")
    ax.set_title(f"架空の町の配送（今月の{len(test):,}件）", fontsize=12)
    save(fig, "a952_town_map.png", SRC)

    # 図2：距離と時間
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    d = both.straight_m / 1000
    ax.scatter(d, both.total_min, s=5, color=BLUE, alpha=.25, lw=0, label="1件ずつ（先月と今月）")
    xs = np.linspace(0, d.max(), 50)
    ax.plot(xs, m["rate"] * xs, color=GRAY, lw=2, ls="--", label=f"比例：1kmあたり{m['rate']:.2f}分")
    ax.plot(xs, m["a"] + m["b"] * xs, color=ORANGE, lw=2,
            label=f"直線：{m['a']:.2f}分＋1kmあたり{m['b']:.2f}分")
    bm = [(lo + hi) / 2000 if hi < 9000 else 4.75 for lo, hi in BANDS]
    ax.plot(bm, bands.mean_min, "o", color=INK, ms=6, label="距離の帯ごとの平均")
    ax.set_xlabel("拠点からのまっすぐの距離（km）"); ax.set_ylabel("1件の時間（分）")
    ax.set_ylim(0, np.quantile(both.total_min, .995))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title(f"2km前後の配送は、1km前後の{r21:.2f}倍の時間だった（2倍ではない）", fontsize=12)
    save(fig, "a952_time_vs_distance.png", SRC)

    # 図3：比例で見積もったときの、距離の帯ごとの外れ（今月）＋確かめ
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0), gridspec_kw={"width_ratios": [1.25, 1]})
    labs = ["0〜0.5", "0.5〜1", "1〜2", "2〜3", "3〜4", "4km〜"]
    xb = np.arange(len(BANDS))
    w = .38
    for j, (k, c) in enumerate([(METHODS[0], GRAY), (METHODS[1], ORANGE)]):
        v = [ev[k][f"bias_{lo}_{hi}"] * 100 for lo, hi in BANDS]
        axes[0].bar(xb + (j - .5) * w, v, w, color=c, label=k)
    axes[0].axhline(0, color=INK, lw=.8)
    axes[0].set_xticks(xb); axes[0].set_xticklabels(labs, fontsize=9)
    axes[0].set_xlabel("まっすぐの距離（km）"); axes[0].set_ylabel("見積もりの外れ（%、＋は長く見積もった）")
    axes[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    axes[0].set_title("今月の配送を、先月の決まりで見積もると", fontsize=11)
    g = rob[rob.key == "fixed_median"]
    xl = [f"{v:g}分" for v in g.value]
    axes[1].bar(xl, g.ratio_2km_1km, color=[ORANGE if b else LIGHT for b in g.is_base])
    for xx, yy in zip(xl, g.ratio_2km_1km):
        axes[1].text(xx, yy + .03, f"{yy:.2f}倍", ha="center", fontsize=9)
    axes[1].axhline(2, color=GRAY, ls=":", lw=1)
    axes[1].text(3.45, 2.04, "比例なら2倍", fontsize=8.5, color=GRAY, ha="right")
    axes[1].set_ylim(0, 2.4)
    axes[1].set_xlabel("停めて渡す時間（中央値）"); axes[1].set_ylabel("2km前後÷1km前後の時間")
    axes[1].set_title("停めて渡す時間を変えると（各10回）", fontsize=11)
    fig.tight_layout()
    save(fig, "a952_bias_robustness.png", SRC)


if __name__ == "__main__":
    main()
