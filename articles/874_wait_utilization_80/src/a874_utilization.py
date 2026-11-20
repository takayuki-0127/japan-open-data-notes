"""874 利用が8割を超えると、待ち時間はなぜ急に伸びるのか？（架空のデータ）

架空の窓口（レジや受付）。客はでたらめな間隔（ポアソン過程）で来て、来た順に並ぶ。
1人の処理時間の平均は2分。「利用率」は、窓口が人を処理している時間の割合（来る人数×処理時間÷窓口の数）。
利用率を0.3〜0.97に変えて、平均の待ち時間を数える。ずっと開いている窓口（長く流して平均）と、
1日600分で毎朝空から始まる窓口の両方を数え、式（待ち行列の理論の値）とも比べる。
"""
import json, heapq, math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 874
SRC = "架空の窓口（作成者が乱数で作成、seed 874）"
S = 2.0                          # 平均の処理時間（分）
RHOS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97]
N_CUST, WARM, REPS = 200_000, 20_000, 5
T_OPEN, N_DAYS = 600.0, 400


def svc(rng, n, kind):
    if kind == "exp":
        return rng.exponential(S, n)
    if kind == "const":
        return np.full(n, S)
    if kind == "lognorm2":
        s2 = np.log(1 + 2.0 ** 2)
        return rng.lognormal(np.log(S) - s2 / 2, np.sqrt(s2), n)


def waits(arr, sv, c):
    n = len(arr); w = [0.0] * n
    if c == 1:
        free = 0.0
        for i in range(n):
            a = arr[i]; st = a if a > free else free
            w[i] = st - a; free = st + sv[i]
        return np.array(w)
    h = [0.0] * c
    for i in range(n):
        a = arr[i]; f = heapq.heappop(h); st = a if a > f else f
        w[i] = st - a; heapq.heappush(h, st + sv[i])
    return np.array(w)


def erlang_c_wq(rho, c, s=S):
    a = rho * c
    top = a ** c / math.factorial(c) * c / (c - a)
    pw = top / (sum(a ** k / math.factorial(k) for k in range(c)) + top)
    return pw * s / (c - a)


def kingman_factor(kind):
    cv2 = {"exp": 1.0, "const": 0.0, "lognorm2": 4.0}[kind]
    return (1 + cv2) / 2


