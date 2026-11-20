"""882 1人増やしたときの待ち時間の減り方は、何人目まで大きいのか？（架空のデータ）

架空のスーパーのレジ。1日10時間（600分）、客はでたらめな間隔（ポアソン到着）で来る。
1人の会計にかかる時間はガンマ分布（基本は指数分布＝ばらつきの係数1）。
レジは空いた順に、来た順の客を受け付ける（1列に並ぶ）。開店時は行列なし。
同じ日の客と会計時間を使って、レジの台数（人数）だけを変えて比べる（共通の乱数）。
"""
import json, math, time
from heapq import heapreplace
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 882
SRC = "架空のスーパーのレジ（作成者が乱数で作成、seed 882）"
DAY = 600.0          # 1日の営業（分）
SVC = 2.0            # 1人の会計の平均（分）
BIG = 1.0            # 「大きい減り」とみなす平均の待ちの減り（分）


def make_day(rng, per_hour, cv=1.0, day=DAY, svc=SVC):
    lam = per_hour / 60.0
    n = rng.poisson(lam * day)
    arr = np.sort(rng.uniform(0, day, n))
    k = 1.0 / cv ** 2
    s = rng.gamma(k, svc / k, n)
    return arr, s


def waits(arr, s, c):
    free = [0.0] * c
    w = np.empty(len(arr))
    for i, (a, d) in enumerate(zip(arr.tolist(), s.tolist())):
        f = free[0]
        st = a if a > f else f
        w[i] = st - a
        heapreplace(free, st + d)
    return w


def erlang_c_wait(c, a, svc=SVC):
    """待ち行列の式（M/M/c、ずっと続く場合）の平均の待ち（分）"""
    if c <= a:
        return float("inf")
    s = sum(a ** k / math.factorial(k) for k in range(c))
    last = a ** c / math.factorial(c) * c / (c - a)
    pc = last / (s + last)
    return pc * svc / (c - a)


def run(rng, per_hour, cs, n_days, cv=1.0):
    rows = []
    for d in range(n_days):
        arr, s = make_day(rng, per_hour, cv)
        for c in cs:
            w = waits(arr, s, c)
            rows.append({"day": d, "staff": c, "n": len(w), "mean_wait": w.mean(),
                         "share_ge5": (w >= 5).mean(), "p90": np.quantile(w, .9), "max": w.max()})
    return pd.DataFrame(rows)


def summarize(df):
    g = df.groupby("staff").agg(mean_wait=("mean_wait", "mean"), share_ge5=("share_ge5", "mean"),
                                p90=("p90", "mean"), max_wait=("max", "mean")).reset_index()
    g["drop_from_prev"] = -g["mean_wait"].diff()
    g["ratio_to_prev"] = g["mean_wait"] / g["mean_wait"].shift()
    return g


