"""850 「最もありそうな日数」で計画すると、間に合う確率は何%か？（架空のデータ）

架空のプロジェクト（作業10個を順に行う）。作業の実際の日数は右に長い対数正規分布（中央値 med・ばらつき sigma）。
担当者が答える「最もありそうな日数」は、この分布の山の位置（最頻値＝med×exp(-sigma²)）と置く。
最頻値・中央値・平均・三点見積もり・8割点で計画したとき、実際に間に合う確率を数える。
"""
import json
import math
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 850
SRC = "架空のプロジェクトの作業日数（作成者が乱数で作成、seed 850）"
rng = np.random.default_rng(SEED)
N_RUN = 200_000
SIGMA = 0.5
MED = rng.integers(2, 11, 10).astype(float)  # 作業10個の中央値（日）
Z80 = 0.8416212335729143


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def zq(p):
    """標準正規の p 点（二分法）"""
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if phi(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def task_points(med, sigma, lo_q=0.05, hi_q=0.95):
    """作業ごとの見積もりの値。最短・最長は、担当者が答える分布の lo_q 点・hi_q 点と置く"""
    mode = med * np.exp(-sigma ** 2)
    mean = med * np.exp(sigma ** 2 / 2)
    p80 = med * np.exp(sigma * Z80)
    a = med * np.exp(sigma * zq(lo_q))
    b = med * np.exp(sigma * zq(hi_q))
    pert = (a + 4 * mode + b) / 6
    pert_sd = (b - a) / 6
    return {"mode": mode, "median": med, "mean": mean, "p80": p80, "a": a, "b": b, "pert": pert, "pert_sd": pert_sd}


PLAN_NAMES = {"mode": "最もありそうな日数（最頻値）", "median": "半々で終わる日数（中央値）", "pert": "三点見積もり（最短＋4×最もありそう＋最長）÷6",
              "mean": "平均の日数", "pert80": "三点見積もり＋ばらつきで8割をねらう", "p80": "作業ごとの8割点"}


def draw(rng, med, sigma, n_run, rho=0.0, shape="lognormal"):
    k = len(med)
    if shape == "gamma":
        cv = np.sqrt(np.exp(sigma ** 2) - 1)
        sh = 1 / cv ** 2
        base_med = np.median(np.random.default_rng(SEED + 1).gamma(sh, 1.0, 2_000_000))
        return rng.gamma(sh, 1.0, (n_run, k)) / base_med * med[None, :]
    z = np.sqrt(rho) * rng.standard_normal((n_run, 1)) + np.sqrt(1 - rho) * rng.standard_normal((n_run, k))
    return med[None, :] * np.exp(sigma * z)


def evaluate(x, pts):
    """計画の日数と、実際の合計がそれ以内に収まる確率（作業1個目だけ・作業10個の合計）"""
    tot = x.sum(1)
    out = {}
    for key in ["mode", "median", "pert", "mean", "pert80", "p80"]:
        if key == "pert80":
            plan_all = pts["pert"].sum() + Z80 * np.sqrt((pts["pert_sd"] ** 2).sum())
            plan_one = pts["pert"][0] + Z80 * pts["pert_sd"][0]
        else:
            plan_all = pts[key].sum()
            plan_one = pts[key][0]
        out[key] = {"plan_one": round(float(plan_one), 2), "p_one": round(float((x[:, 0] <= plan_one).mean()), 4),
                    "plan_all": round(float(plan_all), 2), "p_all": round(float((tot <= plan_all).mean()), 4)}
    return out


def main():
    t0 = time.time()
    pts = task_points(MED, SIGMA)
    x = draw(rng, MED, SIGMA, N_RUN)
    base = evaluate(x, pts)
    theory = {"p_le_mode_one_task": round(phi(-SIGMA), 4), "mode_over_median": round(math.exp(-SIGMA ** 2), 4),
              "mean_over_mode": round(math.exp(1.5 * SIGMA ** 2), 4)}
    tot = x.sum(1)
    extra = {"total_mean": round(float(tot.mean()), 2), "total_median": round(float(np.median(tot)), 2),
             "total_p80": round(float(np.quantile(tot, .8)), 2),
             "mean_overrun_vs_mode_plan_pct": round(float((tot.mean() / pts["mode"].sum() - 1) * 100), 2),
             "p_each_task_le_mode": [round(float(v), 4) for v in (x <= pts["mode"][None, :]).mean(0)]}

    tasks = pd.DataFrame({"task_id": np.arange(1, 11), "median": MED, "most_likely": pts["mode"].round(2),
                          "mean": pts["mean"].round(2), "shortest_5pct": pts["a"].round(2), "longest_95pct": pts["b"].round(2),
                          "pert": pts["pert"].round(2), "p80": pts["p80"].round(2)})
    tasks.to_csv(DATA / "tasks.csv", index=False)
    runs = pd.DataFrame(np.round(x[:1000], 2), columns=[f"t{i}" for i in range(1, 11)])
    runs.insert(0, "run", np.arange(1, 1001))
    runs["total"] = runs[[f"t{i}" for i in range(1, 11)]].sum(1).round(2)
    runs.to_csv(DATA / "runs.csv", index=False)

    rows = []
    for k, v in base.items():
        rows.append({"plan": PLAN_NAMES[k], "key": k, **v})
    plans = pd.DataFrame(rows)
    plans.to_csv(RES / "plans_base.csv", index=False)

    # 確かめ：置き方を変える
    cases = [("基本（sigma=0.5・対数正規・作業どうし独立・最短最長は5%点と95%点）", dict()),
             ("ばらつき sigma=0.3", dict(sigma=0.3)), ("ばらつき sigma=0.8", dict(sigma=0.8)),
             ("分布をガンマに（ばらつきは同じ）", dict(shape="gamma")),
             ("共通の振れ rho=0.3", dict(rho=0.3)), ("共通の振れ rho=0.6", dict(rho=0.6)),
             ("最短・最長を広く答える（1%点と99%点）", dict(lo=0.01, hi=0.99)),
             ("最短・最長を狭く答える（10%点と90%点）", dict(lo=0.10, hi=0.90)),
             ("最短・最長をもっと狭く答える（20%点と80%点）", dict(lo=0.20, hi=0.80))]
    rob = []
    for i, (name, c) in enumerate(cases):
        sg = c.get("sigma", SIGMA)
        pp = task_points(MED, sg, c.get("lo", 0.05), c.get("hi", 0.95))
        xx = draw(np.random.default_rng(SEED * 10 + i), MED, sg, N_RUN, c.get("rho", 0.0), c.get("shape", "lognormal"))
        if c.get("shape") == "gamma":  # ガンマのときは、最頻値・平均もガンマのものに置き直す
            cv = np.sqrt(np.exp(sg ** 2) - 1); sh = 1 / cv ** 2
            base_med = np.median(np.random.default_rng(SEED + 1).gamma(sh, 1.0, 2_000_000))
            pp["mode"] = MED * (sh - 1) / base_med
            pp["mean"] = MED * sh / base_med
        ev = evaluate(xx, pp)
        rob.append({"case": name, **{f"{k}_p_one": v["p_one"] for k, v in ev.items()},
                    **{f"{k}_p_all": v["p_all"] for k, v in ev.items()}})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    med1 = 10.0
    p1 = task_points(np.array([med1]), SIGMA)
    one10 = {k: {"days": round(float(p1[k][0]), 2), "p_formula": round(phi(math.log(float(p1[k][0]) / med1) / SIGMA), 4)}
             for k in ["mode", "median", "mean", "p80"]}
    out = {"base": base, "theory": theory, "base_extra": extra, "one_task_median10_formula": one10,
           "range_mode_p_one": [float(rob.mode_p_one.min()), float(rob.mode_p_one.max())],
           "range_mode_p_all": [float(rob.mode_p_all.min()), float(rob.mode_p_all.max())],
           "range_pert80_p_all": [float(rob.pert80_p_all.min()), float(rob.pert80_p_all.max())],
           "range_pert_p_all": [float(rob.pert_p_all.min()), float(rob.pert_p_all.max())],
           "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a850_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：作業1個の日数の分布と、計画の線（中央値10日の作業で描く）
    xs = np.linspace(0.5, 35, 600)
    dens = np.exp(-(np.log(xs / med1)) ** 2 / (2 * SIGMA ** 2)) / (xs * SIGMA * np.sqrt(2 * np.pi))
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.fill_between(xs, dens, color=LIGHT, lw=0)
    lines = [("mode", "最もありそう", ORANGE), ("median", "半々", BLUE), ("mean", "平均", GRAY), ("p80", "8割", INK)]
    ymax = dens.max()
    for j, (k, lab, c) in enumerate(lines):
        v, p = one10[k]["days"], one10[k]["p_formula"]
        ax.axvline(v, color=c, lw=1.3, ls="--")
        ax.text(v + 0.3, ymax * (1.02 - 0.13 * j), f"{lab} {v:.1f}日\n間に合う {p*100:.0f}%", color=c, fontsize=9,
                bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xlabel("作業1個の実際の日数（半々で終わる日数を10日と置いた作業）"); ax.set_yticks([]); ax.set_xlim(0, 35)
    ax.set_ylim(0, ymax * 1.18)
    ax.set_title("山の位置（最もありそうな日数）で計画すると、間に合うのは3割")
    save(fig, "a850_one_task.png", SRC)

    # 図2：計画の決め方ごとの間に合う確率（作業1個・作業10個の合計）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    yy = np.arange(len(plans))[::-1]
    ax.barh(yy + 0.2, plans.p_one * 100, height=0.38, color=LIGHT, label="作業1個")
    ax.barh(yy - 0.2, plans.p_all * 100, height=0.38, color=BLUE, label="作業10個の合計")
    for y, a_, b_ in zip(yy, plans.p_one * 100, plans.p_all * 100):
        ax.text(a_ + 1, y + 0.2, f"{a_:.0f}%", va="center", fontsize=8.5)
        ax.text(b_ + 1, y - 0.2, f"{b_:.0f}%", va="center", fontsize=8.5)
    short = ["最もありそうな日数", "半々の日数", "三点見積もり", "平均の日数", "三点見積もり＋8割", "作業ごとの8割点"]
    ax.set_yticks(yy); ax.set_yticklabels(short); ax.set_xlim(0, 110)
    ax.set_xlabel("計画の日数以内に終わる確率（%）"); ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("作業10個の合計を「最もありそうな日数」の合計で計画すると、ほぼ間に合わない")
    save(fig, "a850_plans.png", SRC)

    # 図3：置き方を変えたとき
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    yy = np.arange(len(rob))[::-1]
    lab = ["基本", "sigma=0.3", "sigma=0.8", "ガンマ分布", "共通の振れ0.3", "共通の振れ0.6", "最短最長1〜99%点", "最短最長10〜90%点", "最短最長20〜80%点"]
    ax.barh(yy + 0.2, rob.mode_p_all * 100, height=0.38, color=ORANGE, label="最もありそうな日数の合計")
    ax.barh(yy - 0.2, rob.pert80_p_all * 100, height=0.38, color=BLUE, label="三点見積もり＋8割をねらう")
    for y, a_, b_ in zip(yy, rob.mode_p_all * 100, rob.pert80_p_all * 100):
        ax.text(a_ + 1, y + 0.2, f"{a_:.1f}%" if a_ < 1 else f"{a_:.0f}%", va="center", fontsize=8.5)
        ax.text(b_ + 1, y - 0.2, f"{b_:.0f}%", va="center", fontsize=8.5)
    ax.axvline(80, color=GRAY, lw=1, ls=":")
    ax.set_yticks(yy); ax.set_yticklabels(lab); ax.set_xlim(0, 110)
    ax.set_xlabel("作業10個の合計が計画以内に終わる確率（%）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("置き方を変えても、最もありそうな日数の合計はほぼ間に合わない")
    save(fig, "a850_robust.png", SRC)
    print(json.dumps({k: out[k] for k in ["base", "theory", "base_extra"]}, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
