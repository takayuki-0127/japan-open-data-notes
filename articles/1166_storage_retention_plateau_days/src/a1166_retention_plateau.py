"""1166 古いものを消す決まりを入れると、量の伸びはどこで止まり、そこまで何日かかるのか？（架空のデータ）

作成者が置いた架空のアプリの保存ファイル。毎日およそ1,000件（数は平均1,000のばらつきのある乱数）のファイルが増え、
1件は20MB（1日に約20GB）。消す決まりは次のとおり置いた：
  ・作ってから R 日たったら消す（基本 R＝90日）
  ・一部（残す印の付いたファイル）は365日残す（基本0%、確かめで10%・30%）
  ・「最後に使ってから R 日」で消す決まり：作ったあと、ファイルは λ0×exp（−経過日数÷τ）の割合で使われる
    （λ0＝1日0.3回、τ は対数が正規の形で中央値10日・対数の標準偏差1.0）。使われると消すまでの日数が数え直しになる
  ・増える件数が毎月一定の率で伸びる場合（月0・1・3%）
1,095日（3年）作り、毎日の量（GB）を数えた。
確かめ：R（30・90・180日）×残す印の割合（0・10・30%）×決まり（作ってから／最後に使ってから）×伸び（月0・1・3%）の54通り
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1166
SRC = "架空のアプリの保存ファイル（作成者が置いた増え方・消す決まり・使われ方からの乱数、seed 1166）"
DAYS = 1095
PER_DAY, FILE_GB = 1000, 0.02
LONG_KEEP = 365
LAM0, TAU_MED, TAU_SD = 0.3, 10.0, 1.0
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def make_files(rng, growth):
    days = np.arange(1, DAYS + 1)
    lam = PER_DAY * (1 + growth) ** ((days - 1) / 30)
    n = rng.poisson(lam)
    create = np.repeat(days, n)
    return create


def last_use_age(rng, n, R_each):
    """作ってからの最後に使った日（経過日数）。使われる間隔が R を超えると、その前に消えている"""
    tau = np.exp(rng.normal(np.log(TAU_MED), TAU_SD, n))
    k = rng.poisson(LAM0 * tau)
    fid = np.repeat(np.arange(n), k)
    age = rng.exponential(np.repeat(tau, k))
    order = np.argsort(fid * 8192.0 + np.minimum(age, 8000.0), kind="stable")
    fid, age = fid[order], age[order]
    start = np.r_[True, fid[1:] != fid[:-1]]
    prev = np.r_[0.0, age[:-1]]
    prev[start] = 0.0
    bad = (age - prev) > R_each[fid]
    cb = np.cumsum(bad)
    first_idx = np.flatnonzero(start)
    base = np.repeat(cb[first_idx] - bad[first_idx], np.diff(np.r_[first_idx, len(fid)]))
    ok = (cb - base) == 0                                 # 消える前に使われた分（並べた先頭から続く分）
    fo, ao = fid[ok], age[ok]
    ends = np.r_[fo[1:] != fo[:-1], True]
    last = np.zeros(n)
    last[fo[ends]] = ao[ends]
    return last


def run(seed, R, long_share, rule, growth):
    rng = np.random.default_rng(seed)
    create = make_files(rng, growth)
    n = len(create)
    keep = np.where(rng.random(n) < long_share, LONG_KEEP, R).astype(float)
    if rule == "used":
        extra = last_use_age(rng, n, keep)
    else:
        extra = np.zeros(n)
    delete = create + np.ceil(extra) + keep              # この日に消える
    add = np.bincount(create, minlength=DAYS + 2)[:DAYS + 1]
    d = np.clip(delete, 0, DAYS + 1).astype(int)
    sub = np.bincount(d, minlength=DAYS + 2)[:DAYS + 1]
    level = np.cumsum(add - sub)[1:] * FILE_GB            # 1〜1,095日目の量（GB）
    return level, extra, keep


def stats(level, growth, R, long_share, rule):
    end = level[-30:].mean()
    t = np.arange(1, DAYS + 1)
    reach95 = int(t[np.flatnonzero(level >= 0.95 * end)[0]])
    out = {"R": R, "long_share_pct": long_share * 100, "rule": "最後に使ってから" if rule == "used" else "作ってから",
           "growth_pct": growth * 100,
           "level_day90": r(level[89], 1), "level_day365": r(level[364], 1), "level_end": r(end, 1),
           "day90_over_end_pct": r(level[89] / end * 100, 2),
           "reach95_day": reach95,
           "last_year_growth_pct": r((level[-30:].mean() / level[-395:-365].mean() - 1) * 100, 2),
           "inflow_growth_year_formula_pct": r(((1 + growth) ** (365 / 30) - 1) * 100, 2)}
    if rule != "used" and growth == 0:
        out["plateau_formula"] = r(PER_DAY * FILE_GB * ((1 - long_share) * R + long_share * LONG_KEEP), 1)
    return out


def main():
    out = {}
    # 基本の4つ
    cases = [("作ってから90日", 90, 0.0, "create", 0.0),
             ("作ってから90日（1割は365日）", 90, 0.1, "create", 0.0),
             ("最後に使ってから90日", 90, 0.0, "used", 0.0),
             ("作ってから90日・件数が月3%伸びる", 90, 0.0, "create", 0.03)]
    rows, series = [], {}
    for i, (nm, R, ls, rule, g) in enumerate(cases):
        level, extra, keep = run(SEED + i, R, ls, rule, g)
        st = stats(level, g, R, ls, rule)
        st["case"] = nm
        if rule == "used":
            st["last_use_mean_days"] = r(extra.mean(), 2)
            st["last_use_median_days"] = r(np.median(extra), 2)
            st["last_use_p90_days"] = r(np.quantile(extra, 0.9), 2)
            st["last_use_over_180_pct"] = r((extra > 180).mean() * 100, 3)
            st["stay_mean_days"] = r((np.ceil(extra) + keep).mean(), 2)
            st["plateau_from_stay_gb"] = r(PER_DAY * FILE_GB * st["stay_mean_days"], 1)
        rows.append(st)
        series[nm] = level
    base = pd.DataFrame(rows)
    cols = ["case"] + [c for c in base.columns if c != "case"]
    base = base[cols]
    base.to_csv(RES / "base_cases.csv", index=False)
    out["setting"] = {"files_per_day": PER_DAY, "file_gb": FILE_GB, "gb_per_day": PER_DAY * FILE_GB, "days": DAYS,
                      "long_keep_days": LONG_KEEP, "use_rate_per_day": LAM0, "tau_median_days": TAU_MED,
                      "tau_sd_log": TAU_SD,
                      "base_plateau_formula_gb": r(PER_DAY * FILE_GB * 90, 1),
                      "mixed_plateau_formula_gb": r(PER_DAY * FILE_GB * (0.9 * 90 + 0.1 * LONG_KEEP), 1),
                      "mixed_day90_formula_pct": r(90 / (0.9 * 90 + 0.1 * LONG_KEEP) * 100, 2),
                      "mixed_reach95_formula_day": r((0.95 * (0.9 * 90 + 0.1 * LONG_KEEP) - 0.9 * 90) / 0.1, 1)}
    out["base"] = base.to_dict(orient="records")
    lv = pd.DataFrame({"day": np.arange(1, DAYS + 1), **{f"case{i + 1}_gb": np.round(series[c[0]], 2)
                                                          for i, c in enumerate(cases)}})
    lv.to_csv(DATA / "daily_level_base.csv", index=False)
    print("base", round(time.time() - T0, 1), flush=True)

    # 確かめ：54通り
    rows = []
    gi = 0
    for rule in ["create", "used"]:
        for R in [30, 90, 180]:
            for ls in [0.0, 0.1, 0.3]:
                for g in [0.0, 0.01, 0.03]:
                    gi += 1
                    level, _, _ = run(SEED * 100 + gi, R, ls, rule, g)
                    rows.append(stats(level, g, R, ls, rule))
        print("grid", rule, round(time.time() - T0, 1), flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    g0 = grid[grid.growth_pct == 0]
    gc = g0[g0.rule == "作ってから"]
    gu = g0[g0.rule == "最後に使ってから"]
    gg = grid[grid.growth_pct > 0]
    out["grid"] = {
        "settings": int(len(grid)),
        "create_formula_maxdiff_pct": r(((gc.level_end - gc.plateau_formula).abs() / gc.plateau_formula).max() * 100, 3),
        "create_reach95_min": int(gc.reach95_day.min()), "create_reach95_max": int(gc.reach95_day.max()),
        "create_day90_over_end_min": r(gc.day90_over_end_pct.min(), 2),
        "used_reach95_min": int(gu.reach95_day.min()), "used_reach95_max": int(gu.reach95_day.max()),
        "used_over_create_end_min": r((gu.level_end.values / gc.level_end.values).min(), 3),
        "used_over_create_end_max": r((gu.level_end.values / gc.level_end.values).max(), 3),
        "growth_settings": int(len(gg)),
        "growth1_last_year_min": r(gg[gg.growth_pct == 1].last_year_growth_pct.min(), 2),
        "growth1_last_year_max": r(gg[gg.growth_pct == 1].last_year_growth_pct.max(), 2),
        "growth3_last_year_min": r(gg[gg.growth_pct == 3].last_year_growth_pct.min(), 2),
        "growth3_last_year_max": r(gg[gg.growth_pct == 3].last_year_growth_pct.max(), 2),
        "growth1_formula_pct": r(gg[gg.growth_pct == 1].inflow_growth_year_formula_pct.iloc[0], 2),
        "growth3_formula_pct": r(gg[gg.growth_pct == 3].inflow_growth_year_formula_pct.iloc[0], 2)}
    b = base.set_index("case")
    out["headline"] = {"plateau_base": b.loc["作ってから90日", "level_end"],
                       "mixed_end": b.loc["作ってから90日（1割は365日）", "level_end"],
                       "mixed_day90_pct": b.loc["作ってから90日（1割は365日）", "day90_over_end_pct"],
                       "mixed_reach95": int(b.loc["作ってから90日（1割は365日）", "reach95_day"]),
                       "used_end": b.loc["最後に使ってから90日", "level_end"],
                       "used_reach95": int(b.loc["最後に使ってから90日", "reach95_day"]),
                       "used_over_create_end": r(b.loc["最後に使ってから90日", "level_end"] / b.loc["作ってから90日", "level_end"], 3),
                       "growth3_last_year_pct": b.loc["作ってから90日・件数が月3%伸びる", "last_year_growth_pct"]}

    # 図1：基本の4つの量の動き
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    colors = [BLUE, GREEN, ORANGE, GRAY]
    for (nm, *_), c in zip(cases, colors):
        ax.plot(np.arange(1, DAYS + 1), series[nm], color=c, lw=1.6, label=nm)
    ax.axvline(90, color=INK, lw=0.8, ls=":")
    ax.text(92, ax.get_ylim()[1] * 0.03, "90日目", fontsize=8.5)
    ax.set_ylim(0, None)
    ax.set_xlim(0, DAYS)
    ax.set_xlabel("日数（1日目から増え始める）")
    ax.set_ylabel("残っている量（GB）")
    ax.set_title("止まる高さと日数は消す決まりで違い、件数が伸びると止まらない")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right", ncol=1, bbox_to_anchor=(1.0, 0.03))
    save(fig, "a1166_level_curves.png", SRC)

    # 図2：90日目の量÷3年目の量 と 95%に届いた日（伸びなし、作ってから・最後に使ってから）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True)
    for ax, rule, ttl in [(axes[0], "作ってから", "作ってから R 日で消す"), (axes[1], "最後に使ってから", "最後に使ってから R 日で消す")]:
        q = g0[g0.rule == rule]
        for j, ls in enumerate([0, 10, 30]):
            v = q[q.long_share_pct == ls]
            ax.bar(np.arange(3) + (j - 1) * 0.26, v.reach95_day, width=0.26, color=[LIGHT, BLUE, INK][j],
                   label=f"365日残す印：{ls}%" if rule == "作ってから" else None)
            for i, y in enumerate(v.reach95_day):
                ax.text(i + (j - 1) * 0.26, y + 8, f"{y}", ha="center", fontsize=7.5)
        ax.set_xticks(range(3))
        ax.set_xticklabels([f"R＝{R}日" for R in [30, 90, 180]])
        ax.set_title(ttl, fontsize=11)
    axes[0].set_ylabel("止まる高さの95%に届いた日")
    axes[0].set_ylim(0, g0.reach95_day.max() * 1.15)
    fig.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, 1.04), ncol=3)
    fig.suptitle("止まる高さの95%に届くまでの日数（件数の伸びなし、18通り）", y=1.1, fontsize=12)
    save(fig, "a1166_reach95.png", SRC)

    # 図3：伸びのあるとき、3年目の1年の伸び
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    sub = grid[(grid.long_share_pct == 0)]
    for j, g in enumerate([0, 1, 3]):
        v = sub[(sub.growth_pct == g) & (sub.rule == "作ってから")]
        ax.bar(np.arange(3) + (j - 1) * 0.26, v.last_year_growth_pct, width=0.26, color=[GRAY, BLUE, ORANGE][j],
               label=f"件数の伸び：月{g}%")
        for i, y in enumerate(v.last_year_growth_pct):
            ax.text(i + (j - 1) * 0.26, max(y, 0) + 1, f"{y:g}%", ha="center", fontsize=7.5)
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"作ってから{R}日で消す" for R in [30, 90, 180]])
    ax.set_ylabel("3年目の1年で量が伸びた割合（%）")
    ax.set_ylim(-3, sub.last_year_growth_pct.max() * 1.35)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_title("件数が伸びていると、消す決まりがあっても量は伸び続ける")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3)
    save(fig, "a1166_growth.png", SRC)

    out["run_sec"] = r(time.time() - T0, 1)
    (RES / "a1166_main.json").write_text(json.dumps({k: v for k, v in out.items() if k != "run_sec"},
                                                   ensure_ascii=False, indent=1, default=float))
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
