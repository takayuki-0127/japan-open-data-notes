"""1106 両端の2つの条件だけを試すと、真ん中の山を見落とすのか？（架空のデータ）

架空の陶芸工房が、窯の温度（1180〜1260度）を決めるために、試し焼きを12個焼く。
温度ごとの「本当の仕上がりの点」（焼き色のむらの少なさ、100点満点）は、作成者が山の形で置く。
山のいちばん高い温度は回ごとに乱数で決め、工房には分からない。1個ごとの仕上がりには、ぶれが入る。
12個を「両端の2温度×6個」「3温度×4個」…「12温度×1個」に分けて焼き、
いちばん良かった温度・2次の曲線を当てはめた山の位置のどちらかで温度を選び、
選んだ温度の本当の点が、山のいちばん高い所よりどれだけ低いかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1106
SRC = "架空の陶芸工房の試し焼き（作成者が置いた山の形とぶれからの乱数、seed 1106）"
LO, HI = 1180.0, 1260.0
BUDGET = 12
BASE = {"height": 80.0, "curv": 12.0, "noise": 4.0, "asym": 1.0, "peak_range": [1200.0, 1240.0]}
LOCS = {"真ん中寄り（1200〜1240度）": [1200.0, 1240.0], "端寄り（1185〜1200度）": [1185.0, 1200.0],
        "範囲の外（1280〜1320度、範囲の中では上り坂）": [1280.0, 1320.0]}
DESIGNS = [2, 3, 4, 6, 12]
REPS = 4000
GRID_REPS = 1000
Z = 1.959964
FINE = np.linspace(LO, HI, 161)


def r(x, d=4):
    return round(float(x), d)


def curve(T, T0, curv, asym, shape=2.0, height=BASE["height"]):
    """山の形：|T−T0|/40 の shape 乗に比例して下がる（2なら丸い山、1ならとがった山）。山より高い温度側は asym 倍の速さで下がる"""
    u = (T - T0) / 40.0
    k = np.where(u > 0, asym, 1.0)
    return height - curv * k * np.abs(u) ** shape


def run(rng, reps, design, peak_range, curv, noise, asym, shape=2.0):
    T0 = rng.uniform(peak_range[0], peak_range[1], reps)
    temps = np.linspace(LO, HI, design)
    per = BUDGET // design
    f_t = curve(temps[None, :], T0[:, None], curv, asym, shape)
    y = f_t[:, :, None] + noise * rng.standard_normal((reps, design, per))
    mean = y.mean(2)
    f_fine = curve(FINE[None, :], T0[:, None], curv, asym, shape)
    best_true = f_fine.max(1)                                  # 範囲の中でいちばん高い本当の点
    # 選び方①：いちばん良かった温度
    pick_obs = temps[mean.argmax(1)]
    # 選び方②：2次の曲線（3温度以上）。範囲の中で曲線がいちばん高い温度
    if design >= 3:
        X = np.vstack([np.ones(design), (temps - 1220) / 40, ((temps - 1220) / 40) ** 2]).T
        coef = np.linalg.lstsq(X, mean.T, rcond=None)[0].T          # 温度ごとの平均に当てはめ（個数は同じ）
        xf = (FINE - 1220) / 40
        fit = coef[:, [0]] + coef[:, [1]] * xf[None, :] + coef[:, [2]] * xf[None, :] ** 2
        pick_fit = FINE[fit.argmax(1)]
    else:
        pick_fit = pick_obs
    f_pick_obs = curve(pick_obs, T0, curv, asym, shape)
    f_pick_fit = curve(pick_fit, T0, curv, asym, shape)
    out = {"T0": T0, "loss_obs": best_true - f_pick_obs, "loss_fit": best_true - f_pick_fit,
           "pick_obs": pick_obs, "pick_fit": pick_fit, "best_true": best_true,
           "end_best": np.maximum(f_t[:, 0], f_t[:, -1])}
    if design == 2:
        se = np.sqrt(y[:, 0].var(1, ddof=1) / per + y[:, 1].var(1, ddof=1) / per)
        out["no_diff"] = np.abs(mean[:, 1] - mean[:, 0]) <= Z * se          # 両端で「差なし」
        out["gain_hidden"] = best_true - np.maximum(f_t[:, 0], f_t[:, 1])    # 両端より山が高い分
    if design == 3:
        se = np.sqrt(y[:, 1].var(1, ddof=1) / per + 0.25 * (y[:, 0].var(1, ddof=1) + y[:, 2].var(1, ddof=1)) / per)
        out["mid_bend_found"] = (mean[:, 1] - 0.5 * (mean[:, 0] + mean[:, 2])) > Z * se
    return out


def summ(o, design):
    d = {"design": f"{design}温度×{BUDGET // design}個", "n_temps": design,
         "loss_obs_mean": r(o["loss_obs"].mean(), 3), "loss_fit_mean": r(o["loss_fit"].mean(), 3),
         "loss_obs_gt5": r((o["loss_obs"] > 5).mean() * 100, 2), "loss_fit_gt5": r((o["loss_fit"] > 5).mean() * 100, 2),
         "pick_end_obs": r(np.isin(o["pick_obs"], [LO, HI]).mean() * 100, 2),
         "pick_end_fit": r(np.isin(o["pick_fit"], [LO, HI]).mean() * 100, 2)}
    if "no_diff" in o:
        d["two_ends_no_diff"] = r(o["no_diff"].mean() * 100, 2)
        d["gain_hidden_mean"] = r(o["gain_hidden"].mean(), 3)
        d["no_diff_and_hidden_gt10"] = r((o["no_diff"] & (o["gain_hidden"] > 10)).mean() * 100, 2)
    if "mid_bend_found" in o:
        d["mid_above_ends_found"] = r(o["mid_bend_found"].mean() * 100, 2)
    return d


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    outs = {}
    for dz in DESIGNS:
        o = run(rng, REPS, dz, BASE["peak_range"], BASE["curv"], BASE["noise"], BASE["asym"])
        outs[dz] = o
        rows.append(summ(o, dz))
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "by_design.csv", index=False)

    # 山の場所を変えると（ほかは基本）
    loc_rows = []
    for li, (lname, pr) in enumerate(LOCS.items()):
        g = np.random.default_rng(SEED * 10 + li)
        for dz in DESIGNS:
            # 真ん中寄りは基本の置き方と同じなので、上の4,000回を使う
            o = outs[dz] if pr == BASE["peak_range"] else run(g, REPS, dz, pr, BASE["curv"], BASE["noise"], BASE["asym"])
            loc_rows.append({"peak_location": lname, **summ(o, dz)})
    by_loc = pd.DataFrame(loc_rows)
    by_loc.to_csv(RES / "by_peak_location.csv", index=False)

    # 確かめ：山の場所3×山の鋭さ3×ぶれ3×左右の形2×山の丸さ2＝108通り
    grid = []
    gi = 0
    for lname, pr in LOCS.items():
        for curv in [6.0, 12.0, 24.0]:
            for noise in [2.0, 4.0, 8.0]:
                for asym in [1.0, 3.0]:
                  for shape in [2.0, 1.0]:
                    g = np.random.default_rng(SEED * 1000 + gi); gi += 1
                    res = {dz: run(g, GRID_REPS, dz, pr, curv, noise, asym, shape) for dz in DESIGNS}
                    row = {"peak_location": lname, "curv": curv, "noise": noise, "asym": asym, "shape": shape}
                    for dz in DESIGNS:
                        row[f"loss_obs_{dz}"] = r(res[dz]["loss_obs"].mean(), 3)
                        if dz >= 3:
                            row[f"loss_fit_{dz}"] = r(res[dz]["loss_fit"].mean(), 3)
                    row["two_ends_no_diff"] = r(res[2]["no_diff"].mean() * 100, 2)
                    row["two_ends_no_diff_hidden_gt10"] = r((res[2]["no_diff"] & (res[2]["gain_hidden"] > 10)).mean() * 100, 2)
                    row["mid_above_ends_found_3"] = r(res[3]["mid_bend_found"].mean() * 100, 2)
                    cands = {"2温度": row["loss_obs_2"], **{f"{dz}温度・良かった温度": row[f"loss_obs_{dz}"] for dz in DESIGNS[1:]},
                             **{f"{dz}温度・曲線": row[f"loss_fit_{dz}"] for dz in DESIGNS[1:]}}
                    row["best_way"] = min(cands, key=cands.get)
                    grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    lk = list(LOCS)
    gsum = {"n": int(len(grid))}
    for name, key in zip(["middle", "near_end", "outside"], lk):
        gg = grid[grid.peak_location == key]
        gsum[name] = {
            "loss_2_range": [r(gg.loss_obs_2.min(), 3), r(gg.loss_obs_2.max(), 3)],
            "loss_fit3_range": [r(gg.loss_fit_3.min(), 3), r(gg.loss_fit_3.max(), 3)],
            "fit3_better_than_2": int((gg.loss_fit_3 < gg.loss_obs_2).sum()),
            "two_ends_no_diff_range": [r(gg.two_ends_no_diff.min(), 2), r(gg.two_ends_no_diff.max(), 2)],
            "no_diff_hidden_gt10_range": [r(gg.two_ends_no_diff_hidden_gt10.min(), 2), r(gg.two_ends_no_diff_hidden_gt10.max(), 2)],
            "mid_above_ends_found_3_range": [r(gg.mid_above_ends_found_3.min(), 2), r(gg.mid_above_ends_found_3.max(), 2)],
            "fit3_better_than_2_shape1": int((gg[gg["shape"] == 1].loss_fit_3 < gg[gg["shape"] == 1].loss_obs_2).sum()),
            "fit3_minus_obs3_shape1": [r((gg[gg["shape"] == 1].loss_fit_3 - gg[gg["shape"] == 1].loss_obs_3).min(), 3),
                                       r((gg[gg["shape"] == 1].loss_fit_3 - gg[gg["shape"] == 1].loss_obs_3).max(), 3)],
            "fit3_minus_obs3_shape2": [r((gg[gg["shape"] == 2].loss_fit_3 - gg[gg["shape"] == 2].loss_obs_3).min(), 3),
                                       r((gg[gg["shape"] == 2].loss_fit_3 - gg[gg["shape"] == 2].loss_obs_3).max(), 3)],
            "best_way_counts": {k: int(v) for k, v in gg.best_way.value_counts().items()},
            "best_way_is_curve": int(gg.best_way.str.contains("曲線").sum()),
            "best_way_counts_sharp_asym": {k: int(v) for k, v in gg[(gg["shape"] == 1) & (gg.asym == 3)].best_way.value_counts().items()},
            "fit3_loss_sharp_asym": [r(gg[(gg["shape"] == 1) & (gg.asym == 3)].loss_fit_3.min(), 3), r(gg[(gg["shape"] == 1) & (gg.asym == 3)].loss_fit_3.max(), 3)],
            "obs12_loss_sharp_asym": [r(gg[(gg["shape"] == 1) & (gg.asym == 3)].loss_obs_12.min(), 3), r(gg[(gg["shape"] == 1) & (gg.asym == 3)].loss_obs_12.max(), 3)],
            "n": int(len(gg))}
    gin = grid[grid.peak_location != lk[2]]
    gsum["inside_fit3_better_than_2"] = int((gin.loss_fit_3 < gin.loss_obs_2).sum())
    gsum["inside_n"] = int(len(gin))
    go = grid[grid.peak_location == lk[2]]
    lcols = [c for c in grid.columns if c.startswith("loss_")]
    gsum["outside_two_ends_min_or_tie"] = int((go.loss_obs_2 <= go[lcols].min(1)).sum())
    # 本当の山（基本の置き方、山の位置1220度）での両端と山の高さ（式どおり）
    ref = {"peak_1220_end_1180": r(curve(np.array(LO), 1220.0, BASE["curv"], 1.0), 3),
           "peak_1220_end_1260": r(curve(np.array(HI), 1220.0, BASE["curv"], 1.0), 3), "height": BASE["height"]}
    # 両端で正しい方を選べたときの不足の期待（式）：山から近い端までの距離 d が20〜40度で一様 → 12×E[(d/40)²]
    dd = np.linspace(20, 40, 200001)
    ref["two_end_loss_if_right_end_formula"] = r(BASE["curv"] * np.mean((dd / 40) ** 2), 3)

    # data：1回分の試し焼き（山の位置は乱数、2温度×6個と3温度×4個）
    g1 = np.random.default_rng(SEED + 1)
    T0 = float(g1.uniform(*BASE["peak_range"]))
    recs = []
    for dz in [2, 3]:
        temps = np.linspace(LO, HI, dz)
        for T in temps:
            for j in range(BUDGET // dz):
                recs.append({"design": f"{dz}temps", "temp": int(T), "piece": j + 1,
                             "score": round(float(curve(np.array(T), T0, BASE["curv"], 1.0) + BASE["noise"] * g1.standard_normal()), 4)})
    pd.DataFrame(recs).to_csv(DATA / "pieces_one_trial.csv", index=False)
    pd.DataFrame({"temp": FINE, "true_score": curve(FINE, T0, BASE["curv"], 1.0).round(4)}).to_csv(DATA / "true_curve_one_trial.csv", index=False)

    out = {"base": BASE, "range": [LO, HI], "budget": BUDGET, "reps": REPS, "reference_curve": ref,
           "one_trial_peak_temp": r(T0, 2), "by_design": tab.to_dict("records"),
           "by_peak_location": by_loc.to_dict("records"), "grid_summary": gsum}
    json.dump(out, open(RES / "a1106_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の試し焼きと本当の山
    d1 = pd.read_csv(DATA / "pieces_one_trial.csv")
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.plot(FINE, curve(FINE, T0, BASE["curv"], 1.0), color=GRAY, lw=2, label="本当の仕上がりの点（作成者が置いた山）")
    a = d1[d1.design == "2temps"]; b = d1[d1.design == "3temps"]
    ax.scatter(a.temp - 1.5, a.score, color=ORANGE, s=18, label="両端の2温度×6個")
    ax.scatter(b.temp + 1.5, b.score, color=BLUE, s=18, marker="s", label="3温度×4個")
    ax.axvline(T0, color=GRAY, lw=0.8, ls=":")
    ax.text(T0 + 1, 52, f"山の位置 {T0:.2f}度", fontsize=8, color=INK)
    ax.set_xlabel("窯の温度（度）"); ax.set_ylabel("仕上がりの点（焼き色のむらの少なさ）")
    ax.set_ylim(50, 90)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("両端の2温度だけでは、真ん中の山の高さは測れない（1回分）")
    save(fig, "a1106_one_trial.png", SRC)

    # 図2：割り方ごとの、選んだ温度の点の不足（山が範囲の中）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(len(tab))
    ax.bar(x - 0.2, tab.loss_obs_mean, 0.4, color=ORANGE, label="いちばん良かった温度を選ぶ")
    ax.bar(x[1:] + 0.2, tab.loss_fit_mean[1:], 0.4, color=BLUE, label="2次の曲線の山の温度を選ぶ")
    for i in range(len(tab)):
        ax.text(i - 0.2, tab.loss_obs_mean[i] + 0.2, f"{tab.loss_obs_mean[i]:.3f}", ha="center", fontsize=8)
        if i > 0:
            ax.text(i + 0.2, tab.loss_fit_mean[i] + 0.2, f"{tab.loss_fit_mean[i]:.3f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(tab.design)
    ax.set_ylim(0, tab.loss_obs_mean.max() * 1.25)
    ax.set_ylabel("山の高さより低かった分（点、4,000回の平均）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("山が1200〜1240度にあるとき、試し焼き12個の割り方と点の不足")
    save(fig, "a1106_designs.png", SRC)

    # 図3：山の場所ごと（両端2温度 vs 3温度・曲線 vs 6温度・良かった温度）
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    names = ["2温度×6個", "3温度×4個・曲線", "6温度×2個・良かった温度"]
    cols = [ORANGE, BLUE, GREEN]
    w = 0.26
    for j, (nm, c) in enumerate(zip(names, cols)):
        vals = []
        for lname in LOCS:
            s = by_loc[by_loc.peak_location == lname].set_index("n_temps")
            vals.append(s.loc[2, "loss_obs_mean"] if j == 0 else (s.loc[3, "loss_fit_mean"] if j == 1 else s.loc[6, "loss_obs_mean"]))
        ax.bar(np.arange(3) + (j - 1) * w, vals, w, color=c, label=nm)
        for i, v in enumerate(vals):
            ax.text(i + (j - 1) * w, v + 0.2, f"{v:.3f}", ha="center", fontsize=7.5)
    ax.set_xticks(range(3)); ax.set_xticklabels([k.replace("（", "\n（") for k in LOCS], fontsize=8.5)
    ax.set_ylabel("山の高さより低かった分（点）")
    ax.set_ylim(0, by_loc.loss_obs_mean.max() * 1.3)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("山が真ん中寄りのとき、両端の2温度の不足がいちばん大きかった（基本の置き方）")
    save(fig, "a1106_location.png", SRC)

    out["run_sec"] = r(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
