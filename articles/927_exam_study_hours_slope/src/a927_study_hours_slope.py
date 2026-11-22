"""927 勉強時間と点数の相関から、何時間で何点上がると言えるのか？（架空のデータ）

架空の社内資格試験（100点満点）の受験者2,000人。受験者ごとに「もとの力」（勉強しなかったときの点）を置き、
勉強時間の効き目（伸びはだんだん小さくなる）と、もとの力と勉強時間の結びつき、自己申告の時間のずれを作成者が置く。
「全員が10時間多く勉強したら平均何点上がるか」（本当の効き目）と、点数を申告の時間で直線に当てはめた傾きを比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 927
SRC = "架空の社内資格試験の受験者（作成者が乱数で作成、seed 927）"
N = 2000
BASE = {"rho": 0.3, "rep_sd": 0.4, "tau": 120.0}
G = 30.0           # 勉強をいくらでも増やしたときの伸びの上限（点）
B_MEAN, B_SD = 45.0, 12.0
H_MED, H_SIG = 80.0, 0.6
NOISE = 6.0        # その日の出来の振れ（点）
REPS = 100


LIN = 0.12        # 確かめ用：伸びが減らない（直線）ときの1時間あたりの点


def gain(h, tau):
    if tau is None:
        return LIN * h
    return G * (1 - np.exp(-h / tau))


def log_effect(r1, s1, r2=None, s2=None):
    """対数の時間で当てはめ、本人の時間に10時間を足したときの伸びを平均する"""
    x1 = np.log(np.maximum(r1, 5))
    if r2 is None:
        b = slope(x1, s1)
    else:
        b = slope(np.log(np.maximum(r2, 5)) - x1, s2 - s1)
    return float(b * np.mean(np.log((np.maximum(r1, 5) + 10) / np.maximum(r1, 5))))


def people(rng, n=N, rho=BASE["rho"], rep_sd=BASE["rep_sd"], tau=BASE["tau"]):
    zb = rng.standard_normal(n)
    base = B_MEAN + B_SD * zb
    hours = H_MED * np.exp(H_SIG * (rho * zb + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)))
    eps = NOISE * rng.standard_normal(n)
    score = np.clip(base + gain(hours, tau) + eps, 0, 100)
    score10 = np.clip(base + gain(hours + 10, tau) + eps, 0, 100)
    rep = np.round(hours * np.exp(rep_sd * rng.standard_normal(n)) / 5) * 5
    rep = np.maximum(rep, 0)
    return pd.DataFrame({"base": base, "hours": hours, "reported": rep, "score": score, "score_plus10": score10})


def slope(x, y):
    x = x - x.mean()
    return float((x * (y - y.mean())).sum() / (x * x).sum())


def two_exams(rng, n=N, rho=BASE["rho"], rep_sd=BASE["rep_sd"], tau=BASE["tau"]):
    """同じ人が同じ水準の試験を2回受ける。時間は人ごとの分と回ごとの分を半分ずつ"""
    zb = rng.standard_normal(n)
    base = B_MEAN + B_SD * zb
    u = rng.standard_normal(n)
    out = []
    for _ in range(2):
        v = rng.standard_normal(n)
        h = H_MED * np.exp(H_SIG * (rho * zb + np.sqrt(1 - rho ** 2) * (np.sqrt(.5) * u + np.sqrt(.5) * v)))
        s = np.clip(base + gain(h, tau) + NOISE * rng.standard_normal(n), 0, 100)
        r = np.round(h * np.exp(rep_sd * rng.standard_normal(n)) / 5) * 5
        out.append((h, r, s))
    (h1, r1, s1), (h2, r2, s2) = out
    return (slope(r2 - r1, s2 - s1) * 10, slope(h2 - h1, s2 - s1) * 10,
            log_effect(r1, s1, r2, s2), log_effect(h1, s1, h2, s2))


def one_cell(rho, rep_sd, tau, key):
    rows = []
    for r in range(REPS):
        g = np.random.default_rng([SEED, key, r])
        d = people(g, rho=rho, rep_sd=rep_sd, tau=tau)
        fd_rep, fd_true, fdl_rep, fdl_true = two_exams(g, rho=rho, rep_sd=rep_sd, tau=tau)
        rows.append({"true10": float((d.score_plus10 - d.score).mean()),
                     "ols_reported10": slope(d.reported, d.score) * 10,
                     "ols_true_hours10": slope(d.hours, d.score) * 10,
                     "within10": fd_rep, "within_true_hours10": fd_true,
                     "log_reported": log_effect(d.reported.values, d.score.values),
                     "log_true_hours": log_effect(d.hours.values, d.score.values),
                     "within_log_reported": fdl_rep, "within_log_true_hours": fdl_true,
                     "corr": float(np.corrcoef(d.reported, d.score)[0, 1])})
    t = pd.DataFrame(rows)
    q = lambda c, p: round(float(t[c].quantile(p)), 2)
    return {"rho": rho, "rep_sd": rep_sd, "tau": tau,
            "true10": round(float(t.true10.mean()), 2),
            "ols_reported10": round(float(t.ols_reported10.mean()), 2),
            "ols_reported10_p10": q("ols_reported10", .1), "ols_reported10_p90": q("ols_reported10", .9),
            "ols_true_hours10": round(float(t.ols_true_hours10.mean()), 2),
            "within10": round(float(t.within10.mean()), 2),
            "within10_p10": q("within10", .1), "within10_p90": q("within10", .9),
            "within_true_hours10": round(float(t.within_true_hours10.mean()), 2),
            "log_reported": round(float(t.log_reported.mean()), 2),
            "log_true_hours": round(float(t.log_true_hours.mean()), 2),
            "within_log_reported": round(float(t.within_log_reported.mean()), 2),
            "within_log_true_hours": round(float(t.within_log_true_hours.mean()), 2),
            "corr": round(float(t["corr"].mean()), 3),
            "ratio_ols_to_true": round(float(t.ols_reported10.mean() / t.true10.mean()), 2)}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    d = people(rng)
    out_df = d[["base", "hours", "reported", "score"]].copy()
    out_df.insert(0, "person_id", np.arange(1, N + 1))
    out_df.columns = ["person_id", "base_true", "hours_true", "hours_reported", "score"]
    out_df.to_csv(DATA / "learners.csv", index=False, float_format="%.2f")

    one = {"corr_reported_score": round(float(np.corrcoef(d.reported, d.score)[0, 1]), 3),
           "true10": round(float((d.score_plus10 - d.score).mean()), 2),
           "ols_reported10": round(slope(d.reported, d.score) * 10, 2),
           "hours_median": round(float(d.hours.median()), 1),
           "hours_p10": round(float(d.hours.quantile(.1)), 1), "hours_p90": round(float(d.hours.quantile(.9)), 1),
           "score_mean": round(float(d.score.mean()), 1)}

    # 基本の置き方（100回）
    base = one_cell(BASE["rho"], BASE["rep_sd"], BASE["tau"], 0)

    # 確かめ：もとの力との結びつき × 申告のずれ（伸びの減り方は基本）
    grid = []
    k = 1
    for rho in [-0.6, -0.3, 0.0, 0.3, 0.6]:
        for rs in [0.0, 0.4, 0.8]:
            grid.append(one_cell(rho, rs, BASE["tau"], k)); k += 1
    grid = pd.DataFrame(grid)
    # 確かめ：伸びの減り方（tau）
    tau_rows = []
    for j, tau in enumerate([60.0, 120.0, 240.0, None]):
        tau_rows.append(one_cell(0.0, 0.0, tau, 100 + j))
    tau_df = pd.DataFrame(tau_rows)
    tau_df["tau_label"] = ["60時間", "120時間（基本）", "240時間", "減らない（直線）"]
    robust = pd.concat([grid.assign(part="rho_x_report"), tau_df.drop(columns="tau_label").assign(part="tau_rho0_report0")])
    robust.to_csv(RES / "robustness.csv", index=False)

    # いまの勉強時間ごとの、あと10時間の伸び（本当の値、式）
    marg = []
    for h in [10, 30, 50, 80, 120, 200, 300, 400]:
        marg.append({"hours_now": h, "gain_next10": round(float(gain(h + 10, BASE["tau"]) - gain(h, BASE["tau"])), 2)})
    marg = pd.DataFrame(marg)
    marg.to_csv(RES / "gain_by_hours.csv", index=False)

    out = {"settings": {"n_people": N, "linear_check_per_hour": LIN, "reps": REPS, "base_mean": B_MEAN, "base_sd": B_SD, "hours_median": H_MED,
                        "hours_log_sd": H_SIG, "gain_max": G, "tau": BASE["tau"], "rho": BASE["rho"],
                        "report_log_sd": BASE["rep_sd"], "noise_sd": NOISE},
           "one_draw": one, "base_100reps": base,
           "grid_rho_report": grid.to_dict("records"),
           "grid_tau": tau_df.to_dict("records"),
           "gain_next10_by_hours": marg.to_dict("records"),
           "summary": {"ols_reported10_range": [float(grid.ols_reported10.min()), float(grid.ols_reported10.max())],
                       "true10_range": [float(grid.true10.min()), float(grid.true10.max())],
                       "ratio_range": [float(grid.ratio_ols_to_true.min()), float(grid.ratio_ols_to_true.max())],
                       "within10_range": [float(grid.within10.min()), float(grid.within10.max())],
                       "within_true_hours10_range": [float(grid.within_true_hours10.min()),
                                                     float(grid.within_true_hours10.max())],
                       "within_log_true_hours_range": [float(grid.within_log_true_hours.min()),
                                                       float(grid.within_log_true_hours.max())],
                       "within_log_reported_range": [float(grid.within_log_reported.min()),
                                                     float(grid.within_log_reported.max())],
                       "within10_by_report": {str(k): [float(v.within10.min()), float(v.within10.max())]
                                              for k, v in grid.groupby("rep_sd")},
                       "within_log_reported_with_error_range": [float(grid[grid.rep_sd > 0].within_log_reported.min()),
                                                                float(grid[grid.rep_sd > 0].within_log_reported.max())],
                       "within_log_true_hours_report0_range": [float(grid[grid.rep_sd == 0].within_log_true_hours.min()),
                                                               float(grid[grid.rep_sd == 0].within_log_true_hours.max())],
                       "ratio_ols_to_true_by_tau": tau_df.ratio_ols_to_true.tolist(),
                       "rho0_rep0_ols": float(grid[(grid.rho == 0) & (grid.rep_sd == 0)].ols_reported10.iloc[0]),
                       "rho0_rep0_true": float(grid[(grid.rho == 0) & (grid.rep_sd == 0)].true10.iloc[0])}}
    json.dump(out, open(RES / "a927_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：申告の時間と点数（1回分）と、当てはめた直線・本当の伸び
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    ax.scatter(d.reported, d.score, s=6, color=BLUE, alpha=.35, lw=0)
    xs = np.linspace(0, 400, 200)
    b = slope(d.reported, d.score)
    ax.plot(xs, d.score.mean() + b * (xs - d.reported.mean()), color=ORANGE, lw=2,
            label=f"当てはめた直線（10時間で+{b*10:.2f}点）")
    ax.plot(xs, B_MEAN + gain(xs, BASE["tau"]), color=INK, lw=1.6, ls="--",
            label="本当の伸び（もとの力が平均の人）")
    ax.set_xlim(0, 400); ax.set_ylim(0, 100)
    ax.set_xlabel("申告の勉強時間（時間）"); ax.set_ylabel("点数（100点満点）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"相関は{one['corr_reported_score']:.2f}。直線の傾きは本当の伸びとは別のもの（2,000人）")
    save(fig, "a927_scatter.png", SRC)

    # 図2：結びつき×申告のずれで、傾きはどう動くか
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    cols = {0.0: INK, 0.4: BLUE, 0.8: LIGHT}
    for rs, gg in grid.groupby("rep_sd"):
        lab = {0.0: "申告のずれなし", 0.4: "申告のずれ 中（基本）", 0.8: "申告のずれ 大"}[rs]
        ax.plot(gg.rho, gg.ols_reported10, marker="o", color=cols[rs], label="直線の傾き：" + lab)
    gw = grid[grid.rep_sd == 0.4]
    ax.plot(gw.rho, gw.within10, marker="s", color=GREEN, ls=":", label="同じ人の2回の差から（ずれ 中）")
    g0 = grid[grid.rep_sd == 0.0]
    ax.plot(g0.rho, g0.within_log_true_hours, marker="D", color=GREEN, ls="--",
            label="同じ人の2回の差＋曲がりを入れる（ずれなし）")
    ax.plot(gw.rho, gw.true10, color=ORANGE, lw=2.2, label="本当の効き目（全員が10時間増やしたとき）")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_xticks([-0.6, -0.3, 0, 0.3, 0.6])
    ax.set_xlabel("もとの力と勉強時間の結びつき（負：力の低い人ほど長く勉強する）")
    ax.set_ylabel("10時間あたりの点（100回の平均）")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    ax.set_title("傾きは、誰が長く勉強するかで本当の効き目の上にも下にもずれる")
    save(fig, "a927_slope_grid.png", SRC, y=-0.17)

    # 図3：いまの勉強時間ごとの、あと10時間の伸び
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    hh = np.arange(10, 401, 5)
    ax.plot(hh, gain(hh + 10, BASE["tau"]) - gain(hh, BASE["tau"]), color=BLUE, lw=2, label="本当のあと10時間の伸び")
    ax.axhline(base["true10"], color=ORANGE, ls="--", lw=1.4,
               label=f"全員の平均（{base['true10']:.2f}点）")
    ax.set_xlabel("いまの勉強時間（時間）"); ax.set_ylabel("あと10時間で上がる点")
    ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9)
    m0, m1 = marg.gain_next10.iloc[0], marg.gain_next10.iloc[-1]
    ax.set_title(f"同じ10時間でも、いまの時間で伸びは{m0:.2f}点から{m1:.2f}点まで変わる（置いた伸び方）")
    save(fig, "a927_gain_by_hours.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