def last_big(g, thr=BIG):
    """平均の待ちが thr 分以上減った、最後の『足した1人』の人数"""
    ok = g[g.drop_from_prev >= thr]
    return int(ok.staff.max()) if len(ok) else None


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 基本：1時間120人、会計2分（仕事量＝レジ4台分）、4〜10人
    base_cs = list(range(4, 11))
    df = run(rng, 120, base_cs, 200)
    base = summarize(df)
    a = 120 / 60 * SVC
    base["erlang_c_wait"] = [round(erlang_c_wait(c, a), 3) if c > a else None for c in base.staff]
    base["utilization"] = (a / base.staff).round(3)
    base.round(3).to_csv(RES / "base_by_staff.csv", index=False)

    # 1回分のデータ（1日分の客と、5人・6人・7人のときの待ち）
    arr, s = make_day(np.random.default_rng(SEED + 1), 120)
    one = pd.DataFrame({"customer_id": np.arange(1, len(arr) + 1), "arrival_min": arr, "service_min": s})
    for c in [5, 6, 7]:
        one[f"wait_staff{c}"] = waits(arr, s, c)
    one.to_csv(DATA / "one_day_customers.csv", index=False, float_format="%.3f")

    # 2) 確かめ：店の大きさ（仕事量＝レジ何台分か）を変える
    load_rows = []
    for ph in [30, 60, 120, 240, 480]:
        aa = ph / 60 * SVC
        cs = list(range(int(math.floor(aa)), int(math.floor(aa)) + 8))
        g = summarize(run(rng, ph, cs, 100))
        g["per_hour"] = ph; g["load"] = aa
        g["erlang_c_wait"] = [round(erlang_c_wait(c, aa), 3) if c > aa else None for c in g.staff]
        load_rows.append(g)
    loads = pd.concat(load_rows, ignore_index=True)
    loads["extra_staff"] = loads.staff - loads.load
    loads.round(3).to_csv(RES / "sensitivity_load.csv", index=False)

    # 2b) 確かめ：仕事量が整数でないとき（1時間100〜140人）
    fine_rows = []
    for ph in [100, 110, 130, 140]:
        aa = ph / 60 * SVC
        cs = list(range(int(math.floor(aa)), int(math.floor(aa)) + 6))
        g = summarize(run(rng, ph, cs, 100))
        g["per_hour"] = ph; g["load"] = aa
        fine_rows.append(g)
    fine = pd.concat(fine_rows, ignore_index=True)
    fine.round(3).to_csv(RES / "sensitivity_load_fine.csv", index=False)

    # 2c) 決まった目標を満たす最少の人数（5分以上待つ人5%未満／平均の待ち0.5分未満）
    tgt = []
    for ph, g in loads.groupby("per_hour"):
        aa = float(g.load.iloc[0])
        c5 = int(g[g.share_ge5 < 0.05].staff.min()); c05 = int(g[g.mean_wait < 0.5].staff.min())
        tgt.append({"per_hour": int(ph), "load": aa, "staff_share5_lt5pct": c5, "staff_mean_lt0_5": c05,
                    "extra_mean_lt0_5": round(c05 - aa, 2), "util_mean_lt0_5": round(aa / c05, 3)})

    # 3) 確かめ：会計時間のばらつき（ばらつきの係数 0.5・1・1.5）
    cv_rows = []
    for cv in [0.5, 1.0, 1.5]:
        g = summarize(run(rng, 120, base_cs, 100, cv))
        g["cv"] = cv
        cv_rows.append(g)
    cvs = pd.concat(cv_rows, ignore_index=True)
    cvs.round(3).to_csv(RES / "sensitivity_cv.csv", index=False)

    # まとめ：「大きい減り」の最後の人数（線を0.5・1・2分に変える）
    def lb_table(frame, key):
        out = []
        for v, g in frame.groupby(key, sort=False):
            g = g.sort_values("staff").reset_index(drop=True)
            row = {key: v}
            for thr in [0.5, 1.0, 2.0]:
                lb = last_big(g, thr)
                row[f"last_big_{thr}"] = lb
            if "load" in g:
                row["load"] = float(g.load.iloc[0])
                lb1 = row["last_big_1.0"]
                row["last_big_1.0_extra"] = round(lb1 - row["load"], 2)
                row["last_big_1.0_util"] = round(row["load"] / lb1, 3)
            out.append(row)
        return out

    out = {"setting": {"day_min": DAY, "service_mean_min": SVC, "big_drop_min": BIG,
                       "base_per_hour": 120, "base_load": a, "base_days": 200},
           "base": base.round(3).to_dict("records"),
           "base_last_big": {f"thr_{t}": last_big(base, t) for t in [0.5, 1.0, 2.0]},
           "base_drop_share": {int(r.staff): round(float(r.drop_from_prev / base.mean_wait.iloc[0]), 4)
                               for r in base.itertuples() if not np.isnan(r.drop_from_prev)},
           "load_last_big": lb_table(loads, "per_hour"),
           "load_fine_last_big": lb_table(fine, "per_hour"),
           "target_staff": tgt,
           "cv_last_big": lb_table(cvs, "cv"),
           "cv_wait": {str(cv): {int(r.staff): round(float(r.mean_wait), 3) for r in g.itertuples()}
                       for cv, g in cvs.groupby("cv")},
           "one_day": {"n": int(len(one)), **{f"mean_wait_staff{c}": round(float(one[f"wait_staff{c}"].mean()), 3)
                                              for c in [5, 6, 7]},
                       **{f"max_wait_staff{c}": round(float(one[f"wait_staff{c}"].max()), 3) for c in [5, 6, 7]}}}
    json.dump(out, open(RES / "a882_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：基本の人数ごとの平均の待ち
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    col = [GRAY if c == 4 else (ORANGE if c == 5 else BLUE) for c in base.staff]
    labels = [f"{c}人" if np.isnan(d) else f"{c}人\n（−{d:.2f}）" for c, d in zip(base.staff, base.drop_from_prev)]
    ax.bar(range(len(base)), base.mean_wait, color=col)
    ax.set_xticks(range(len(base))); ax.set_xticklabels(labels, fontsize=9.5)
    for i, r in base.iterrows():
        ax.text(i, r.mean_wait + 0.25, f"{r.mean_wait:.2f}分", ha="center", fontsize=9)
    ax.set_ylim(0, base.mean_wait.max() * 1.12)
    ax.set_ylabel("平均の待ち（分、200日の平均）")
    ax.set_xlabel("レジの人数（括弧は、1人足して減った分）")
    b5, b6 = base.set_index("staff").loc[5], base.set_index("staff").loc[6]
    ax.set_title(f"仕事量レジ4台分：5人目で{b5.drop_from_prev:.1f}分減り、6人目は{b6.drop_from_prev:.2f}分、7人目から0.2分未満",
                 fontsize=12)
    save(fig, "a882_base.png", SRC, y=-0.07)

    # 図2：店の大きさごとの「1人足した減り」（横軸：仕事量を超えた人数）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cols = [GRAY, LIGHT, BLUE, ORANGE, GREEN]
    for (ph, g), cl in zip(loads.groupby("per_hour"), cols):
        g = g.dropna(subset=["drop_from_prev"])
        g = g[(g.extra_staff > 0) & (g.drop_from_prev > 0.0005)]
        ax.plot(g.extra_staff, g.drop_from_prev, "o-", color=cl, ms=4,
                label=f"1時間{ph}人（{ph / 60 * SVC:.0f}台分）")
    ax.axhline(BIG, color=INK, lw=.8, ls="--"); ax.text(6.3, BIG * 1.15, "1分", fontsize=9)
    ax.set_yscale("log"); ax.set_xlabel("足したあとの人数 − 仕事量（レジ何台分か）")
    ax.set_ylabel("1人足した減り（分、対数の目盛り）")
    ax.legend(frameon=False, fontsize=8.5)
    d2 = loads[np.isclose(loads.extra_staff, 2)].drop_from_prev
    ax.set_title(f"仕事量を超えた1人目は大きく減り、2人目は{d2.min():.1f}〜{d2.max():.1f}分、3人目から小さい")
    save(fig, "a882_load.png", SRC)

    # 図3：会計時間のばらつきごとの平均の待ち
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for (cv, g), cl in zip(cvs.groupby("cv"), [LIGHT, BLUE, ORANGE]):
        g = g[g.staff >= 5]
        ax.plot(g.staff, g.mean_wait, "o-", color=cl, label=f"ばらつきの係数 {cv}")
    ax.set_xlabel("レジの人数"); ax.set_ylabel("平均の待ち（分）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("会計のばらつきが大きいほど待ちは長く、6人目の減りも1分を超えた")
    save(fig, "a882_cv.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
