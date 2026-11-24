"""1170 空きが何%を切ったら足すと決めるとき、増え方のばらつきで、足りなくなる日の何日前に気づけるのか？（架空のデータ）

作成者が置いた架空のアプリの保存領域。容量10,000GB、使っている量5,000GBから始め、1日に増える量の平均は20GB。
「空きが X% を切ったら足す」と決めたとき、気づいた日から満杯になる日までの日数（何日前に気づけたか）を数える。
増え方が毎日同じなら X%×容量÷20GB 日（10%なら50日、式どおり）。足すのに要る日数は30日と置いた。
(1) 増え方の4通り（日ごとの振れだけ／まれな大きな追加／増え方の水準がゆっくり動く／両方）を各10,000回
(2) 比べる決まり：「空き÷直近28日の1日の増えの平均」が50日を切ったら足す
(3) 確かめ：日ごとの振れ（3通り）×水準の動き（3通り）×まれな大きな追加（あり・なし）の18通り（各2,000回、空き10%）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1170
SRC = "架空のアプリの保存領域（作成者が置いた増え方からの乱数、seed 1170）"
CAP, U0, MU = 10_000.0, 5_000.0, 20.0
NEED = 30            # 足すのに要る日数（作成者が置いた値）
T = 1600             # 数える日数の上限
PHI = 0.99           # 水準の動きの持ちこし（1日あたり）
BURST_P, BURST_MEAN = 0.02, 200.0
WIN, PROJ_DAYS = 28, 50
PCTS = [10, 20, 30]
R_MAIN, R_GRID, CHUNK = 10_000, 2_000, 1_000
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def growth(rng, n, sd_day, sd_level, burst):
    """n 回分の毎日の増え（GB、形 n×T）。平均はどの置き方でも1日20GB"""
    base = MU - (BURST_P * BURST_MEAN if burst else 0.0)
    e = np.exp(sd_day * rng.standard_normal((n, T)) - sd_day ** 2 / 2)
    if sd_level > 0:
        z = rng.standard_normal((n, T))
        x = np.empty((n, T))
        x[:, 0] = sd_level * z[:, 0]
        k = np.sqrt(1 - PHI ** 2) * sd_level
        for t in range(1, T):
            x[:, t] = PHI * x[:, t - 1] + k * z[:, t]
        lev = np.exp(x - sd_level ** 2 / 2)
    else:
        lev = 1.0
    g = base * lev * e
    if burst:
        hit = rng.random((n, T)) < BURST_P
        g = g + hit * rng.exponential(BURST_MEAN, (n, T)) * lev
    return g


def first_true(m):
    """各行で最初に True になる日（1始まり）。なければ -1"""
    any_ = m.any(axis=1)
    idx = m.argmax(axis=1) + 1
    return np.where(any_, idx, -1)


def run(rng, R, sd_day, sd_level, burst, keep=False):
    rec = {f"pct{p}": [] for p in PCTS}
    rec["proj"], rec["full"], rec["level_at_alert"] = [], [], []
    examples = None
    for c in range(R // CHUNK):
        g = growth(rng, CHUNK, sd_day, sd_level, burst)
        used = U0 + np.cumsum(g, axis=1)
        free = CAP - used
        full = first_true(used >= CAP)
        rec["full"].append(full)
        for p in PCTS:
            a = first_true(free < CAP * p / 100)
            rec[f"pct{p}"].append(a)
        cs = np.cumsum(g, axis=1)
        avg = np.full_like(cs, np.nan)
        avg[:, WIN - 1] = cs[:, WIN - 1] / WIN
        avg[:, WIN:] = (cs[:, WIN:] - cs[:, :-WIN]) / WIN
        with np.errstate(invalid="ignore"):
            proj = (free / avg) < PROJ_DAYS
        proj[:, :WIN - 1] = False
        rec["proj"].append(first_true(proj))
        if keep and c == 0:
            examples = used[:6]
    out = {k: np.concatenate(v) for k, v in rec.items() if v}
    return out, examples


def lead_stats(alert, full):
    ok = (alert > 0) & (full > 0)
    lead = (full - alert)[ok]
    return {"runs_counted": int(ok.sum()), "lead_mean": r(lead.mean(), 2), "lead_median": r(np.median(lead), 1),
            "lead_p5": r(np.quantile(lead, 0.05), 1), "lead_p95": r(np.quantile(lead, 0.95), 1),
            "lead_min": int(lead.min()),
            "below_need_pct": r((lead < NEED).mean() * 100, 2),
            "over_100_pct": r((lead > 100).mean() * 100, 2)}, lead


SCEN = [("daily", "日ごとの振れだけ", 0.5, 0.0, False),
        ("burst", "まれな大きな追加あり", 0.5, 0.0, True),
        ("level", "増え方の水準がゆっくり動く", 0.5, 0.4, False),
        ("both", "大きな追加＋水準の動き", 0.5, 0.4, True)]


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"capacity_gb": CAP, "start_used_gb": U0, "mean_growth_gb_per_day": MU, "need_days": NEED,
                       "formula_lead_days": {f"pct{p}": r(CAP * p / 100 / MU, 1) for p in PCTS},
                       "level_phi_per_day": PHI, "burst_prob": BURST_P, "burst_mean_gb": BURST_MEAN,
                       "proj_window_days": WIN, "proj_threshold_days": PROJ_DAYS, "horizon_days": T}}
    rows, leads, ex = [], {}, None
    for key, name, sdd, sdl, b in SCEN:
        res, e = run(rng, R_MAIN, sdd, sdl, b, keep=(key == "level"))
        if e is not None:
            ex = e
        full = res["full"]
        row = {"scenario": key, "name": name, "sd_day": sdd, "sd_level": sdl, "burst": b,
               "not_full_in_horizon_pct": r((full < 0).mean() * 100, 2),
               "full_day_median": r(np.median(full[full > 0]), 1)}
        for p in PCTS:
            s, l = lead_stats(res[f"pct{p}"], full)
            row.update({f"pct{p}_{k}": v for k, v in s.items()})
            leads[(key, f"pct{p}")] = l
        s, l = lead_stats(res["proj"], full)
        row.update({f"proj_{k}": v for k, v in s.items()})
        leads[(key, "proj")] = l
        rows.append(row)
        print(key, round(time.time() - T0, 1), flush=True)
    main_df = pd.DataFrame(rows)
    main_df.to_csv(RES / "scenarios.csv", index=False)
    out["scenarios"] = rows

    # 分布の csv（空き10%と見込みの決まり、4通り）
    dist = []
    for key, *_ in SCEN:
        for rule in ["pct10", "proj"]:
            l = leads[(key, rule)]
            h = np.bincount(np.clip(l, 0, 200).astype(int), minlength=201)
            for d in range(201):
                if h[d]:
                    dist.append({"scenario": key, "rule": rule, "lead_days": d, "runs": int(h[d])})
    pd.DataFrame(dist).to_csv(RES / "lead_hist.csv", index=False)

    # data：水準が動く置き方の6回分の使っている量（10日ごと）
    days = np.arange(10, T + 1, 10)
    dd = pd.DataFrame({"day": days})
    for i in range(ex.shape[0]):
        dd[f"run{i + 1}_used_gb"] = np.round(ex[i, days - 1], 1)
    dd.to_csv(DATA / "used_examples.csv", index=False)

    # (3) 18通り
    grid = []
    for sdd in [0.25, 0.5, 1.0]:
        for sdl in [0.0, 0.2, 0.4]:
            for b in [False, True]:
                res, _ = run(rng, R_GRID, sdd, sdl, b)
                s, _ = lead_stats(res["pct10"], res["full"])
                sp, _ = lead_stats(res["proj"], res["full"])
                grid.append({"sd_day": sdd, "sd_level": sdl, "burst": b,
                             **{f"pct10_{k}": v for k, v in s.items()}, **{f"proj_{k}": v for k, v in sp.items()},
                             "not_full_pct": r((res["full"] < 0).mean() * 100, 2)})
        print("grid", sdd, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    g0 = grid[grid.sd_level == 0]
    gl = grid[grid.sd_level > 0]
    out["grid"] = {"settings": len(grid),
                   "pct10_below_need_min": r(grid.pct10_below_need_pct.min(), 2),
                   "pct10_below_need_max": r(grid.pct10_below_need_pct.max(), 2),
                   "pct10_p5_min": r(grid.pct10_lead_p5.min(), 1), "pct10_p5_max": r(grid.pct10_lead_p5.max(), 1),
                   "pct10_median_min": r(grid.pct10_lead_median.min(), 1), "pct10_median_max": r(grid.pct10_lead_median.max(), 1),
                   "no_level_pct10_below_need_max": r(g0.pct10_below_need_pct.max(), 2),
                   "level_pct10_below_need_min": r(gl.pct10_below_need_pct.min(), 2),
                   "proj_below_need_min": r(grid.proj_below_need_pct.min(), 2),
                   "proj_below_need_max": r(grid.proj_below_need_pct.max(), 2),
                   "settings_proj_lower_than_pct10": int((grid.proj_below_need_pct < grid.pct10_below_need_pct).sum()),
                   "settings_proj_higher_than_pct10": int((grid.proj_below_need_pct > grid.pct10_below_need_pct).sum()),
                   "not_full_max": r(grid.not_full_pct.max(), 2),
                   "level_noburst_settings": int(((grid.sd_level > 0) & ~grid.burst).sum()),
                   "level_noburst_proj_lower": int(((grid.sd_level > 0) & ~grid.burst &
                                                    (grid.proj_below_need_pct < grid.pct10_below_need_pct)).sum()),
                   "burst_settings": int(grid.burst.sum()),
                   "burst_proj_higher": int((grid.burst & (grid.proj_below_need_pct > grid.pct10_below_need_pct)).sum()),
                   "pct10_mean_min": r(grid.pct10_lead_mean.min(), 2), "pct10_mean_max": r(grid.pct10_lead_mean.max(), 2)}
    b = {x["scenario"]: x for x in rows}
    out["headline"] = {"formula_lead_pct10": out["setting"]["formula_lead_days"]["pct10"],
                       "daily_pct10_p5": b["daily"]["pct10_lead_p5"], "daily_pct10_below": b["daily"]["pct10_below_need_pct"],
                       "level_pct10_median": b["level"]["pct10_lead_median"], "level_pct10_p5": b["level"]["pct10_lead_p5"],
                       "level_pct10_below": b["level"]["pct10_below_need_pct"],
                       "level_proj_below": b["level"]["proj_below_need_pct"],
                       "both_pct10_below": b["both"]["pct10_below_need_pct"]}

    # 図1：何日前に気づけたかの分かれ方（空き10%、4通り）
    fig, axs = plt.subplots(2, 2, figsize=(8.4, 5.6), sharex=True)
    bins = np.arange(0, 202, 4)
    for ax, (key, name, *_) in zip(axs.ravel(), SCEN):
        l = leads[(key, "pct10")]
        ax.hist(np.clip(l, 0, 200), bins=bins, color=BLUE, alpha=0.9)
        ax.axvspan(0, NEED, color=ORANGE, alpha=0.12)
        ax.axvline(50, color=INK, lw=1, ls="--")
        ax.set_title(f"{name}\n30日未満 {b[key]['pct10_below_need_pct']:g}%", fontsize=10)
        ax.set_ylim(bottom=0)
    for ax in axs[1]:
        ax.set_xlabel("気づいた日から満杯までの日数（200日以上は200）")
    for ax in axs[:, 0]:
        ax.set_ylabel("回数（10,000回）")
    fig.suptitle("空き10%で気づく決まり：増え方が毎日同じなら50日前（破線）", fontsize=12)
    fig.tight_layout()
    save(fig, "a1170_lead_hist.png", SRC)

    # 図2：30日未満になった回の割合（4通り×決まり）
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    labs = [s[1] for s in SCEN]
    w = 0.2
    series = [("pct10", "空き10%", BLUE), ("pct20", "空き20%", GREEN), ("pct30", "空き30%", GRAY),
              ("proj", "残り日数の見込み50日", ORANGE)]
    for j, (k, lab, col) in enumerate(series):
        vals = [b[s[0]][f"{k}_below_need_pct"] for s in SCEN]
        xs = np.arange(4) + (j - 1.5) * w
        ax.bar(xs, vals, width=w, color=col, label=lab)
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.6, f"{v:g}", ha="center", fontsize=7.5)
    ax.set_xticks(range(4))
    ax.set_xticklabels([l.replace("＋", "＋\n") if len(l) > 10 else l for l in labs], fontsize=8.5)
    ax.set_ylim(0, max(main_df[[f"{k}_below_need_pct" for k, *_ in series]].max()) * 1.2 + 1)
    ax.set_ylabel("気づいてから満杯まで30日未満の回（%）")
    ax.set_title("足すのに30日要るとき、間に合わない回の割合", pad=26)
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    save(fig, "a1170_below_need.png", SRC)

    # 図3：使っている量の例（水準が動く置き方の6回）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    cols = [BLUE, ORANGE, GREEN, GRAY, INK, "#8a5cc2"]
    for i in range(ex.shape[0]):
        u = ex[i]
        end = np.argmax(u >= CAP) + 1 if (u >= CAP).any() else T
        ax.plot(np.arange(1, end + 1), u[:end] / 1000, color=cols[i], lw=1.2)
    ax.axhline(CAP / 1000, color=INK, lw=1)
    ax.axhline(CAP * 0.9 / 1000, color=ORANGE, lw=1, ls="--")
    ax.text(5, CAP * 0.9 / 1000 - 0.25, "空き10%の線", color=ORANGE, fontsize=9)
    ax.set_xlim(0, None)
    ax.set_ylim(U0 / 1000 - 0.2, CAP / 1000 + 0.2)
    ax.set_xlabel("日")
    ax.set_ylabel("使っている量（千GB）")
    ax.set_title("水準がゆっくり動くと、同じ線を越えてからの速さが回ごとに違う")
    save(fig, "a1170_used_examples.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1170_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
