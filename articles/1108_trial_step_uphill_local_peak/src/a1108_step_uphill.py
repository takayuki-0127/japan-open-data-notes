"""1108 良い方へ少しずつ条件を動かしていくと、いちばん良い所に着くのか？（架空のデータ）

架空の陶芸工房で、釉薬の焼き上がりの「色むらの少なさの点数」（高いほど良い）を、窯の温度と焼く時間の2つの条件で試す。
本当の点数の地形（2つの山：低い山と高い山）は作成者が置き、1つ焼くごとに作成者が置いたばらつきを足す。
今の条件から始め、上下左右の4つの隣を1つずつ焼いて、いちばん良く見えた隣が今より良く見えれば動く。
良く見える隣がなくなるか、焼ける数（120個）を使い切ったら止める。どこに着いたかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1108
SRC = "架空の陶芸工房の試し焼き（作成者が置いた点数の地形とばらつきからの乱数、seed 1108）"
NG = 21                        # 温度・時間それぞれ21段階（0〜20）
TEMP = 1180 + 6 * np.arange(NG)   # 1180〜1300℃（6℃きざみ）
HOURS = 4 + 0.4 * np.arange(NG)   # 4〜12時間（0.4時間きざみ）
BASE = {"noise": 2.0, "step": 1, "repeat": 1, "budget": 120, "low_peak": 22.0, "start": "fixed"}
START_FIXED = (3, 4)             # 今の条件（1198℃・5.6時間）
RUNS = 2000
REACH_TOL = 1.0                  # いちばん良い点数から1点以内に着いたら「着いた」


def r(x, d=4):
    return round(float(x), d)


def surface(low_peak=22.0, high_peak=30.0, low_center=(0.3, 0.35), high_center=(0.78, 0.72)):
    g = np.linspace(0, 1, NG)
    X, Y = np.meshgrid(g, g, indexing="ij")
    return (60 + low_peak * np.exp(-((X - low_center[0]) ** 2 + (Y - low_center[1]) ** 2) / (2 * 0.15 ** 2))
            + high_peak * np.exp(-((X - high_center[0]) ** 2 + (Y - high_center[1]) ** 2) / (2 * 0.1 ** 2)))


def climb(F, rng, runs, noise, step, repeat, budget, start="fixed", n_starts=1):
    """runs 回の登りをまとめて進める。n_starts>1 のときは、焼ける数を出発点の数で等分し、いちばん良く見えた着き先を選ぶ"""
    best_true = F.max()
    finals_true = np.full(runs, -np.inf)
    finals_seen = np.full(runs, -np.inf)
    final_pos = np.zeros((runs, 2), int)
    used_all = np.zeros(runs)
    per_budget = budget // n_starts
    for s in range(n_starts):
        if start == "fixed" and n_starts == 1:
            pos = np.tile(np.array(START_FIXED), (runs, 1))
        else:
            pos = rng.integers(0, NG, (runs, 2))
        sd = noise / np.sqrt(repeat)
        cur = F[pos[:, 0], pos[:, 1]] + rng.normal(0, sd, runs)
        used = np.full(runs, repeat, float)
        active = np.ones(runs, bool)
        moves = np.array([[step, 0], [-step, 0], [0, step], [0, -step]])
        while active.any():
            idx = np.where(active)[0]
            cand = pos[idx, None, :] + moves[None, :, :]
            inb = (cand >= 0).all(2) & (cand < NG).all(2)
            cc = np.clip(cand, 0, NG - 1)
            meas = F[cc[..., 0], cc[..., 1]] + rng.normal(0, sd, inb.shape)
            meas[~inb] = -np.inf
            cost = inb.sum(1) * repeat
            over = used[idx] + cost > per_budget
            used[idx] += np.where(over, 0, cost)
            k = meas.argmax(1)
            bm = meas[np.arange(len(idx)), k]
            go = (bm > cur[idx]) & ~over
            newp = cand[np.arange(len(idx)), k]
            pos[idx[go]] = newp[go]
            cur[idx[go]] = bm[go]
            active[idx[~go]] = False
        t = F[pos[:, 0], pos[:, 1]]
        better = cur > finals_seen
        finals_seen = np.where(better, cur, finals_seen)
        finals_true = np.where(better, t, finals_true)
        final_pos = np.where(better[:, None], pos, final_pos)
        used_all += used
    reach = finals_true >= best_true - REACH_TOL
    return {"reach": reach, "final_true": finals_true, "final_seen": finals_seen, "pos": final_pos, "used": used_all}


def summ(res, F):
    lowpk = F[:11, :11].max()  # 低い山の頂（左下の半分の中のいちばん高い所）
    return {"reach_best": r(res["reach"].mean()),
            "at_low_peak": r((np.abs(res["final_true"] - lowpk) <= REACH_TOL).mean()),
            "final_true_mean": r(res["final_true"].mean(), 3),
            "seen_minus_true_mean": r((res["final_seen"] - res["final_true"]).mean(), 3),
            "used_mean": r(res["used"].mean(), 2)}


def basin_share(F, step):
    """ばらつき0なら、着き先は出発点だけで決まる。441の出発点すべてで数えた、いちばん良い所に着く出発点の割合"""
    ok = 0
    for i in range(NG):
        for j in range(NG):
            p = np.array([i, j])
            while True:
                nb = [p + d for d in ([step, 0], [-step, 0], [0, step], [0, -step]) if (0 <= (p + d)).all() and ((p + d) < NG).all()]
                v = [F[q[0], q[1]] for q in nb]
                k = int(np.argmax(v))
                if v[k] > F[p[0], p[1]]:
                    p = nb[k]
                else:
                    break
            ok += F[p[0], p[1]] >= F.max() - REACH_TOL
    return ok / NG ** 2


def main():
    t0 = time.time()
    F = surface()
    out = {"setup": {**BASE, "start_fixed": {"temp": float(TEMP[START_FIXED[0]]), "hours": r(HOURS[START_FIXED[1]], 1)},
                     "runs": RUNS, "reach_tol": REACH_TOL, "grid": NG,
                     "best_true": r(F.max(), 3), "best_temp": float(TEMP[np.unravel_index(F.argmax(), F.shape)[0]]),
                     "best_hours": r(HOURS[np.unravel_index(F.argmax(), F.shape)[1]], 1),
                     "low_peak_true": r(F[:11, :11].max(), 3),
                     "start_true": r(F[START_FIXED], 3)}}
    pd.DataFrame(F.round(3), index=TEMP, columns=[f"{h:.1f}" for h in HOURS]).to_csv(DATA / "true_surface.csv", index_label="temp_c")

    # 1) 基本：今の条件から、ばらつき2点・1段ずつ・1個ずつ焼く
    rows = []
    ways = [("基本：今の条件から・1段ずつ・1個ずつ", dict(start="fixed")),
            ("1つの条件を3個ずつ焼いて平均", dict(start="fixed", repeat=3)),
            ("でたらめな出発点から1回", dict(start="random")),
            ("でたらめな出発点4つ（各30個）", dict(start="random", n_starts=4))]
    traces = {}
    for k, (name, kw) in enumerate(ways):
        p = {**BASE, **kw}
        rng = np.random.default_rng(SEED * 10 + k)
        res = climb(F, rng, RUNS, p["noise"], p["step"], p["repeat"], p["budget"], p["start"], kw.get("n_starts", 1))
        rows.append({"way": name, **summ(res, F)})
        traces[name] = res
    ways_df = pd.DataFrame(rows)
    ways_df.to_csv(RES / "ways.csv", index=False)
    out["ways"] = rows

    # ばらつき0のとき（式どおりではなく、441の出発点をすべてたどった数え上げ）
    out["no_noise"] = {"fixed_start_final_true": None, "basin_share_step": {}}
    for st in [1, 2, 4]:
        out["no_noise"]["basin_share_step"][str(st)] = r(basin_share(F, st))
    res0 = climb(F, np.random.default_rng(SEED), 1, 0.0, 1, 1, 10 ** 6, "fixed")
    out["no_noise"]["fixed_start_final_true"] = r(res0["final_true"][0], 3)
    out["no_noise"]["fixed_start_final_temp"] = float(TEMP[res0["pos"][0, 0]])
    out["no_noise"]["fixed_start_final_hours"] = r(HOURS[res0["pos"][0, 1]], 1)

    # 2) 確かめ：ばらつき×きざみ×出発点（4×3×2＝24通り）
    grid = []
    for noise in [0.0, 1.0, 2.0, 4.0]:
        for step in [1, 2, 4]:
            for start in ["fixed", "random"]:
                rng = np.random.default_rng(SEED * 100 + int(noise * 10) * 10 + step + (500 if start == "random" else 0))
                res = climb(F, rng, RUNS, noise, step, 1, BASE["budget"], start)
                grid.append({"noise": noise, "step": step, "start": start, **summ(res, F)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid_noise_step_start.csv", index=False)
    out["grid_ranges"] = {st: {"reach_min": r(g[g.start == st].reach_best.min()), "reach_max": r(g[g.start == st].reach_best.max()),
                               "seen_minus_true_min": r(g[g.start == st].seen_minus_true_mean.min(), 3),
                               "seen_minus_true_max": r(g[g.start == st].seen_minus_true_mean.max(), 3)}
                          for st in ["fixed", "random"]}

    # 3) 確かめ：低い山の高さ（16・22・26点）と、高い山の位置（近い・基本・遠い）
    grid2 = []
    for lp in [16.0, 22.0, 26.0]:
        for name, hc in [("近い", (0.6, 0.6)), ("基本", (0.78, 0.72)), ("遠い", (0.9, 0.9))]:
            F2 = surface(low_peak=lp, high_center=hc)
            for start in ["fixed", "random"]:
                rng = np.random.default_rng(SEED * 1000 + int(lp) * 10 + len(grid2))
                res = climb(F2, rng, RUNS, BASE["noise"], BASE["step"], 1, BASE["budget"], start)
                s = summ(res, F2)
                grid2.append({"low_peak_height": lp, "high_peak_place": name, "start": start,
                              "best_true": r(F2.max(), 3), "reach_best": s["reach_best"],
                              "final_true_mean": s["final_true_mean"], "seen_minus_true_mean": s["seen_minus_true_mean"]})
    g2 = pd.DataFrame(grid2)
    g2.to_csv(RES / "grid_landscape.csv", index=False)
    out["landscape_ranges"] = {st: {"reach_min": r(g2[g2.start == st].reach_best.min()), "reach_max": r(g2[g2.start == st].reach_best.max())}
                               for st in ["fixed", "random"]}
    out["seen_above_true_all_settings"] = int((pd.concat([g.seen_minus_true_mean[g.noise > 0], g2.seen_minus_true_mean]) > 0).sum())
    out["settings_with_noise"] = int((g.noise > 0).sum() + len(g2))
    fx = pd.concat([g[g.start == "fixed"].reach_best, g2[g2.start == "fixed"].reach_best])
    rd = pd.concat([g[g.start == "random"].reach_best, g2[g2.start == "random"].reach_best])
    out["fixed_start_all"] = {"settings": int(len(fx)), "reach_max": r(fx.max())}
    out["random_start_all"] = {"settings": int(len(rd)), "reach_min": r(rd.min()), "reach_max": r(rd.max())}
    st1 = g[(g.step == 1) & (g.noise > 0)]
    out["step1_noise_seen_minus_true"] = {"min": r(st1.seen_minus_true_mean.min(), 3), "max": r(st1.seen_minus_true_mean.max(), 3)}

    # data：基本の置き方の1回目〜200回目の着き先
    b = traces[ways[0][0]]
    pd.DataFrame({"run": np.arange(200), "final_temp": TEMP[b["pos"][:200, 0]], "final_hours": HOURS[b["pos"][:200, 1]].round(1),
                  "final_true": b["final_true"][:200].round(3), "final_seen": b["final_seen"][:200].round(3),
                  "pieces_used": b["used"][:200]}).to_csv(DATA / "basic_runs_first200.csv", index=False)

    json.dump(out, open(RES / "a1108_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：地形と着き先（基本、2,000回）
    fig, ax = plt.subplots(figsize=(7.2, 5.6))
    cs = ax.contourf(HOURS, TEMP, F, levels=np.arange(60, 92, 2), cmap="Blues")
    fig.colorbar(cs, ax=ax, label="本当の点数（置いた値）")
    cnt = pd.DataFrame(b["pos"], columns=["i", "j"]).value_counts().reset_index(name="n")
    ax.scatter(HOURS[cnt.j], TEMP[cnt.i], s=cnt.n / 4, color=ORANGE, edgecolor="white", lw=0.5, label="着いた所（大きさは回数）")
    ax.scatter(HOURS[START_FIXED[1]], TEMP[START_FIXED[0]], marker="s", s=60, color=INK, label="今の条件（出発点）")
    gi = np.unravel_index(F.argmax(), F.shape)
    ax.scatter(HOURS[gi[1]], TEMP[gi[0]], marker="*", s=160, color=GREEN, edgecolor=INK, lw=0.5, label="いちばん良い所")
    ax.set_xlabel("焼く時間（時間）")
    ax.set_ylabel("窯の温度（℃）")
    ax.set_title("今の条件から1段ずつ登った2,000回の着き先")
    ax.legend(fontsize=8, loc="lower right", framealpha=0.9)
    save(fig, "a1108_landscape.png", SRC, y=-0.03)

    # 図2：やり方ごとの「いちばん良い所に着いた割合」と「低い山の頂上に着いた割合」
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    y = np.arange(len(ways_df))[::-1]
    ax.barh(y + 0.18, ways_df.reach_best * 100, color=BLUE, height=0.34, label=f"いちばん良い所（{F.max():.3f}点）")
    ax.barh(y - 0.18, ways_df.at_low_peak * 100, color=ORANGE, height=0.34, label="低い山の頂上（82点）")
    for yy, v, w, u in zip(y, ways_df.reach_best * 100, ways_df.at_low_peak * 100, ways_df.used_mean):
        ax.text(v + 1, yy + 0.18, f"{round(v, 2):g}%（焼いた数 平均{u:g}個）", va="center", fontsize=8.5)
        ax.text(w + 1, yy - 0.18, f"{round(w, 2):g}%", va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(ways_df.way)
    ax.set_xlim(0, 100)
    ax.set_xlabel("着いた割合（%、1点以内、2,000回）")
    ax.set_title("ばらつき2点・1段ずつ・焼ける数120個まで")
    ax.legend(fontsize=8.5, loc="lower right", frameon=False)
    save(fig, "a1108_ways.png", SRC, y=-0.04)

    # 図3：確かめ（ばらつき×きざみ）
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, st, col_, ttl in [(axes[0], "fixed", "at_low_peak", "今の条件から：低い山の頂上（82点）に着いた割合"),
                              (axes[1], "random", "reach_best", "でたらめな出発点から：いちばん良い所に着いた割合")]:
        for step, c in zip([1, 2, 4], [BLUE, ORANGE, GREEN]):
            sub = g[(g.start == st) & (g.step == step)]
            ax.plot(sub.noise, sub[col_] * 100, "o-", color=c, label=f"一度に{step}段ずつ")
        ax.set_title(ttl, fontsize=11)
        ax.set_xlabel("1個ごとのばらつき（標準偏差、点）")
        ax.set_xticks([0, 1, 2, 4])
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("着いた割合（%、2,000回）")
    axes[0].text(2.6, 66, "今の条件からは、いちばん良い所には\n12通りすべてで0%。\n2段・4段ずつでは、動ける点が\n低い山の頂上の点に重ならない", ha="center", fontsize=9, color=INK)
    axes[1].legend(fontsize=9, frameon=False)
    save(fig, "a1108_robust.png", SRC, y=-0.05)

    print(json.dumps({k: out[k] for k in ["no_noise", "grid_ranges", "landscape_ranges", "fixed_start_all", "random_start_all", "step1_noise_seen_minus_true"]}, ensure_ascii=False, indent=1))
    print(g.to_string())
    print(g2.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
