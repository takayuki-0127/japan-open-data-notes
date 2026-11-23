"""1019 予約を多めに取ると、断る人は何%出るのか？（架空のデータ）

架空の料理教室（1回の定員12人）。毎回、定員より k 人多く予約を受け（k=0〜4、予約はいつも埋まると置く）、
予約した人は当日、作成者が置いた確率で来ない。来た人が定員を超えた分を「断る人」とし、
「断る人が出た回の割合」「予約した人のうち断った人の割合」「来た人のうち断った人の割合」の3つの物差しで数える。
来ない率が回ごとに振れる場合と、2人連れの予約（2人そろって来る・来ない）がある場合も数える。
助言ではなく、数え方を比べるためのもの。
"""
import json
import time
from math import comb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1019
SRC = "架空の料理教室の予約（作成者が乱数で作成、seed 1019）"
CAP = 12
N_SIM = 200000


def exact(cap, k, q):
    """来ない率 q が毎回同じで、1人ずつ別々に来る・来ないが決まるとき（二項分布の式）"""
    n = cap + k
    pm = [comb(n, a) * (1 - q) ** a * q ** (n - a) for a in range(n + 1)]
    over = [max(a - cap, 0) for a in range(n + 1)]
    p_any = sum(p for p, o in zip(pm, over) if o > 0)
    e_turn = sum(p * o for p, o in zip(pm, over))
    e_arr = n * (1 - q)
    e_empty = sum(p * max(cap - a, 0) for a, p in enumerate(pm))
    return {"p_session": p_any, "per_booked": e_turn / n, "per_arrived": e_turn / e_arr,
            "turned_mean": e_turn, "empty_mean": e_empty}


def simulate(rng, cap, k, q, sd, pair_share, n_sim=N_SIM, keep=False):
    n = cap + k
    n_pair = int(round(n * pair_share / 2))
    n_single = n - 2 * n_pair
    if sd > 0:
        ab = q * (1 - q) / sd ** 2 - 1
        qq = rng.beta(q * ab, (1 - q) * ab, n_sim)
    else:
        qq = np.full(n_sim, q)
    arr = rng.binomial(n_single, 1 - qq) + 2 * rng.binomial(n_pair, 1 - qq)
    turned = np.maximum(arr - cap, 0)
    empty = np.maximum(cap - arr, 0)
    r = {"p_session": float((turned > 0).mean()), "per_booked": float(turned.sum() / (n * n_sim)),
         "per_arrived": float(turned.sum() / arr.sum()), "turned_mean": float(turned.mean()),
         "empty_mean": float(empty.mean()), "turned_mean_when_any": float(turned[turned > 0].mean()) if (turned > 0).any() else 0.0}
    if keep:
        return r, pd.DataFrame({"session": np.arange(1, n_sim + 1), "noshow_rate": qq.round(4), "booked": n,
                                "arrived": arr, "turned_away": turned, "empty_seats": empty})
    return r


def pct(x, d=2):
    return round(float(x) * 100, d)


def fmt(r):
    return {"p_session": pct(r["p_session"]), "per_booked": pct(r["per_booked"], 3), "per_arrived": pct(r["per_arrived"], 3),
            "turned_mean": round(r["turned_mean"], 4), "empty_mean": round(r["empty_mean"], 3),
            **({"turned_mean_when_any": round(r["turned_mean_when_any"], 3)} if "turned_mean_when_any" in r else {})}


