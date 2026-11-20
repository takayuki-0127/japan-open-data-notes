"""883 開店直後の行列は、何分で解消するのか？（架空のデータ）

架空のパン屋。開店前に客が並ぶ（人数はポアソン分布、基本は平均60人）。
開店後も客はでたらめな間隔で来る（基本は1分に1.0人、1日中同じ勢い）。
レジは基本3台、1人の会計は平均2分（ガンマ分布、ばらつきの係数は基本1）。
客は1列に並び、空いたレジに来た順に進む。
「解消」＝会計を待つ人（会計中の人を除く）が初めて0人になった時刻（開店からの分）。
見えている行列の人数÷1分に会計できる人数で読む「そのままの見込み」と、
開店後に来る客を差し引いた「余力で割る見込み」（行列÷（会計できる速さ−来る速さ））と比べる。
"""
import json, time
from heapq import heapreplace
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 883
SRC = "架空のパン屋の開店直後（作成者が乱数で作成、seed 883）"
HORIZON = 480.0   # 開店から8時間まで見る


def make_day(rng, q0_mean, lam, cv, svc, horizon=HORIZON):
    q0 = rng.poisson(q0_mean)
    n = rng.poisson(lam * horizon)
    arr = np.concatenate([np.zeros(q0), np.sort(rng.uniform(0, horizon, n))])
    k = 1.0 / cv ** 2
    s = rng.gamma(k, svc / k, len(arr))
    return q0, arr, s


def starts(arr, s, c):
    free = [0.0] * c
    st = np.empty(len(arr))
    for i, (a, d) in enumerate(zip(arr.tolist(), s.tolist())):
        f = free[0]
        t = a if a > f else f
        st[i] = t
        heapreplace(free, t + d)
    return st


def clear_times(arr, st, wait_line=5.0):
    """A：会計待ちの人が初めて0になった時刻、B：来た人の待ちが初めて wait_line 分未満になった時刻"""
    n = len(arr)
    if n == 0:
        return 0.0, 0.0
    nxt = np.append(arr[1:], np.inf)
    ok = np.where(nxt > st)[0]
    a_t = float(st[ok[0]]) if len(ok) else np.nan
    if a_t > HORIZON:
        a_t = np.nan
    w = st - arr
    okb = np.where((w < wait_line) & (arr > 0))[0]
    b_t = float(arr[okb[0]]) if len(okb) else np.nan
    if arr[0] > 0:   # 開店前に誰も並んでいない
        a_t, b_t = 0.0, 0.0
    return a_t, b_t


def run(rng, n_days, q0_mean=60, lam=1.0, c=3, cv=1.0, svc=2.0):
    rows = []
    for d in range(n_days):
        q0, arr, s = make_day(rng, q0_mean, lam, cv, svc)
        st = starts(arr, s, c)
        a_t, b_t = clear_times(arr, st)
        rows.append({"day": d, "q0": q0, "clear_min": a_t, "wait_lt5_min": b_t,
                     "naive_min": q0 / (c / svc), "margin_min": q0 / (c / svc - lam) if c / svc > lam else np.inf})
    return pd.DataFrame(rows)


