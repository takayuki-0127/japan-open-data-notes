"""848 計測の仕様が月の途中で変わったとき、前月比はどうなるのか？（架空のデータ）

架空のアカウントの1日ごとの再生数（9月1日〜11月30日の91日）。本当の再生数は、月に3%ずつ
なだらかに伸び、週末は多く、日ごとに振れる。10月16日から「再生1回」の数え方が変わり、
同じ見られ方でも記録される回数が1.20倍になったと置く。
前月比（10月÷9月、11月÷10月）が本当の伸びとどれだけずれるかを数え、
(1) 切り替えのあと7日間だけ新旧両方の数え方が見られる場合に、その比で直す
(2) 新旧両方が見られない場合に、日ごとの記録から段差を推し量って直す（回帰）
の2つの直し方を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 848
SRC = "架空のアカウントの再生数（作成者が乱数で作成、seed 848）"
DATES = pd.date_range("2026-09-01", "2026-11-30", freq="D")
T = len(DATES)
MONTH = np.asarray(DATES.month)
REPS = 500
BASE = dict(change_day=16, factor=1.20, growth=0.03, noise=0.12, jump=0.0, overlap=7)


def change_index(change_day):
    return int(np.where((DATES.month == 10) & (DATES.day == change_day))[0][0])


def simulate(rng, change_day=16, factor=1.20, growth=0.03, noise=0.12, jump=0.0, overlap=7):
    t = np.arange(T)
    k = change_index(change_day)
    weekend = np.asarray(DATES.dayofweek >= 5)
    logm = np.log(5000) + np.log1p(growth) * t / 30.4 + np.log(1.2) * weekend
    logm = logm + np.log1p(jump) * (t >= k)            # 同じ日に本当の伸び（話題になった等）も起きる場合
    true = np.round(np.exp(logm + rng.normal(0, noise, T))).astype(int)
    f_day = factor * np.exp(rng.normal(0, 0.03, T))     # 新しい数え方の倍率は日ごとに少し振れる
    new_count = np.round(true * f_day).astype(int)
    recorded = np.where(t >= k, new_count, true)
    old_shown = np.where((t >= k) & (t < k + overlap), true, -1)   # 新旧両方が見られる日の旧い数え方
    return pd.DataFrame({"date": DATES.strftime("%Y-%m-%d"), "true_old_rule": true, "recorded": recorded,
                         "old_rule_shown": old_shown}), k


def month_sum(x):
    return {m: float(x[MONTH == m].sum()) for m in (9, 10, 11)}


def month_avg(x):
    """月の1日あたりの平均（月の日数の違い 30日・31日 を除くため）"""
    return {m: float(x[MONTH == m].mean()) for m in (9, 10, 11)}


def mom(x):
    s = month_avg(x)
    return s[10] / s[9] - 1, s[11] / s[10] - 1


def mom_total(x):
    s = month_sum(x)
    return s[10] / s[9] - 1, s[11] / s[10] - 1


def fix_overlap(df, k, overlap):
    o = df.iloc[k:k + overlap]
    f_hat = o.recorded.sum() / o.old_rule_shown.sum()
    adj = df.recorded.to_numpy().astype(float)
    adj[k:] = adj[k:] / f_hat
    return adj, float(f_hat)


def fix_regression(df, k):
    """log(記録) = 切片 + 傾き×日 + 曜日 + 段差×（切り替え後）を最小二乗で当てはめ、段差で割り戻す"""
    y = np.log(df.recorded.to_numpy())
    t = np.arange(T)
    dow = np.asarray(DATES.dayofweek)
    X = np.column_stack([np.ones(T), t / 30.4] + [(dow == d).astype(float) for d in range(1, 7)] + [(t >= k).astype(float)])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    f_hat = float(np.exp(b[-1]))
    adj = df.recorded.to_numpy().astype(float)
    adj[k:] = adj[k:] / f_hat
    return adj, f_hat


def one(rng, **kw):
    df, k = simulate(rng, **kw)
    tr = mom(df.true_old_rule.to_numpy())
    nv = mom(df.recorded.to_numpy())
    a1, f1 = fix_overlap(df, k, kw.get("overlap", 7))
    a2, f2 = fix_regression(df, k)
    return df, k, {"true_oct": tr[0], "true_nov": tr[1], "naive_oct": nv[0], "naive_nov": nv[1],
                   "overlap_oct": mom(a1)[0], "overlap_nov": mom(a1)[1], "reg_oct": mom(a2)[0], "reg_nov": mom(a2)[1],
                   "f_overlap": f1, "f_reg": f2}


def run_many(seed, reps=REPS, **kw):
    return pd.DataFrame([one(np.random.default_rng(seed + r), **kw)[2] for r in range(reps)])


def main():
    t0 = time.time()
    res = {"base": BASE, "days": T, "reps": REPS, "period": "2026-09-01〜2026-11-30（架空）",
           "mom_definition": "前月比は月の1日あたりの平均どうしで比べる（月の日数の違いを除く）"}

    # 1回分
    df, k, r1 = one(np.random.default_rng(SEED), **BASE)
    df.to_csv(DATA / "daily.csv", index=False)
    s_true, s_rec = month_sum(df.true_old_rule.to_numpy()), month_sum(df.recorded.to_numpy())
    tt = mom_total(df.true_old_rule.to_numpy())
    res["one_run"] = {"month_true": s_true, "month_recorded": s_rec,
                      "month_avg_true": {m: round(v, 1) for m, v in month_avg(df.true_old_rule.to_numpy()).items()},
                      "month_avg_recorded": {m: round(v, 1) for m, v in month_avg(df.recorded.to_numpy()).items()},
                      "true_total_oct": round(tt[0], 4), "true_total_nov": round(tt[1], 4),
                      **{k2: round(v, 4) for k2, v in r1.items()}}

    # 500回（基本）
    base = run_many(SEED * 1000, **BASE)
    rows = []
    for name, col in [("本当の伸び", "true"), ("記録そのまま", "naive"), ("新旧両方の7日で直す", "overlap"), ("段差を推し量って直す", "reg")]:
        for mo, lab in [("oct", "10月÷9月"), ("nov", "11月÷10月")]:
            x = base[f"{col}_{mo}"] * 100
            err = (base[f"{col}_{mo}"] - base[f"true_{mo}"]) * 100
            rows.append({"method": name, "compare": lab, "mom_mean_pct": round(float(x.mean()), 2),
                         "err_mean_pt": round(float(err.mean()), 2),
                         "err_p05_pt": round(float(err.quantile(0.05)), 2), "err_p95_pt": round(float(err.quantile(0.95)), 2)})
    meth = pd.DataFrame(rows)
    meth.to_csv(RES / "methods.csv", index=False)
    res["methods"] = meth.to_dict("records")
    res["factor_estimates"] = {"overlap_p05": round(float(base.f_overlap.quantile(0.05)), 3),
                               "overlap_p95": round(float(base.f_overlap.quantile(0.95)), 3),
                               "reg_p05": round(float(base.f_reg.quantile(0.05)), 3),
                               "reg_p95": round(float(base.f_reg.quantile(0.95)), 3)}

    # 確かめ：置き方を変える（各500回）
    cases = [("基本（10月16日・1.20倍・本当の伸び月3%）", {}),
             ("切り替え日 10月2日", {"change_day": 2}),
             ("切り替え日 10月25日", {"change_day": 25}),
             ("倍率 1.10倍", {"factor": 1.10}),
             ("倍率 0.85倍（数え方が厳しくなる）", {"factor": 0.85}),
             ("本当の伸び 月0%", {"growth": 0.0}),
             ("日ごとの振れ 大（0.25）", {"noise": 0.25}),
             ("同じ日に本当にも15%伸びた", {"jump": 0.15}),
             ("新旧両方が見られるのは3日だけ", {"overlap": 3})]
    rows = []
    for i, (name, kw) in enumerate(cases):
        d = run_many(SEED * 1000 + (i + 1) * 10000, **{**BASE, **kw})
        rows.append({"case": name,
                     "true_oct_pct": round(float(d.true_oct.mean() * 100), 2),
                     "naive_oct_pct": round(float(d.naive_oct.mean() * 100), 2),
                     "naive_nov_err_pt": round(float(((d.naive_nov - d.true_nov) * 100).mean()), 2),
                     "naive_oct_err_pt": round(float(((d.naive_oct - d.true_oct) * 100).mean()), 2),
                     "overlap_oct_err_pt": round(float(((d.overlap_oct - d.true_oct) * 100).mean()), 2),
                     "overlap_oct_err_p95abs_pt": round(float(((d.overlap_oct - d.true_oct) * 100).abs().quantile(0.95)), 2),
                     "reg_oct_err_pt": round(float(((d.reg_oct - d.true_oct) * 100).mean()), 2),
                     "reg_oct_err_p95abs_pt": round(float(((d.reg_oct - d.true_oct) * 100).abs().quantile(0.95)), 2),
                     **{f"{c}_oct_err_{q}_pt": round(float(((d[f"{c}_oct"] - d.true_oct) * 100).quantile(qq)), 2)
                        for c in ("naive", "overlap", "reg") for q, qq in (("p05", 0.05), ("p95", 0.95))}})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False)
    res["robustness"] = rob.to_dict("records")

    # 図1：1回分の日ごとの再生数
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    x = DATES
    ax.plot(x, df.true_old_rule, color=GRAY, lw=1.2, label="本当の再生数（旧い数え方のまま）")
    ax.plot(x, df.recorded, color=BLUE, lw=1.6, label="記録された再生数")
    ax.axvline(DATES[k], color=ORANGE, ls="--", lw=1.2)
    ax.text(DATES[k], ax.get_ylim()[1] * 0.98, " 10月16日 数え方が変わる", color=ORANGE, fontsize=9, va="top")
    for m in (9, 10, 11):
        mid = DATES[MONTH == m][7 if m == 10 else 14]
        ax.text(mid, 3200, f"{m}月 記録 {s_rec[m]/10000:.1f}万\n（本当 {s_true[m]/10000:.1f}万）",
                ha="center", fontsize=8.5, color=INK)
    ax.set_ylim(2900, ax.get_ylim()[1])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-m/%-d"))
    ax.set_ylabel("1日の再生数")
    ax.set_title("数え方が変わった日から、記録だけが一段上がる（1回分）")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    save(fig, "a848_daily.png", SRC)

    # 図2：前月比（500回の平均）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    names = ["本当の伸び", "記録そのまま", "新旧両方の7日で直す", "段差を推し量って直す"]
    colors = [GRAY, ORANGE, GREEN, BLUE]
    xx = np.arange(2)
    for j, (nm, c) in enumerate(zip(names, colors)):
        v = [meth[(meth["method"] == nm) & (meth["compare"] == cp)].mom_mean_pct.iloc[0] for cp in ["10月÷9月", "11月÷10月"]]
        ax.bar(xx + (j - 1.5) * 0.2, v, 0.2, color=c, label=nm)
        for xi, vi in zip(xx, v):
            ax.text(xi + (j - 1.5) * 0.2, vi + 0.3, f"{vi:+.1f}", ha="center", fontsize=8.5)
    ax.set_xticks(xx); ax.set_xticklabels(["10月÷9月", "11月÷10月"])
    ax.set_ylabel("前月比（%）")
    ax.set_xlabel("月の1日あたりの平均どうしで比べた前月比（500回の平均）")
    ax.set_ylim(0, max(meth.mom_mean_pct) * 1.3)
    ax.set_title("仕様の変更は、前月比を2か月続けてふくらませる")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    save(fig, "a848_mom.png", SRC)

    # 図3：置き方ごとの10月÷9月のずれ
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    y = np.arange(len(rob))
    ax.axvline(0, color=INK, lw=1)
    for c, col, mk, lab, dy in [("naive", ORANGE, "o", "記録そのまま", -0.22), ("overlap", GREEN, "s", "新旧両方の日数で直す", 0.0),
                                ("reg", BLUE, "D", "段差を推し量って直す", 0.22)]:
        m = rob[f"{c}_oct_err_pt"]
        ax.errorbar(m, y + dy, xerr=[m - rob[f"{c}_oct_err_p05_pt"], rob[f"{c}_oct_err_p95_pt"] - m],
                    fmt=mk, color=col, ms=6, capsize=2, lw=1, label=lab, zorder=3)
    short = [c.split("（")[0] if c.startswith("基本") else c for c in rob.case]
    ax.set_yticks(y); ax.set_yticklabels(short, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("10月÷9月の、本当の伸びとのずれ（ポイント。点は500回の平均、線は5〜95%）")
    ax.set_title("段差を推し量る直し方は、同じ日の本当の伸びまで消してしまう")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.35, -0.13), ncol=3, fontsize=9)
    save(fig, "a848_cases.png", SRC, y=-0.06)

    with open(RES / "a848_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"{time.time() - t0:.1f} 秒")


if __name__ == "__main__":
    main()