def main():
    t0 = time.time()
    res = {"setting": {"capacity": CAP, "noshow": 0.10, "n_sim": N_SIM}}
    # 1) 基本：来ない率10%、毎回同じ、1人ずつ。k=0〜4（式と乱数）
    rows = []
    for k in range(5):
        e = fmt(exact(CAP, k, 0.10))
        s = fmt(simulate(np.random.default_rng(SEED * 10 + k), CAP, k, 0.10, 0.0, 0.0))
        rows.append({"extra": k, **{f"formula_{a}": b for a, b in e.items()}, **{f"sim_{a}": b for a, b in s.items()}})
    base = pd.DataFrame(rows)
    base.to_csv(RES / "base_by_extra.csv", index=False)
    res["base"] = base.set_index("extra").to_dict(orient="index")
    res["max_abs_diff_sim_vs_formula_p_session_pt"] = round(float((base.sim_p_session - base.formula_p_session).abs().max()), 2)

    # 2) 来ない率が回ごとに振れる・2人連れがある（k=2）
    cases = [("毎回同じ・1人ずつ（基本）", 0.0, 0.0), ("回ごとに振れる（標準偏差5ポイント）", 0.05, 0.0),
             ("回ごとに振れる（標準偏差8ポイント）", 0.08, 0.0), ("2人連れが半分", 0.0, 0.5),
             ("振れ5ポイント＋2人連れが半分", 0.05, 0.5)]
    crow = []
    for i, (name, sd, ps) in enumerate(cases):
        for k in range(5):
            r = fmt(simulate(np.random.default_rng(SEED * 100 + i * 10 + k), CAP, k, 0.10, sd, ps))
            crow.append({"case": name, "noshow_sd": sd, "pair_share": ps, "extra": k, **r})
    cdf = pd.DataFrame(crow)
    cdf.to_csv(RES / "cases_by_extra.csv", index=False)
    res["cases_k2"] = {r["case"]: {c: r[c] for c in ["p_session", "per_booked", "per_arrived", "turned_mean", "empty_mean", "turned_mean_when_any"]}
                       for r in cdf[cdf.extra == 2].to_dict(orient="records")}

    # 1回分のデータ（基本・k=2、1,000回）
    _, one = simulate(np.random.default_rng(SEED), CAP, 2, 0.10, 0.0, 0.0, n_sim=1000, keep=True)
    one.to_csv(DATA / "sessions_k2.csv", index=False)
    res["one_run_k2_1000"] = {"sessions_with_turned_away": int((one.turned_away > 0).sum()),
                              "turned_away_total": int(one.turned_away.sum()), "booked_total": int(one.booked.sum())}

    # 3) 確かめ：来ない率×振れ×2人連れ×定員（k=2、54通り）
    grid = []
    j = 0
    for cap in [8, 12, 30]:
        for q in [0.05, 0.10, 0.15]:
            for sd in [0.0, 0.05, 0.08]:
                for ps in [0.0, 0.5]:
                    sdx = min(sd, 0.9 * np.sqrt(q * (1 - q)))
                    r = fmt(simulate(np.random.default_rng(SEED * 1000 + j), cap, 2, q, sdx, ps, n_sim=100000)); j += 1
                    grid.append({"capacity": cap, "noshow": q, "noshow_sd": sdx, "pair_share": ps, **r,
                                 "session_over_booked_ratio": round(r["p_session"] / r["per_booked"], 1) if r["per_booked"] > 0 else None})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "sensitivity_grid.csv", index=False)
    g12 = grid[grid.capacity == 12]
    res["grid_range_k2"] = {
        "p_session": [float(grid.p_session.min()), float(grid.p_session.max())],
        "per_booked": [float(grid.per_booked.min()), float(grid.per_booked.max())],
        "p_session_cap12": [float(g12.p_session.min()), float(g12.p_session.max())],
        "per_booked_cap12": [float(g12.per_booked.min()), float(g12.per_booked.max())],
        "p_session_q10_cap12": [float(g12[g12.noshow == 0.10].p_session.min()), float(g12[g12.noshow == 0.10].p_session.max())],
        "per_booked_q10_cap12": [float(g12[g12.noshow == 0.10].per_booked.min()), float(g12[g12.noshow == 0.10].per_booked.max())],
        "p_session_always_above_per_booked": bool((grid.p_session > grid.per_booked).all()),
        "ratio_session_over_booked": [float(grid.session_over_booked_ratio.min()), float(grid.session_over_booked_ratio.max())],
    }
    with open(RES / "a1019_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)

    # 図1：多めに取る人数ごとの3つの物差し（基本、式の値）
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    x = np.arange(5); w = 0.27
    for i, (col, lab, c) in enumerate([("formula_p_session", "断る人が出た回の割合", ORANGE),
                                        ("formula_per_booked", "予約した人のうち断った人", BLUE),
                                        ("formula_per_arrived", "来た人のうち断った人", GREEN)]):
        v = base[col].values
        ax.bar(x + (i - 1) * w, v, w, color=c, label=lab)
        for xi, vi in zip(x, v):
            if vi > 0:
                ax.text(xi + (i - 1) * w, vi + 0.8, f"{vi:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"定員＋{k}人" for k in range(5)])
    ax.set_xlabel("受けた予約（定員12人）"); ax.set_ylabel("%")
    ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, base.formula_p_session.max() * 1.15)
    ax.set_title("同じ「多めの予約」でも、何で割るかで「断る%」は大きく違う（来ない率10%）")
    save(fig, "a1019_measures.png", SRC)

    # 図2：k=2 で、来ない率の振れと2人連れの有無
    sub = cdf[cdf.extra == 2].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    y = np.arange(len(sub))
    ax.barh(y, sub.p_session, color=ORANGE, label="断る人が出た回の割合")
    ax.barh(y, sub.per_booked, color=BLUE, label="予約した人のうち断った人", height=0.4)
    for yi, a, b in zip(y, sub.p_session, sub.per_booked):
        ax.text(a + 0.5, yi, f"{a:.1f}%（予約した人の{b:.2f}%）", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(sub.case, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, sub.p_session.max() * 1.55); ax.set_xlabel("%（定員12人に14人の予約、来ない率の平均10%）")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    ax.set_title("来ない率の振れ・2人連れで、断った人の割合は増えた（定員＋2人）")
    save(fig, "a1019_cases.png", SRC, y=-0.1)

    # 図3：54通り（k=2）
    fig, ax = plt.subplots(figsize=(8.4, 4.3))
    for cap, c, mk in [(8, GREEN, "s"), (12, BLUE, "o"), (30, ORANGE, "^")]:
        g = grid[grid.capacity == cap]
        ax.scatter(g.per_booked, g.p_session, color=c, marker=mk, s=30, label=f"定員{cap}人（予約は定員＋2人）")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([0.1, 0.3, 1, 3, 10, 20]); ax.set_xticklabels(["0.1", "0.3", "1", "3", "10", "20"])
    ax.set_yticks([3, 10, 30, 100]); ax.set_yticklabels(["3", "10", "30", "100"]); ax.minorticks_off()
    ax.set_xlabel("予約した人のうち断った人（%、対数の目盛り）"); ax.set_ylabel("断る人が出た回の割合（%、対数の目盛り）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("置き方を変えた54通り：断る回の割合は、断った人の割合よりいつも大きい")
    save(fig, "a1019_grid.png", SRC)
    print(json.dumps(res, ensure_ascii=False, indent=1)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