def summ(df, extra):
    nc = float(df.clear_min.isna().mean())
    c = df.clear_min.fillna(HORIZON + 1)   # 8時間で解消しない日は「8時間より後」として順位だけ数える

    def q(x, p):
        v = float(x.quantile(p, interpolation="lower"))
        return round(v, 2) if v <= HORIZON else None   # None＝8時間より後
    r = {**extra, "days": int(len(df)), "not_cleared_8h": round(nc, 4),
         "clear_mean": round(float(c.mean()), 2) if nc == 0 else None, "clear_median": q(c, .5),
         "clear_p10": q(c, .1), "clear_p90": q(c, .9),
         "wait_lt5_median": q(df.wait_lt5_min.fillna(HORIZON + 1), .5),
         "naive_mean": round(float(df.naive_min.mean()), 2),
         "margin_formula": round(float(extra["q0_mean"] / (extra["c"] / extra["svc"] - extra["lam"])), 2)
         if extra["c"] / extra["svc"] > extra["lam"] else None,
         "ratio_median_to_naive": round(float((c / df.naive_min).median()), 3) if nc < 0.5 else None}
    return r


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base_set = {"q0_mean": 60, "lam": 1.0, "c": 3, "cv": 1.0, "svc": 2.0}

    # 1) 基本：2,000日
    base = run(rng, 2000, **{k: v for k, v in base_set.items()})
    base.round(3).to_csv(RES / "base_days.csv", index=False)
    b = summ(base, base_set)
    # 見えている行列とほぼ同じ60人前後（55〜65人）の日だけで見た幅
    near = base[base.q0.between(55, 65)]
    b["q0_55_65_days"] = int(len(near))
    b["q0_55_65_clear_p10"] = round(float(near.clear_min.quantile(.1)), 2)
    b["q0_55_65_clear_p90"] = round(float(near.clear_min.quantile(.9)), 2)
    b["clear_le_naive_share"] = round(float((base.clear_min <= base.naive_min).mean()), 4)
    b["clear_gt_2x_naive_share"] = round(float((base.clear_min > 2 * base.naive_min).mean()), 4)

    # 1回分のデータ（行列の人数の動き）
    r1 = np.random.default_rng(SEED + 1)
    q0, arr, s = make_day(r1, 60, 1.0, 1.0, 2.0)
    st = starts(arr, s, 3)
    one = pd.DataFrame({"customer_id": np.arange(1, len(arr) + 1), "arrival_min": arr, "start_min": st,
                        "service_min": s, "wait_min": st - arr, "in_line_at_open": arr == 0})
    one.to_csv(DATA / "one_day_customers.csv", index=False, float_format="%.3f")
    one_a, one_b = clear_times(arr, st)
    grid = np.arange(0, 241, 1.0)
    qlen = np.array([int(((arr <= t) & (st > t)).sum()) for t in grid])
    b_one = {"q0": int(q0), "clear_min": round(one_a, 2), "wait_lt5_min": round(one_b, 2),
             "naive_min": round(q0 / 1.5, 2), "margin_min": round(q0 / 0.5, 2),
             "last_of_opening_line_wait": round(float((st - arr)[q0 - 1]), 2)}

    # 2) 確かめ：開店後に来る速さ（1分に0.5〜1.4人）
    rows = []
    for lam in [0.5, 0.75, 1.0, 1.25, 1.4]:
        st_ = dict(base_set, lam=lam)
        rows.append(summ(run(rng, 500, **st_), st_))
    # 3) 確かめ：開店前の行列の人数・レジの台数・会計のばらつき
    for q in [30, 90]:
        st_ = dict(base_set, q0_mean=q)
        rows.append(summ(run(rng, 500, **st_), st_))
    for c in [4]:
        st_ = dict(base_set, c=c)
        rows.append(summ(run(rng, 500, **st_), st_))
    for cv in [0.5, 1.5]:
        st_ = dict(base_set, cv=cv)
        rows.append(summ(run(rng, 500, **st_), st_))
    sens = pd.DataFrame(rows)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"setting": dict(base_set, days=2000, horizon_min=HORIZON,
                           clear_def="会計待ちの人が初めて0人になった時刻",
                           wait_def="開店後に来た人の待ちが初めて5分未満になった時刻"),
           "base": b, "one_day": b_one, "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a883_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1日分の行列の人数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(grid, qlen, color=BLUE, lw=1.5)
    ax.axvline(b_one["naive_min"], color=GRAY, ls="--", lw=1)
    ax.text(b_one["naive_min"] + 2, qlen.max() * 0.92, f"行列÷会計の速さ\n{b_one['naive_min']:.0f}分", fontsize=9, color=INK)
    ax.axvline(b_one["margin_min"], color=ORANGE, ls="--", lw=1)
    ax.text(b_one["margin_min"] + 2, qlen.max() * 0.72, f"行列÷（会計の速さ−来る速さ）\n{b_one['margin_min']:.0f}分",
            fontsize=9, color=ORANGE)
    ax.axvline(one_a, color=INK, lw=1)
    ax.text(one_a + 2, qlen.max() * 0.45, f"この日の解消\n{one_a:.0f}分", fontsize=9, color=INK)
    ax.set_xlabel("開店からの時間（分）"); ax.set_ylabel("会計を待つ人（会計中を除く）")
    ax.set_xlim(0, 240); ax.set_ylim(0, None)
    ax.set_title(f"開店前に{q0}人並んだ日：行列は、開店後に来る客の分だけ長く残る")
    save(fig, "a883_one_day.png", SRC)

    # 図2：基本2,000日の解消までの時間
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    v = base.clear_min.dropna()
    ax.hist(v, bins=np.arange(0, v.max() + 10, 10), color=BLUE, alpha=.8)
    ax.axvline(b["naive_mean"], color=GRAY, ls="--", label=f"行列÷会計の速さ（平均{b['naive_mean']:.0f}分）")
    ax.axvline(b["margin_formula"], color=ORANGE, ls="--", label=f"余力で割る式（{b['margin_formula']:.0f}分）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_xlabel("開店から行列が解消するまで（分）"); ax.set_ylabel("日数")
    ax.set_title(f"解消までの中央値は{b['clear_median']:.0f}分、1割の日は{b['clear_p90']:.0f}分を超えた（2,000日）")
    save(fig, "a883_hist.png", SRC)

    # 図3：来る速さごとの解消までの時間
    s5 = sens[(sens.q0_mean == 60) & (sens.c == 3) & (sens.cv == 1.0)].sort_values("lam")
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    s5 = s5.fillna(HORIZON)
    ax.fill_between(s5.lam, s5.clear_p10, s5.clear_p90, color=LIGHT, alpha=.6, label="10〜90%の日")
    ax.plot(s5.lam, s5.clear_median, "o-", color=BLUE, label="中央値")
    lam_g = np.linspace(0.5, 1.4, 50)
    ax.plot(lam_g, 60 / (1.5 - lam_g), color=ORANGE, ls="--", label="余力で割る式")
    ax.axhline(40, color=GRAY, ls=":", label="行列÷会計の速さ（40分）")
    nc14 = float(s5[s5.lam == 1.4].not_cleared_8h.iloc[0])
    ax.text(1.12, 360, f"1.4人では{nc14 * 100:.0f}%の日が\n8時間で解消しなかった", fontsize=8.5, ha="center", color=INK)
    ax.set_ylim(0, HORIZON); ax.set_xlabel("開店後に来る客（1分あたり、レジ3台で1.5人まで会計できる）")
    ax.set_ylabel("解消まで（分）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("来る速さが会計の速さに近いほど、解消は遅れ、日による幅も広がる")
    save(fig, "a883_by_rate.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
