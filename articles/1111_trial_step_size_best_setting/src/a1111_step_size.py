"""1111 条件の刻み（5度ごと・10度ごと）で、良い条件の見つかり方はどう変わるのか？（架空のデータ）

架空の塗装工房が、金属の板に塗った塗料を窯で焼き固める温度（150〜210度）を決める。
温度ごとの「本当のつや」（機械で測るつやの値、高いほど良い）を作成者が山の形で置き、山の頂上の温度は工房ごとに 160〜200度の一様。
試し焼きの板は全部で60枚。温度の刻み（5・10・15・20・30度）を変えると、試す温度の数と1つの温度あたりの枚数が変わる。
いちばんつやの良かった温度を選び、①選んだ温度の本当のつやが頂上からどれだけ足りないか、②選んだ温度が頂上から何度ずれたか、
③選んだ温度の見かけのつやが本当よりどれだけ高く出たか、を数える。
板を半分ずつ使う二段の刻み（15度ごとに5温度→良かった温度の前後を5度ごとに5温度）も比べる。
"""
import json
import time
import itertools
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1111
SRC = "架空の塗装工房の試し焼き（作成者が置いたつやの山からの乱数、seed 1111）"
T_LO, T_HI = 150, 210
PEAK_LO, PEAK_HI = 160, 200
TOP = 90.0
STEPS = [5, 10, 15, 20, 30]
BASE = {"a": 0.02, "sigma": 3.0, "budget": 60, "asym": 2.0, "sat": 20.0}
SHAPES = [("左右同じ放物線", 1.0, None), ("基本（焼きすぎ側が2倍急・下がり方が20で頭打ち）", 2.0, 20.0),
          ("焼きすぎ側が4倍急・下がり方が10で頭打ち", 4.0, 10.0)]
REPS = 4000
GRID_A = [0.005, 0.02, 0.08]
GRID_SIGMA = [1.5, 3.0, 6.0]
GRID_BUDGET = [30, 60, 120]
GRID_REPS = 1500


def r(x, d=2):
    return round(float(x), d)


def true_gloss(T, peak, a, asym, sat):
    """頂上から d 度ずれると、a×d²（焼きすぎ側は asym 倍）下がる。sat があれば下がり方は sat で頭打ち"""
    d = T - peak
    q = a * np.where(d > 0, asym, 1.0) * d ** 2
    return TOP - (q if sat is None else sat * (1 - np.exp(-q / sat)))


def levels(step):
    return np.arange(T_LO, T_HI + 0.001, step)