def steady(rng, rho, c=1, kind="exp", n=N_CUST):
    lam = rho * c / S
    arr = np.cumsum(rng.exponential(1 / lam, n + WARM))
    w = waits(arr.tolist(), svc(rng, n + WARM, kind).tolist(), c)
    return float(w[WARM:].mean())


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    # 1) ずっと開いている窓口：窓口1・3・10、処理時間の形3通り（窓口1のみ）
    cases = [(1, "exp", RHOS), (1, "const", RHOS), (1, "lognorm2", RHOS),
             (3, "exp", [0.5, 0.7, 0.8, 0.85, 0.9, 0.95]), (10, "exp", [0.5, 0.7, 0.8, 0.85, 0.9, 0.95])]
    for c, kind, rs in cases:
        for rho in rs:
            vals = [steady(rng, rho, c, kind, N_CUST if c == 1 else N_CUST // 2) for _ in range(REPS)]
            if c == 1:
                theory = rho / (1 - rho) * S * kingman_factor(kind)   # 窓口1つ：ポラチェック＝ヒンチンの式
            else:
                theory = erlang_c_wq(rho, c)                            # 窓口c：アーランのC式（処理時間が指数分布）
            rows.append({"registers": c, "service": kind, "rho": rho, "sim_mean": round(float(np.mean(vals)), 3),
                         "sim_min": round(float(min(vals)), 3), "sim_max": round(float(max(vals)), 3),
                         "theory": round(theory, 3), "theory_per_service": round(theory / S, 3)})
    st = pd.DataFrame(rows)
    st.to_csv(RES / "steady_state.csv", index=False)

    # 2) 1日600分・毎朝空から（窓口1・指数）
    day_rows, traces = [], {}
    for rho in [0.5, 0.7, 0.8, 0.9, 0.95, 1.0, 1.1]:
        lam = rho / S
        dm, ends = [], []
        for d in range(N_DAYS):
            k = int(lam * T_OPEN * 1.5 + 50)
            a = np.cumsum(rng.exponential(1 / lam, k)); a = a[a <= T_OPEN]
            w = waits(a.tolist(), svc(rng, len(a), "exp").tolist(), 1)
            dm.append(w.mean() if len(w) else 0.0)
        dm = np.array(dm)
        day_rows.append({"rho": rho, "mean_of_day_means": round(float(dm.mean()), 3),
                         "day_p10": round(float(np.quantile(dm, .1)), 3), "day_p90": round(float(np.quantile(dm, .9)), 3),
                         "worst_day": round(float(dm.max()), 3)})
    # ある1日（同じ乱数の並びで、客の来る多さだけを変える）
    tr_rng = np.random.default_rng(SEED + 1)
    e = np.cumsum(tr_rng.exponential(1.0, 2000)); sv1 = svc(tr_rng, 2000, "exp")
    for rho in (0.5, 0.8, 0.9):
        a = e / (rho / S); m = a <= T_OPEN
        traces[rho] = pd.DataFrame({"rho": rho, "arrival": a[m], "wait": waits(a[m].tolist(), sv1[m].tolist(), 1)})
    dd = pd.DataFrame(day_rows)
    dd.to_csv(RES / "one_day.csv", index=False)
    tr = pd.concat(traces.values(), ignore_index=True)
    tr.to_csv(DATA / "one_day_trace.csv", index=False, float_format="%.3f")

    # 3) 客が1割増えたら（式の値、窓口1・指数）
    plus10 = []
    for rho in [0.5, 0.6, 0.7, 0.8, 0.85]:
        w0 = rho / (1 - rho) * S; r1 = rho * 1.1; w1 = r1 / (1 - r1) * S
        plus10.append({"rho_from": rho, "rho_to": round(r1, 3), "wait_from": round(w0, 2), "wait_to": round(w1, 2),
                       "increase_min": round(w1 - w0, 2), "ratio": round(w1 / w0, 2)})
    pd.DataFrame(plus10).to_csv(RES / "plus10pct.csv", index=False)

    base = st[(st.registers == 1) & (st.service == "exp")].set_index("rho")
    def g(df, r, col="sim_mean"):
        return float(df.loc[r, col])
    out = {"service_mean_min": S, "customers_per_rep": N_CUST, "reps": REPS,
           "base_sim": base[["sim_mean", "sim_min", "sim_max", "theory"]].reset_index().to_dict("records"),
           "max_abs_gap_sim_vs_theory_rho_le_0_9": round(float((base.sim_mean - base.theory)[base.index <= 0.9].abs().max()), 3),
           "slope_formula_per_service": {str(r): round(1 / (1 - r) ** 2, 2) for r in [0.5, 0.8, 0.9]},
           "plus10pct": plus10, "one_day": day_rows,
           "trace_day_mean": {str(r): round(float(t.wait.mean()), 2) for r, t in traces.items()},
           "trace_day_max": {str(r): round(float(t.wait.max()), 2) for r, t in traces.items()},
           "registers_at_0_9": {str(c): float(st[(st.registers == c) & (st.service == "exp") & (st.rho == 0.9)].sim_mean.iloc[0])
                                for c in [1, 3, 10]},
           "registers_at_0_8": {str(c): float(st[(st.registers == c) & (st.service == "exp") & (st.rho == 0.8)].sim_mean.iloc[0])
                                for c in [1, 3, 10]},
           "service_at_0_9": {k: float(st[(st.registers == 1) & (st.service == k) & (st.rho == 0.9)].sim_mean.iloc[0])
                              for k in ["const", "exp", "lognorm2"]}}
    json.dump(out, open(RES / "a874_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：利用率と待ち時間（窓口1）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    xs = np.linspace(0.3, 0.97, 200)
    ax.plot(xs * 100, xs / (1 - xs) * S, color=GRAY, lw=1.2, label="式の値（ρ÷(1−ρ)×処理時間）")
    ax.errorbar(base.index * 100, base.sim_mean, yerr=[base.sim_mean - base.sim_min, base.sim_max - base.sim_mean],
                fmt="o", color=BLUE, ms=5, capsize=3, label="乱数で数えた値（5回の平均と幅）")
    for r in [0.5, 0.8, 0.9]:
        v = g(base, r); ax.annotate(f"{r*100:.0f}%：{v:.1f}分", (r * 100, v), xytext=(-70, 12), textcoords="offset points",
                                    fontsize=9, color=ORANGE, arrowprops=dict(arrowstyle="-", color=ORANGE, lw=.8))
    ax.set_xlabel("利用率（窓口が人を処理している時間の割合、%）"); ax.set_ylabel("平均の待ち時間（分）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("利用率が上がるほど、待ち時間は加速して伸びる（窓口1つ・処理2分）")
    save(fig, "a874_curve.png", SRC)

    # 図2：窓口の数と処理時間のばらつき（処理時間を1とした倍率）
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 3.9), sharey=True)
    for c, colr in [(1, BLUE), (3, GREEN), (10, ORANGE)]:
        d = st[(st.registers == c) & (st.service == "exp")]
        axs[0].plot(d.rho * 100, d.sim_mean / S, marker="o", color=colr, label=f"窓口{c}つ（1つの列）")
    axs[0].set_title("窓口の数（1つの列に並ぶ）", fontsize=11)
    for kind, lab, colr in [("const", "毎回同じ", GREEN), ("exp", "指数分布（基本）", BLUE), ("lognorm2", "ばらつき大", ORANGE)]:
        d = st[(st.registers == 1) & (st.service == kind)]
        axs[1].plot(d.rho * 100, d.sim_mean / S, marker="o", color=colr, label=f"処理時間：{lab}")
    axs[1].set_title("処理時間のばらつき（窓口1つ）", fontsize=11)
    for a in axs:
        a.set_xlabel("利用率（%）"); a.legend(frameon=False, fontsize=8.5); a.set_xlim(28, 99)
    axs[0].set_ylabel("平均の待ち時間（処理時間の何倍か）"); axs[0].set_yscale("log")
    fig.suptitle("窓口が多いほど伸び始めが右へ、処理時間がばらつくほど全体が上へずれる（縦は対数の目盛り）", fontsize=12, y=1.04)
    save(fig, "a874_variants.png", SRC)

    # 図3：1日の待ち時間の動き
    fig, axs = plt.subplots(3, 1, figsize=(7.2, 6.0), sharex=True, sharey=True)
    for a, r in zip(axs, [0.5, 0.8, 0.9]):
        t = traces[r]
        a.fill_between(t.arrival / 60 + 10, t.wait, color=LIGHT, step="post")
        a.plot(t.arrival / 60 + 10, t.wait, color=BLUE, lw=.8, drawstyle="steps-post")
        a.set_title(f"利用率{r*100:.0f}%（この日の平均 {t.wait.mean():.1f}分）", fontsize=10, loc="left")
    fig.supylabel("来た客の待ち時間（分）", fontsize=11); axs[2].set_xlabel("来た時刻（時）")
    fig.suptitle("同じ客の並びでも、来る人が多いと一度できた列が消えにくい（ある1日）", fontsize=12)
    fig.tight_layout()
    save(fig, "a874_trace.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
