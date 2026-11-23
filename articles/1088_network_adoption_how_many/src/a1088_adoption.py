"""1088 新しい道具の使い始めは、まわりの何人が使えば広がるのか？（架空のデータ）

架空の会社（社員400人、20部署×20人）の仕事のやり取りのつながりを乱数で作り、社員ごとに
「やり取りのある人のうち何人が使っていれば、自分も使い始めるか」（使い始めの人数）を作成者が置く。
最初に何人かに新しい道具を配り、1日ごとに、条件を満たした人がその日に確率 q で使い始めるとして広がりを数える。
配る人数と配り方（ばらばら・1つの部署にまとめる・つながりの多い順）で、最後に使う人の割合がどう変わるか、
また使い始めた人の記録から「まわりの何人で使い始めたか」を数えると、置いた人数とどれだけずれるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1088
SRC = "架空の会社の社員どうしのやり取りと道具の使い始め（作成者が置いた確率からの乱数、seed 1088）"
N_DEPT, DEPT_SIZE = 20, 20
N = N_DEPT * DEPT_SIZE
BASE = {"p_in": 0.3, "cross": 200, "q": 0.3, "theta_values": [1, 2, 3, 4], "theta_probs": [0.05, 0.35, 0.40, 0.20]}
SEEDS = [5, 10, 20, 40]
PLACES = {"random": "ばらばらに配る", "one_dept": "1つの部署にまとめる", "top_deg": "つながりの多い順"}
REPS = 100
GRID_REPS = 40


def r(x, d=4):
    return round(float(x), d)


def company(rng, p_in=BASE["p_in"], cross=BASE["cross"]):
    dept = np.arange(N) // DEPT_SIZE
    same = dept[:, None] == dept[None, :]
    a = np.triu((rng.random((N, N)) < p_in) & same, 1)
    made = 0
    while made < cross:
        i, j = rng.integers(0, N, 2)
        if dept[i] == dept[j]:
            continue
        lo, hi = min(i, j), max(i, j)
        if a[lo, hi]:
            continue
        a[lo, hi] = True
        made += 1
    a = a | a.T
    return a.astype(np.int16), dept


def thresholds(rng, shift=0):
    th = rng.choice(BASE["theta_values"], N, p=BASE["theta_probs"]) + shift
    return np.maximum(th, 1)


def pick_seeds(rng, a, dept, s, how):
    if how == "random":
        return rng.choice(N, s, replace=False)
    if how == "one_dept":
        order = rng.permutation(N_DEPT)
        people = np.concatenate([rng.permutation(np.where(dept == d)[0]) for d in order])
        return people[:s]
    deg = a.sum(1) + rng.random(N) * 0.01  # 同じ数の人は乱数で並べる
    return np.argsort(-deg)[:s]


def spread(rng, a, th, seeds, q=BASE["q"], max_days=400):
    used = np.zeros(N, bool); used[seeds] = True
    is_seed = used.copy()
    day_start = np.full(N, -1); day_start[seeds] = 0
    rec_day = np.full(N, -1)   # 使い始めた日の終わりに、まわりで使っていた人数
    rec_week = np.full(N, -1)  # 使い始めた週の終わりに、まわりで使っていた人数
    cnt_at_start = np.full(N, -1)  # 使い始めた日の朝に、まわりで使っていた人数
    pending_week = []
    day = 0
    while day < max_days:
        day += 1
        cnt = a @ used
        ok = (~used) & (cnt >= th)
        if not ok.any():
            break
        new = ok & (rng.random(N) < q)
        cnt_at_start[new] = cnt[new]
        used = used | new
        day_start[new] = day
        cnt2 = a @ used
        rec_day[new] = cnt2[new]
        pending_week.extend(np.where(new)[0].tolist())
        if day % 7 == 0:
            rec_week[pending_week] = cnt2[pending_week]
            pending_week = []
    cnt2 = a @ used
    if pending_week:
        rec_week[pending_week] = cnt2[pending_week]
    return used, is_seed, day_start, cnt_at_start, rec_day, rec_week, day


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 配る人数×配り方（各100回、会社も使い始めの人数も毎回作り直す）
    rows, adopt_rows = [], []
    for rep in range(REPS):
        rr = np.random.default_rng(SEED * 100 + rep)
        a, dept = company(rr)
        th = thresholds(rr)
        for s in SEEDS:
            for how in PLACES:
                seeds = pick_seeds(rr, a, dept, s, how)
                used, is_seed, ds, c0, rd, rw, days = spread(rr, a, th, seeds)
                rows.append({"rep": rep, "seeds": s, "place": how, "final_share": used.mean(), "days": days,
                             "share_depts_half": float(np.mean([used[dept == d].mean() >= 0.5 for d in range(N_DEPT)]))})
                if s == 20 and how == "random":
                    if rep == 0:
                        one = pd.DataFrame({"person": [f"P{i:03d}" for i in range(N)], "dept": [f"D{d + 1:02d}" for d in dept],
                                            "deg": a.sum(1), "theta": th, "seed": is_seed.astype(int), "used": used.astype(int),
                                            "day_start": ds, "cnt_morning": c0, "rec_day": rd, "rec_week": rw})
                    m = used & ~is_seed
                    for i in np.where(m)[0]:
                        adopt_rows.append({"rep": rep, "theta": int(th[i]), "deg": int(a[i].sum()), "cnt_morning": int(c0[i]),
                                           "rec_day": int(rd[i]), "rec_week": int(rw[i])})
    sim = pd.DataFrame(rows)
    tab = sim.groupby(["seeds", "place"]).agg(final_share=("final_share", "mean"),
                                              p_over_half=("final_share", lambda x: (x > 0.5).mean()),
                                              final_p10=("final_share", lambda x: x.quantile(.1)),
                                              final_p90=("final_share", lambda x: x.quantile(.9)),
                                              days=("days", "mean")).reset_index().round(4)
    tab.to_csv(RES / "by_seeds_place.csv", index=False)
    ad = pd.DataFrame(adopt_rows)
    rec = {"n_adopters": int(len(ad)), "theta_mean": ad.theta.mean(), "cnt_morning_mean": ad.cnt_morning.mean(),
           "rec_day_mean": ad.rec_day.mean(), "rec_week_mean": ad.rec_week.mean(),
           "gap_morning": ad.cnt_morning.mean() - ad.theta.mean(), "gap_day": ad.rec_day.mean() - ad.theta.mean(), "gap_week": ad.rec_week.mean() - ad.theta.mean(),
           "share_rec_week_gt_theta": (ad.rec_week > ad.theta).mean(),
           "share_rec_day_gt_theta": (ad.rec_day > ad.theta).mean(),
           "deg_mean_adopters": ad.deg.mean()}
    byth = ad.groupby("theta").agg(n=("theta", "size"), cnt_morning=("cnt_morning", "mean"), rec_day=("rec_day", "mean"),
                                   rec_week=("rec_week", "mean")).reset_index()
    byth.round(4).to_csv(RES / "record_by_theta.csv", index=False)

    # 2) 確かめ：使い始めの人数・部署の中のつながり・部署をまたぐつながり・q（20人を配る、各40回）
    settings = [("基本", {}), ("使い始めの人数 −1", {"shift": -1}), ("使い始めの人数 +1", {"shift": 1}),
                ("部署の中 0.2", {"p_in": 0.2}), ("部署の中 0.4", {"p_in": 0.4}),
                ("またぐ 100本", {"cross": 100}), ("またぐ 400本", {"cross": 400}),
                ("q 0.1", {"q": 0.1}), ("q 0.6", {"q": 0.6})]
    grid = []
    for k, (name, st) in enumerate(settings):
        res = {h: [] for h in PLACES}
        gaps_w, gaps_d = [], []
        for rep in range(GRID_REPS):
            rr = np.random.default_rng(SEED * 1000 + k * 100 + rep)
            a, dept = company(rr, st.get("p_in", BASE["p_in"]), st.get("cross", BASE["cross"]))
            th = thresholds(rr, st.get("shift", 0))
            for how in PLACES:
                seeds = pick_seeds(rr, a, dept, 20, how)
                used, is_seed, ds, c0, rd, rw, days = spread(rr, a, th, seeds, st.get("q", BASE["q"]))
                res[how].append(used.mean())
                if how == "random":
                    m = used & ~is_seed
                    if m.any():
                        gaps_w.append((rw[m] - th[m]).mean()); gaps_d.append((rd[m] - th[m]).mean())
        grid.append({"setting": name, **{f"final_{h}": r(np.mean(v)) for h, v in res.items()},
                     **{f"p_over_half_{h}": r(np.mean(np.array(v) > 0.5)) for h, v in res.items()},
                     "gap_week": r(np.mean(gaps_w)), "gap_day": r(np.mean(gaps_d))})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    one.to_csv(DATA / "people_one_run.csv", index=False)
    one_check = float(one.used.mean())
    base20 = sim[(sim.rep == 0) & (sim.seeds == 20) & (sim.place == "random")].final_share.iloc[0]

    t = tab.set_index(["seeds", "place"])
    out = {"settings": {"n": N, "departments": N_DEPT, "dept_size": DEPT_SIZE, **BASE, "seeds_grid": SEEDS,
                        "reps": REPS, "grid_reps": GRID_REPS, "seed": SEED,
                        "theta_mean_formula": float(np.dot(BASE["theta_values"], BASE["theta_probs"])),
                        "cross_ties_per_person_formula": 2 * BASE["cross"] / N},
           "by_seeds_place": {f"{s}_{h}": {k: float(v) for k, v in t.loc[(s, h)].items()} for s in SEEDS for h in PLACES},
           "record_s20_random": {k: (r(v) if isinstance(v, float) else v) for k, v in rec.items()},
           "record_by_theta": byth.round(4).to_dict("records"),
           "grid_9": grid.to_dict("records"),
           "grid_ranges": {k: [r(grid[k].min()), r(grid[k].max())] for k in grid.columns if k != "setting"},
           "grid_one_dept_beats_random": int((grid.final_one_dept > grid.final_random).sum()),
           "grid_gap_week_gt_gap_day": int((grid.gap_week > grid.gap_day).sum()),
           "data_check": {"one_run_final_share": r(one_check), "sim_rep0_final_share": r(base20)}}
    json.dump(out, open(RES / "a1088_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：配る人数と最後に使う人の割合
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(len(SEEDS)); wdt = 0.27
    cols = {"random": GRAY, "one_dept": BLUE, "top_deg": ORANGE}
    for k, h in enumerate(PLACES):
        v = [t.loc[(s, h), "final_share"] * 100 for s in SEEDS]
        ax.bar(x + (k - 1) * wdt, v, wdt, color=cols[h], label=PLACES[h])
        for xx, vv in zip(x + (k - 1) * wdt, v):
            ax.text(xx, vv + 1.5, f"{vv:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{s}人" for s in SEEDS]); ax.set_xlabel("最初に配る人数（社員400人のうち）")
    ax.set_ylim(0, 112); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("最後に使っていた人の割合（%、100回の平均）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left")
    ax.set_title("配る人数が少し違うだけで、広がりが大きく変わる。1つの部署にまとめると広がらない", fontsize=11.5)
    save(fig, "a1088_seeds.png", SRC, y=-0.03)

    # 図2：使い始めの人数（置いた値）と記録の値
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    x = np.arange(len(byth)); wdt = 0.2
    ax.bar(x - 1.5 * wdt, byth.theta, wdt, color=INK, label="置いた使い始めの人数")
    ax.bar(x - 0.5 * wdt, byth.cnt_morning, wdt, color=LIGHT, label="使い始めた日の朝")
    ax.bar(x + 0.5 * wdt, byth.rec_day, wdt, color=BLUE, label="日ごとの記録（その日の終わり）")
    ax.bar(x + 1.5 * wdt, byth.rec_week, wdt, color=ORANGE, label="週ごとの記録（その週の終わり）")
    ax.set_xticks(x); ax.set_xticklabels([f"{int(v)}人で使い始める人\n（{int(n)}人）" for v, n in zip(byth.theta, byth.n)], fontsize=8.5)
    ax.set_ylim(0, max(byth.rec_week) * 1.35); ax.set_ylabel("まわりで使っていた人数（人、平均）")
    ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left")
    ax.set_title(f"記録から数えると、使い始めの人数は多めに出る（週ごとで+{rec['gap_week']:.2f}人）")
    save(fig, "a1088_record.png", SRC, y=-0.04)

    # 図3：確かめ（9通り）：20人を配ったときの最後の割合
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    x = np.arange(len(grid)); wdt = 0.27
    for k, h in enumerate(PLACES):
        ax.bar(x + (k - 1) * wdt, grid[f"final_{h}"] * 100, wdt, color=cols[h], label=PLACES[h])
    XL = ["基本", "使い始めの\n人数−1", "使い始めの\n人数+1", "部署の中\n0.2", "部署の中\n0.4", "またぐ\n100本", "またぐ\n400本", "1日の確率\nq=0.1", "1日の確率\nq=0.6"]
    ax.set_xticks(x); ax.set_xticklabels(XL, fontsize=8.5)
    ax.set_ylim(0, 112); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("最後に使っていた人の割合（%、各40回）")
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper left")
    ax.set_title("20人を配ったとき：置き方しだいで、ほぼ広がらないから、ほぼ全員まで動く", fontsize=12)
    save(fig, "a1088_robust.png", SRC, y=-0.04)

    print(json.dumps({k: out[k] for k in ["by_seeds_place", "record_s20_random", "grid_ranges", "data_check"]}, ensure_ascii=False, indent=1))
    print(byth.to_string()); print(grid.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