def alloc(L, budget, rng):
    """budget 枚を L 個の温度にできるだけ同じに分ける（余りはでたらめな温度に1枚ずつ）"""
    n = np.full(L, budget // L)
    n[rng.choice(L, budget % L, replace=False)] += 1
    return n


def finish(peak, pick, seen, a, asym, sat):
    tv = true_gloss(pick, peak, a, asym, sat)
    return {"peak": peak, "pick": pick, "loss": TOP - tv, "dist": np.abs(pick - peak), "overstate": seen - tv}


def simulate(rng, step, reps, a, sigma, budget, asym, sat, noise=True):
    """刻み step で一様に試し、いちばん良かった温度を選ぶ"""
    lv = levels(step); L = len(lv)
    peak = rng.uniform(PEAK_LO, PEAK_HI, reps)
    mu = true_gloss(lv[None, :], peak[:, None], a, asym, sat)
    n = np.array([alloc(L, budget, rng) for _ in range(reps)])
    means = mu + (rng.normal(0, 1, (reps, L)) * sigma / np.sqrt(n) if noise else 0.0)
    k = np.argmax(means, axis=1)
    rows = np.arange(reps)
    out = finish(peak, lv[k], means[rows, k], a, asym, sat)
    out["n_levels"] = L
    out["boards_per_level"] = f"{budget // L}" if budget % L == 0 else f"{budget // L}〜{budget // L + 1}"
    return out


def simulate_two_stage(rng, reps, a, sigma, budget, asym, sat):
    """二段：板の半分で15度ごと（5温度）→良かった温度の前後10度を5度ごと（5温度）に残り半分。二段目の中から選ぶ"""
    lv1 = levels(15)
    peak = rng.uniform(PEAK_LO, PEAK_HI, reps)
    n1 = budget // 2 // len(lv1)
    m1 = true_gloss(lv1[None, :], peak[:, None], a, asym, sat) + rng.normal(0, 1, (reps, len(lv1))) * sigma / np.sqrt(n1)
    c = lv1[np.argmax(m1, axis=1)]
    c = np.clip(c, T_LO + 10, T_HI - 10)                         # 範囲の端なら内側にずらす
    lv2 = c[:, None] + np.array([-10, -5, 0, 5, 10])[None, :]
    n2 = (budget - n1 * len(lv1)) // 5
    m2 = true_gloss(lv2, peak[:, None], a, asym, sat) + rng.normal(0, 1, lv2.shape) * sigma / np.sqrt(n2)
    k = np.argmax(m2, axis=1); rows = np.arange(reps)
    return finish(peak, lv2[rows, k], m2[rows, k], a, asym, sat)


def summarize(s):
    return {"loss": r(s["loss"].mean()), "loss_p90": r(np.percentile(s["loss"], 90)),
            "share_loss_over_1": r((s["loss"] > 1).mean() * 100, 2),
            "dist": r(s["dist"].mean()), "share_dist_within_2": r((s["dist"] <= 2).mean() * 100, 2),
            "overstate": r(s["overstate"].mean())}


def main():
    t0 = time.time()
    b = BASE
    P = (b["a"], b["sigma"], b["budget"], b["asym"], b["sat"])

    # 1) 例：頂上183度の工房を5度刻みと20度刻みで試す（data に置く）
    ex_rows = []
    rng = np.random.default_rng(SEED)
    ex_peak = 183.0
    example = {"peak": ex_peak}
    for step in [5, 20]:
        lv = levels(step); n = alloc(len(lv), b["budget"], rng)
        for T, nn in zip(lv, n):
            vals = true_gloss(T, ex_peak, b["a"], b["asym"], b["sat"]) + rng.normal(0, b["sigma"], nn)
            for j, v in enumerate(vals):
                ex_rows.append({"step": step, "temp": T, "board": j + 1, "gloss": round(float(v), 3)})
    ex = pd.DataFrame(ex_rows)
    ex.to_csv(DATA / "example_boards.csv", index=False)
    exm = ex.groupby(["step", "temp"]).gloss.agg(["mean", "size"]).reset_index()
    for step in [5, 20]:
        g = exm[exm.step == step].reset_index(drop=True)
        kk = int(g["mean"].idxmax())
        mn, mx = int(g["size"].min()), int(g["size"].max())
        example[f"step{step}"] = {"chosen": float(g.temp[kk]), "chosen_mean": r(g["mean"][kk], 2),
                                  "chosen_true": r(true_gloss(g.temp[kk], ex_peak, b["a"], b["asym"], b["sat"]), 2),
                                  "boards_per_level": f"{mn}" if mn == mx else f"{mn}〜{mx}"}

    # 2) 基本の置き方で刻みごと（各4,000回）。ぶれなし・山の形を変えたものも
    rows = []
    for si, step in enumerate(STEPS):
        s = simulate(np.random.default_rng(SEED * 10 + si), step, REPS, *P)
        s0 = simulate(np.random.default_rng(SEED * 20 + si), step, REPS, *P, noise=False)
        rec = {"step": step, "n_levels": s["n_levels"], "boards_per_level": s["boards_per_level"], **summarize(s),
               "noise_free_loss": r(s0["loss"].mean(), 4), "noise_free_dist": r(s0["dist"].mean())}
        for hi, (hname, asym, sat) in enumerate(SHAPES):
            if hi == 1:
                continue
            tag = "parab" if hi == 0 else "asym4"
            sh = simulate(np.random.default_rng(SEED * 30 + si * 3 + hi), step, REPS, b["a"], b["sigma"], b["budget"], asym, sat)
            s0h = simulate(np.random.default_rng(SEED * 40 + si * 3 + hi), step, REPS, b["a"], b["sigma"], b["budget"], asym, sat, noise=False)
            rec[f"{tag}_loss"] = r(sh["loss"].mean()); rec[f"{tag}_noise_free_loss"] = r(s0h["loss"].mean(), 4)
        rec["formula_parab_noise_free_loss"] = r(b["a"] * step ** 2 / 12, 4)
        rows.append(rec)
    bystep = pd.DataFrame(rows)
    two = simulate_two_stage(np.random.default_rng(SEED * 50), REPS, *P)
    two_sum = summarize(two)
    tworow = {"step": "二段（15度→5度）", "n_levels": 10, "boards_per_level": "6", **two_sum}
    pd.concat([bystep, pd.DataFrame([tworow])], ignore_index=True).to_csv(RES / "by_step.csv", index=False)

    # 3) 確かめ：山のとがり a × 1枚のぶれ σ × 全部の枚数（27通り、各1,500回）
    grid = []
    for gi, (a, sig, bud) in enumerate(itertools.product(GRID_A, GRID_SIGMA, GRID_BUDGET)):
        rec = {"a": a, "sigma": sig, "budget": bud}
        for si, step in enumerate(STEPS):
            s = simulate(np.random.default_rng(SEED * 1000 + gi * 10 + si), step, GRID_REPS, a, sig, bud, b["asym"], b["sat"])
            rec[f"loss_s{step}"] = r(s["loss"].mean()); rec[f"dist_s{step}"] = r(s["dist"].mean())
            rec[f"over_s{step}"] = r(s["overstate"].mean())
        t2 = simulate_two_stage(np.random.default_rng(SEED * 1000 + gi * 10 + 9), GRID_REPS, a, sig, bud, b["asym"], b["sat"])
        rec["loss_two"] = r(t2["loss"].mean()); rec["dist_two"] = r(t2["dist"].mean()); rec["over_two"] = r(t2["overstate"].mean())
        l = [rec[f"loss_s{st}"] for st in STEPS]
        rec["best_step"] = STEPS[int(np.argmin(l))]
        rec["loss_s5_over_best"] = r(l[0] / min(l))
        rec["loss_s30_over_best"] = r(l[-1] / min(l))
        rec["two_vs_best_uniform"] = r(rec["loss_two"] / min(l))
        rec["dist_s5_minus_s10"] = r(rec["dist_s5"] - rec["dist_s10"])
        grid.append(rec)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    out = {"base": BASE, "range": [T_LO, T_HI], "peak_range": [PEAK_LO, PEAK_HI], "top": TOP, "reps": REPS,
           "shapes": [{"name": n, "asym": a_, "sat": s_} for n, a_, s_ in SHAPES],
           "example": example,
           "by_step": bystep.to_dict(orient="records"),
           "two_stage": two_sum,
           "base_best_step": int(bystep.step[bystep.loss.idxmin()]),
           "drop_10deg_low_side_by_a": {str(a): r(TOP - true_gloss(-10.0, 0.0, a, b["asym"], b["sat"]), 2) for a in GRID_A},
           "drop_10deg_high_side_by_a": {str(a): r(TOP - true_gloss(10.0, 0.0, a, b["asym"], b["sat"]), 2) for a in GRID_A},
           "grid_best_step_counts": {str(k): int(v) for k, v in grid.best_step.value_counts().sort_index().items()},
           "grid_loss_s5_over_best_range": [r(grid.loss_s5_over_best.min()), r(grid.loss_s5_over_best.max())],
           "grid_loss_s30_over_best_range": [r(grid.loss_s30_over_best.min()), r(grid.loss_s30_over_best.max())],
           "grid_two_vs_best_uniform_range": [r(grid.two_vs_best_uniform.min()), r(grid.two_vs_best_uniform.max())],
           "grid_two_beats_best_uniform_count": int((grid.two_vs_best_uniform < 1).sum()),
           "grid_two_beats_s5_count": int((grid.loss_two < grid.loss_s5).sum()),
           "grid_dist_s5_ge_s10_count": int((grid.dist_s5_minus_s10 >= 0).sum()),
           "grid_over_s5_gt_s20_count": int((grid.over_s5 > grid.over_s20).sum()),
           "grid_over_s5_range": [r(grid.over_s5.min()), r(grid.over_s5.max())],
           "grid_over_s20_range": [r(grid.over_s20.min()), r(grid.over_s20.max())],
           "grid_count": len(grid)}
    json.dump(out, open(RES / "a1111_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の工房
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    Tg = np.linspace(T_LO, T_HI, 301)
    for ax, step in zip(axes, [5, 20]):
        g = exm[exm.step == step]
        e = ex[ex.step == step]
        ax.plot(Tg, true_gloss(Tg, ex_peak, b["a"], b["asym"], b["sat"]), color=GRAY, lw=1.5, label="本当のつや（作成者が置いた山）")
        ax.scatter(e.temp, e.gloss, color=LIGHT, s=10, label="板1枚ずつ")
        ax.plot(g.temp, g["mean"], "o", color=BLUE, ms=6, label="温度ごとの平均")
        c = example[f"step{step}"]["chosen"]
        ax.axvline(c, color=ORANGE, lw=1.5, ls="--", label="いちばん良かった温度")
        ax.axvline(ex_peak, color=INK, lw=0.8, ls=":", label="本当の頂上（183度）")
        ax.set_title(f"{step}度ごと（{len(g)}温度×{example[f'step{step}']['boards_per_level']}枚）", loc="left", fontsize=11)
        ax.set_xlabel("焼き付けの温度（度）")
    axes[0].set_ylabel("つや（機械で測った値）")
    axes[1].legend(frameon=False, fontsize=8, loc="lower center")
    fig.suptitle("例の工房：刻みが細かいと1温度あたりの枚数が減り、温度ごとの平均がぶれる", x=0.01, y=1.03, ha="left", fontsize=12)
    save(fig, "a1111_example.png", SRC)

    # 図2：刻みごとの3つの物差し
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))
    labels = [f"{s}度\n{n}温度" for s, n in zip(STEPS, bystep.n_levels)] + ["二段\n15→5度"]
    x = np.arange(len(labels))
    cols = [BLUE] * len(STEPS) + [GREEN]
    panels = [("loss", "①つやの不足（平均）", "noise_free_loss", "{:.2f}"),
              ("dist", "②頂上からのずれ（度、平均）", "noise_free_dist", "{:.2f}"),
              ("overstate", "③見かけのつや−本当のつや", None, "{:.2f}")]
    for ax, (col, title, nf, fmt) in zip(axes, panels):
        vals = list(bystep[col]) + [two_sum[col]]
        bars = ax.bar(x, vals, color=cols)
        refs = list(bystep[nf]) + [0] if nf else [0] * len(vals)
        if nf:
            ax.plot(x[:len(STEPS)], bystep[nf], "_", color=INK, ms=18, mew=2, label="板のぶれがないとき")
            ax.legend(frameon=False, fontsize=8.5, loc="upper left")
        for bb, v, rf in zip(bars, vals, refs):
            ax.text(bb.get_x() + bb.get_width() / 2, max(v, rf) + max(vals) * 0.02, fmt.format(v), ha="center", va="bottom", fontsize=8.5)
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5)
        ax.set_ylim(0, max(max(vals), max(refs)) * 1.25)
        ax.set_title(title, loc="left", fontsize=11)
    fig.suptitle("板60枚を刻みで分けたとき（4,000回の平均）：5度ごとにしても、頂上からのずれは10度ごとより縮まなかった", x=0.01, y=1.04, ha="left", fontsize=12)
    save(fig, "a1111_by_step.png", SRC)

    # 図3：確かめ（板60枚の9通り）
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for ax, a in zip(axes, GRID_A):
        g = grid[(grid.a == a) & (grid.budget == 60)]
        for sig, col in zip(GRID_SIGMA, [GREEN, BLUE, ORANGE]):
            gg = g[g.sigma == sig]
            ax.plot(STEPS, [gg[f"loss_s{s}"].iloc[0] for s in STEPS], marker="o", color=col, lw=1.3, label=f"一様な刻み　板のぶれ {sig}")
            ax.plot([37], [gg["loss_two"].iloc[0]], marker="*", color=col, ms=12, ls="none", label=f"二段（15→5度）　板のぶれ {sig}")
        ax.set_xticks(STEPS + [37]); ax.set_xticklabels([str(v) for v in STEPS] + ["二段"])
        ax.set_xlabel("刻み（度）"); ax.set_ylim(bottom=0)
        ax.set_title(f"山のとがり {a}（低い側に10度で−{TOP - true_gloss(-10.0, 0.0, a, b['asym'], b['sat']):.1f}）", loc="left", fontsize=10.5)
    axes[0].set_ylabel("つやの不足（平均）")
    axes[2].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    fig.suptitle("確かめ（板60枚）：不足のいちばん小さい刻みは、山のとがりと板のぶれで入れかわる（★は二段）", x=0.01, y=1.04, ha="left", fontsize=12)
    save(fig, "a1111_robust.png", SRC)

    print(json.dumps(example, ensure_ascii=False))
    pd.set_option("display.width", 250)
    print(bystep.to_string()); print(two_sum); print(grid.to_string())
    print({k: out[k] for k in out if k.startswith("grid_") or k.startswith("base_best")})
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
