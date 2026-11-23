"""1034 混む時間帯を避けると、どれだけ早く着くのか？（選んだ人の違い）（架空のデータ）

架空の通勤者3,000人の20日分。人ごとに道のり（km）と「混む時間帯に乗ると1kmあたり何分よけいにかかるか」を置く。
混む時間帯を避ける日の割合は人ごとに違い、近くに住む人・混む時間帯の遅れが大きい人ほど避けやすいと置く（基本）。
避けた便と混む便の所要時間の差（そのままの比べ方）と、作成者が置いた本当の得（同じ人が避けたときに縮む分数）を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1034
SRC = "架空の通勤者の所要時間（作成者が乱数で作成、seed 1034）"
N_PEOPLE, N_DAYS = 3000, 20
BASE = dict(a=-1.0, b_flex=1.5, b_d=-0.8, b_g=0.8, noise=3.0)


def make_people(rng, n=N_PEOPLE):
    d = np.clip(np.exp(rng.normal(np.log(12), 0.6, n)), 2, 40)          # 道のり（km）
    g = rng.gamma(2.0, 0.25, n)                                          # 混む時間帯の1kmあたりのよけいな分数
    flex = rng.normal(0, 1, n)                                           # 時間をずらしやすさ（観測できない）
    return d, g, flex


def simulate(rng, P, n=N_PEOPLE, days=N_DAYS):
    d, g, flex = make_people(rng, n)
    zd = (np.log(d) - np.log(d).mean()) / np.log(d).std()
    zg = (g - g.mean()) / g.std()
    p = 1 / (1 + np.exp(-(P["a"] + P["b_flex"] * flex + P["b_d"] * zd + P["b_g"] * zg)))   # 避ける日の確率
    off = rng.random((n, days)) < p[:, None]
    base = 8 + 2.0 * d                                                   # 空いている時間帯の所要時間（分）
    gain = g * d                                                         # 本当の得：同じ人が避けたときに縮む分数
    t = base[:, None] + gain[:, None] * (~off) + rng.normal(0, P["noise"], (n, days))
    return dict(d=d, g=g, p=p, off=off, t=t, gain=gain)


def estimate(s):
    d, off, t, gain = s["d"], s["off"], s["t"], s["gain"]
    peak = ~off
    D = np.repeat(d[:, None], off.shape[1], 1)
    naive = t[peak].mean() - t[off].mean()
    # 1kmあたりの差に全員の平均の道のりを掛ける
    perkm = ((t / D)[peak].mean() - (t / D)[off].mean()) * d.mean()
    # 道のりを入れた回帰（所要時間 ＝ 切片 ＋ 混む日 ＋ 道のり）
    X = np.column_stack([np.ones(t.size), peak.ravel().astype(float), D.ravel()])
    coef = np.linalg.lstsq(X, t.ravel(), rcond=None)[0]
    # 同じ人の、混む日と避けた日の差（両方の日がある人）
    npk, nof = peak.sum(1), off.sum(1)
    both = (npk > 0) & (nof > 0)
    mp = np.where(peak, t, 0).sum(1)[both] / npk[both]
    mo = np.where(off, t, 0).sum(1)[both] / nof[both]
    within = float((mp - mo).mean())
    return {
        "naive": float(naive), "per_km": float(perkm), "regress_distance": float(coef[1]), "within_person": within,
        "true_all": float(gain.mean()),
        "true_peak_trips": float((gain[:, None] * peak).sum() / peak.sum()),
        "true_off_trips": float((gain[:, None] * off).sum() / off.sum()),
        "true_both_people": float(gain[both].mean()),
        "off_share": float(off.mean()), "both_people_share": float(both.mean()),
        "never_off_share": float((nof == 0).mean()), "always_off_share": float((npk == 0).mean()),
        "dist_peak_trips": float(D[peak].mean()), "dist_off_trips": float(D[off].mean()),
    }


LABELS = {"naive": "そのまま比べる（混む便の平均−避けた便の平均）",
          "per_km": "1kmあたりで比べる（×全員の平均の道のり）",
          "regress_distance": "道のりをそろえる（道のりを入れた回帰）",
          "within_person": "同じ人の、混む日と避けた日の差",
          "true_all": "本当の得：全員の平均",
          "true_peak_trips": "本当の得：いま混む時間帯に乗っている便",
          "true_off_trips": "本当の得：いま避けている便",
          "true_both_people": "本当の得：両方の日がある人"}


def main():
    rng = np.random.default_rng(SEED)
    out = {"params": BASE, "people": N_PEOPLE, "days": N_DAYS,
           "extra_min_per_km_peak_mean": 2.0 * 0.25, "off_peak_minutes": "8 + 2.0 * distance_km"}

    # 1回分の通勤者（data）
    s = simulate(rng, BASE)
    npk, nof = (~s["off"]).sum(1), s["off"].sum(1)
    mp = np.where(~s["off"], s["t"], 0).sum(1) / np.maximum(npk, 1)
    mo = np.where(s["off"], s["t"], 0).sum(1) / np.maximum(nof, 1)
    ppl = pd.DataFrame({"person_id": np.arange(1, N_PEOPLE + 1), "distance_km": s["d"].round(3),
                        "extra_min_per_km_peak": s["g"].round(4), "true_gain_min": s["gain"].round(3),
                        "p_avoid": s["p"].round(4), "days_peak": npk, "days_avoid": nof,
                        "mean_min_peak": np.where(npk > 0, mp, np.nan).round(3),
                        "mean_min_avoid": np.where(nof > 0, mo, np.nan).round(3)})
    ppl.to_csv(DATA / "commuters.csv", index=False)
    out["one_draw"] = {k: round(v, 3) for k, v in estimate(s).items()}

    # 2) 基本：100回の平均
    reps = pd.DataFrame([estimate(simulate(np.random.default_rng(SEED * 1000 + r), BASE)) for r in range(100)])
    reps.round(4).to_csv(RES / "reps_base.csv", index=False)
    summ = []
    for k, lab in LABELS.items():
        summ.append({"key": k, "label": lab, "mean": round(float(reps[k].mean()), 3),
                     "p10": round(float(reps[k].quantile(.1)), 3), "p90": round(float(reps[k].quantile(.9)), 3)})
    summ = pd.DataFrame(summ)
    summ.to_csv(RES / "estimates_base.csv", index=False)
    out["base_100reps"] = summ.to_dict("records")
    out["base_other"] = {k: round(float(reps[k].mean()), 4) for k in ["dist_peak_trips", "dist_off_trips"]}
    out["base_other"].update({k + "_pct": round(float(reps[k].mean()) * 100, 2) for k in
                              ["off_share", "both_people_share", "never_off_share", "always_off_share"]})
    m = summ.set_index("key")["mean"]
    out["base_ratios"] = {"naive_over_true_peak": round(float(m["naive"] / m["true_peak_trips"]), 3),
                          "regress_over_true_peak": round(float(m["regress_distance"] / m["true_peak_trips"]), 3),
                          "within_over_true_peak": round(float(m["within_person"] / m["true_peak_trips"]), 3),
                          "true_off_over_true_peak": round(float(m["true_off_trips"] / m["true_peak_trips"]), 3)}

    # 式との照らし合わせ：そのままの差 − 混む便の本当の得 ＝ 2分/km ×（混む便の平均の道のり − 避けた便の平均の道のり）
    ob = out["base_other"]
    out["base_formula_check"] = {
        "naive_minus_true_peak": round(float(m["naive"] - m["true_peak_trips"]), 3),
        "formula_2min_per_km_times_distance_gap": round(2.0 * (ob["dist_peak_trips"] - ob["dist_off_trips"]), 3)}

    # 3) 確かめ：道のりでの選び方 × 得の大きさでの選び方（9通り、各20回）
    grid = []
    gi = 0
    for b_d in [-0.8, 0.0, 0.8]:
        for b_g in [-0.8, 0.0, 0.8]:
            P = dict(BASE, b_d=b_d, b_g=b_g)
            r = pd.DataFrame([estimate(simulate(np.random.default_rng(SEED * 100 + gi * 50 + k), P)) for k in range(20)])
            gi += 1
            row = {"b_d": b_d, "b_g": b_g}
            for k in ["naive", "per_km", "regress_distance", "within_person", "true_all", "true_peak_trips",
                      "true_off_trips", "true_both_people", "off_share", "dist_peak_trips", "dist_off_trips"]:
                row[k] = round(float(r[k].mean()), 3)
            grid.append(row)
    grid = pd.DataFrame(grid)
    grid["naive_minus_true_peak"] = (grid.naive - grid.true_peak_trips).round(3)
    grid["formula_distance_gap_x2"] = (2.0 * (grid.dist_peak_trips - grid.dist_off_trips)).round(3)
    grid["regress_minus_true_peak"] = (grid.regress_distance - grid.true_peak_trips).round(3)
    grid["within_minus_true_peak"] = (grid.within_person - grid.true_peak_trips).round(3)
    grid["within_minus_true_both"] = (grid.within_person - grid.true_both_people).round(3)
    grid.to_csv(RES / "grid_selection.csv", index=False)
    out["grid_summary"] = {
        "naive_min": float(grid.naive.min()), "naive_max": float(grid.naive.max()),
        "true_peak_min": float(grid.true_peak_trips.min()), "true_peak_max": float(grid.true_peak_trips.max()),
        "naive_minus_true_peak_min": float(grid.naive_minus_true_peak.min()),
        "naive_minus_true_peak_max": float(grid.naive_minus_true_peak.max()),
        "regress_minus_true_peak_min": float(grid.regress_minus_true_peak.min()),
        "regress_minus_true_peak_max": float(grid.regress_minus_true_peak.max()),
        "within_minus_true_both_min": float(grid.within_minus_true_both.min()),
        "within_minus_true_both_max": float(grid.within_minus_true_both.max()),
        "within_minus_true_peak_min": float(grid.within_minus_true_peak.min()),
        "within_minus_true_peak_max": float(grid.within_minus_true_peak.max()),
        "n_naive_negative": int((grid.naive < 0).sum()),
        "max_gap_naive_bias_vs_formula": round(float((grid.naive_minus_true_peak - grid.formula_distance_gap_x2).abs().max()), 3),
        "true_off_min": float(grid.true_off_trips.min()), "true_off_max": float(grid.true_off_trips.max()),
        "within_min": float(grid.within_person.min()), "within_max": float(grid.within_person.max()),
        "regress_min": float(grid.regress_distance.min()), "regress_max": float(grid.regress_distance.max()),
        "per_km_min": float(grid.per_km.min()), "per_km_max": float(grid.per_km.max()),
        "bd0_bg0": grid[(grid.b_d == 0) & (grid.b_g == 0)].iloc[0].to_dict(),
        "bd_pos_bg_neg": grid[(grid.b_d == 0.8) & (grid.b_g == -0.8)].iloc[0].to_dict(),
    }

    json.dump(out, open(RES / "a1034_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：比べ方ごとの「避けると何分早いか」（基本、100回の平均）
    order = ["naive", "per_km", "regress_distance", "within_person", "true_peak_trips", "true_all",
             "true_off_trips"]
    sv = summ.set_index("key").loc[order]
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    cols = [ORANGE, ORANGE, ORANGE, ORANGE, BLUE, LIGHT, LIGHT]
    ax.barh(range(len(order)), sv["mean"], color=cols)
    for i, v in enumerate(sv["mean"]):
        ax.text(v + 0.2, i, f"{v:.2f}分", va="center", fontsize=9)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(sv["label"], fontsize=9); ax.invert_yaxis()
    ax.set_xlabel("混む時間帯を避けると、何分早く着くか（100回の平均）")
    ax.set_xlim(0, sv["mean"].max() * 1.18)
    ax.set_title("そのまま比べると、避けた人の道のりの短さが差に混ざる")
    save(fig, "a1034_estimates.png", SRC)

    # 図2：1回分の通勤者。道のりと、混む日・避けた日の平均の所要時間
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ok_p, ok_o = npk > 0, nof > 0
    ax.scatter(s["d"][ok_p], mp[ok_p], s=5, color=ORANGE, alpha=.35, lw=0,
               label=f"混む時間帯に乗った日の平均（{int(ok_p.sum()):,}人）")
    ax.scatter(s["d"][ok_o], mo[ok_o], s=5, color=BLUE, alpha=.35, lw=0,
               label=f"避けた日の平均（{int(ok_o.sum()):,}人）")
    ax.set_xlabel("道のり（km）"); ax.set_ylabel("所要時間（分）")
    ax.legend(frameon=False, fontsize=9, markerscale=3)
    ax.set_title(f"避けた便は道のりが短い（平均 {out['one_draw']['dist_off_trips']:.1f}km 対 "
                 f"{out['one_draw']['dist_peak_trips']:.1f}km、1回分）")
    save(fig, "a1034_scatter.png", SRC)

    # 図3：選び方9通りの、そのままの差と本当の得
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    lab = [f"道のり{bd:+.1f}\n得{bg:+.1f}" for bd, bg in zip(grid.b_d, grid.b_g)]
    x = np.arange(len(grid))
    ax.bar(x - 0.2, grid.naive, width=0.4, color=ORANGE, label="そのまま比べた差")
    ax.bar(x + 0.2, grid.true_peak_trips, width=0.4, color=BLUE, label="本当の得（いま混む時間帯に乗っている便）")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8)
    ax.set_ylabel("分（20回の平均）")
    ax.set_xlabel("避けやすさの置き方（道のりが長いほど・得が大きいほど避けやすい度合い）", fontsize=9)
    ax.set_ylim(grid.naive.min() - 1, grid.naive.max() * 1.25)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("選び方で、そのままの差は本当の得の上にも下にも、負にもなる")
    save(fig, "a1034_grid.png", SRC)


if __name__ == "__main__":
    main()
