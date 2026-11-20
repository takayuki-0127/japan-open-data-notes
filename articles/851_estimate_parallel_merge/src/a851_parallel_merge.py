"""851 並行する作業が増えると、全体の遅れはどれだけ増えるのか？（架空のデータ）

架空のプロジェクト。k 本の作業を同時に進め、全部が終わったら次の段階に進む（合流）。
1本の作業の日数は右に長い対数正規分布（中央値20日・ばらつき sigma）。計画は「1本ごとの見積もり」をそのまま合流の日にする。
1本ごとには正しい見積もりでも、合流の日は一番遅い1本で決まるので、本数が増えるほど遅れる。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 851
SRC = "架空のプロジェクトの作業日数（作成者が乱数で作成、seed 851）"
N_RUN = 200_000
MED = 20.0
SIGMA = 0.4
Z80 = 0.8416212335729143
KS = [1, 2, 3, 4, 6, 8, 12, 16]


def draw(rng, meds, sigma, n_run, rho=0.0, shape="lognormal"):
    meds = np.asarray(meds, float)
    k = len(meds)
    if shape == "gamma":
        cv = np.sqrt(np.exp(sigma ** 2) - 1); sh = 1 / cv ** 2
        base_med = np.median(np.random.default_rng(SEED + 1).gamma(sh, 1.0, 2_000_000))
        return rng.gamma(sh, 1.0, (n_run, k)) / base_med * meds[None, :]
    z = np.sqrt(rho) * rng.standard_normal((n_run, 1)) + np.sqrt(1 - rho) * rng.standard_normal((n_run, k))
    return meds[None, :] * np.exp(sigma * z)


def merge_stats(x, plan):
    fin = x.max(1)
    late = np.clip(fin - plan, 0, None)
    return {"plan": round(float(plan), 2), "p_on_time": round(float((fin <= plan).mean()), 4),
            "mean_finish": round(float(fin.mean()), 2), "median_finish": round(float(np.median(fin)), 2),
            "p80_finish": round(float(np.quantile(fin, .8)), 2),
            "mean_late_days": round(float(late.mean()), 2),
            "mean_finish_minus_plan": round(float(fin.mean() - plan), 2)}


def main():
    t0 = time.time()
    p80_plan = MED * math.exp(SIGMA * Z80)
    rows = []
    for sg in [0.25, 0.4, 0.6]:
        for k in KS:
            x = draw(np.random.default_rng(SEED * 100 + k + int(sg * 100)), [MED] * k, sg, N_RUN)
            for name, plan in [("median", MED), ("p80", MED * math.exp(sg * Z80))]:
                r = merge_stats(x, plan)
                r["theory_p_on_time"] = round(0.5 ** k if name == "median" else 0.8 ** k, 4)
                rows.append({"sigma": sg, "k": k, "plan_rule": name, **r})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "by_k_sigma.csv", index=False)

    # 基本：4本・sigma=0.4、1回分のデータ
    x4 = draw(np.random.default_rng(SEED * 100 + 4 + int(SIGMA * 100)), [MED] * 4, SIGMA, N_RUN)  # 本数×ばらつきの表の4本と同じ乱数
    d = pd.DataFrame(np.round(x4[:1000], 2), columns=["b1", "b2", "b3", "b4"])
    d.insert(0, "run", np.arange(1, 1001))
    d["merge_day"] = d[["b1", "b2", "b3", "b4"]].max(1)
    d.to_csv(DATA / "runs_4branches.csv", index=False)
    base4 = merge_stats(x4, MED)
    base4["which_branch_last_share"] = [round(float(v), 4) for v in np.bincount(x4.argmax(1), minlength=4) / N_RUN]
    # 合流しなければ（1本だけ）と比べた、合流の日の伸び（中央値・平均）
    single = merge_stats(x4[:, :1], MED)

    # 確かめ：置き方を変える（4本・計画は中央値20日）
    cases = [("基本（4本・独立・どれも中央値20日）", dict()),
             ("共通の振れ rho=0.3", dict(rho=0.3)), ("共通の振れ rho=0.6", dict(rho=0.6)), ("共通の振れ rho=0.9", dict(rho=0.9)),
             ("ほかの3本は1割短い（中央値18日）", dict(meds=[20, 18, 18, 18])),
             ("ほかの3本は2割短い（中央値16日）", dict(meds=[20, 16, 16, 16])),
             ("ほかの3本は3割短い（中央値14日）", dict(meds=[20, 14, 14, 14])),
             ("分布をガンマに（ばらつきは同じ）", dict(shape="gamma")),
             ("ばらつき sigma=0.25", dict(sigma=0.25)), ("ばらつき sigma=0.6", dict(sigma=0.6))]
    rob = []
    for i, (name, c) in enumerate(cases):
        xx = x4 if i == 0 else draw(np.random.default_rng(SEED * 10 + i), c.get("meds", [MED] * 4), c.get("sigma", SIGMA), N_RUN,
                  c.get("rho", 0.0), c.get("shape", "lognormal"))
        rob.append({"case": name, **merge_stats(xx, MED)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_4branches.csv", index=False)

    g = grid[(grid.sigma == SIGMA)]
    out = {"setting": {"median_days": MED, "sigma": SIGMA, "p80_plan_days": round(p80_plan, 2)},
           "base_4branches_plan_median": base4, "single_branch_plan_median": single,
           "by_k_sigma0_4": g.to_dict("records"),
           "k_where_p_on_time_below_half_p80plan": int(g[(g.plan_rule == "p80") & (g.p_on_time < 0.5)].k.min()),
           "robustness_4branches": rob.to_dict("records"),
           "range_p_on_time_robustness": [float(rob.p_on_time.min()), float(rob.p_on_time.max())],
           "range_mean_late_robustness": [float(rob.mean_late_days.min()), float(rob.mean_late_days.max())]}
    json.dump(out, open(RES / "a851_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：本数と、計画の日に合流できる確率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for rule, c, lab in [("median", BLUE, "1本ごとに半々の日数（20日）で計画"), ("p80", ORANGE, f"1本ごとに8割の日数（{p80_plan:.1f}日）で計画")]:
        gg = g[g.plan_rule == rule]
        ax.plot(gg.k, gg.p_on_time * 100, "o-", color=c, label=lab)
        for k_, v in zip(gg.k, gg.p_on_time * 100):
            if k_ in ((1, 4) if rule == "median" else (1, 4, 16)):
                ax.text(k_, v + 3, f"{v:.0f}%" if v >= 1 else f"{v:.2f}%", ha="center", fontsize=9, color=c)
    ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels([str(k) for k in KS])
    ax.set_xlabel("同時に進める作業の本数（対数の目盛り）"); ax.set_ylabel("計画の日までに全部終わる確率（%）")
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9)
    ax.set_title("1本ごとの見積もりが正しくても、本数が増えると合流は遅れる")
    save(fig, "a851_p_on_time.png", SRC)

    # 図2：本数と、合流の日の平均（計画20日からの遅れ）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for sg, c in [(0.25, LIGHT), (0.4, BLUE), (0.6, ORANGE)]:
        gg = grid[(grid.sigma == sg) & (grid.plan_rule == "median")]
        ax.plot(gg.k, gg.mean_finish_minus_plan, "o-", color=c, label=f"ばらつき sigma={sg}")
        ax.text(16.8, gg.mean_finish_minus_plan.iloc[-1], f"+{gg.mean_finish_minus_plan.iloc[-1]:.1f}日", va="center", fontsize=9, color=c)
    ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels([str(k) for k in KS]); ax.set_xlim(0.9, 22)
    ax.axhline(0, color=GRAY, lw=1, ls=":")
    ax.set_xlabel("同時に進める作業の本数（対数の目盛り）"); ax.set_ylabel("合流の日の平均 − 計画20日（日）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("合流の日の平均は、本数とばらつきで延びる（1本の半々の日数20日）")
    save(fig, "a851_delay.png", SRC)

    # 図3：確かめ（4本）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    lab = ["基本（独立）", "共通の振れ0.3", "共通の振れ0.6", "共通の振れ0.9", "ほかは1割短い", "ほかは2割短い", "ほかは3割短い",
           "ガンマ分布", "sigma=0.25", "sigma=0.6"]
    yy = np.arange(len(rob))[::-1]
    ax.barh(yy, rob.p_on_time * 100, color=[BLUE] + [LIGHT] * 3 + [GREEN] * 3 + [GRAY] * 3)
    for y, v, dd in zip(yy, rob.p_on_time * 100, rob.mean_finish_minus_plan):
        ax.text(v + 1, y, f"{v:.0f}%（合流の日の平均 +{dd:.1f}日）", va="center", fontsize=8.5,
                bbox=dict(facecolor="white", edgecolor="none", pad=1))
    ax.axvline(50, color=GRAY, lw=1, ls=":"); ax.text(50.5, len(rob) - 0.4, "1本だけなら50%", color=GRAY, fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels(lab); ax.set_xlim(0, 65)
    ax.set_xlabel("4本が計画の20日までに全部終わる確率（%）")
    ax.set_title("一緒に延びる・ほかの本に余裕があると、合流の遅れは小さくなる")
    save(fig, "a851_robust.png", SRC)
    print(json.dumps({k: out[k] for k in ["base_4branches_plan_median", "single_branch_plan_median", "k_where_p_on_time_below_half_p80plan"]}, ensure_ascii=False, indent=1))
    print(g.to_string()); print(rob.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
