"""1296 車の荷台の半分を超える大きな荷物がいくつかまざると、要る台数と積載率はどう動くのか？（架空のデータ）

架空の通販の1日の発送。荷台の容量を1として、荷物の大きさは容量に対する割合で置く（形は考えず、大きさだけで詰める）。
1日の荷物の大きさの合計は 20 前後（車20台分）にそろえる。
大きな荷物（荷台の半分を超えるもの）を m 個まぜ、残りを小さな荷物で埋める（m を増やしても合計はほぼ同じ）。
詰め方：大きい順に並べてから、入る車のうちすきまがいちばん小さい車に積む（入らなければ新しい車）。
大きな荷物どうしは同じ車に載らないので、台数は m 台を下回らない（作りどおり）。
すべてシミュレーション。
"""
import json
import math
import time
from bisect import bisect_left, insort
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1296
SRC = "架空の通販の発送の積み込みのシミュレーション（作成者が乱数で作成、seed 1296）"
CAP = 1_000_000                      # 荷台の容量（整数の単位で計算する）
V_TARGET = 20.0                      # 1日の大きさの合計（車何台分か）
M_LIST = list(range(0, 25))
DAYS = 200
GRID_DAYS = 60
BASE = {"big_lo": 0.5, "big_hi": 0.8, "small_median": 0.04}
SMALL_SIGMA = 0.7
SMALL_MAX = 0.5
BIG_RANGES = [(0.5, 0.6), (0.5, 0.8), (0.7, 0.95)]
SMALL_MEDIANS = [0.02, 0.04, 0.10]
LAMS = [5, 10, 15, 18, 20, 22, 25]     # 大きな荷物の数が日ごとに散らばるとき（1日の平均）


def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def small_item(rng, med):
    while True:
        x = med * math.exp(rng.normal(0, SMALL_SIGMA))
        if x <= SMALL_MAX:
            return x


def make_day(rng, m, big_lo, big_hi, med):
    big = []
    for _ in range(m):
        x = rng.uniform(big_lo, big_hi)
        while x <= 0.5:
            x = rng.uniform(big_lo, big_hi)
        big.append(x)
    items = list(big)
    total = sum(big)
    while True:
        x = small_item(rng, med)
        if total + x > V_TARGET:
            break
        items.append(x); total += x
    sizes = [max(1, int(round(x * CAP))) for x in items]
    return sizes


def pack(sizes):
    """大きい順に並べ、入る車のうちすきまのいちばん小さい車に積む。台数を返す"""
    res = []                          # 車ごとの残りの容量（小さい順）
    for s in sorted(sizes, reverse=True):
        i = bisect_left(res, s)
        if i < len(res):
            r = res.pop(i) - s
        else:
            r = CAP - s
        insort(res, r)
    return len(res)


def run(rng, days, big_lo, big_hi, med, keep=False):
    rows = []
    for m in M_LIST:
        for d in range(days):
            sizes = make_day(rng, m, big_lo, big_hi, med)
            vol = sum(sizes) / CAP
            trucks = pack(sizes)
            est_v = math.ceil(sum(sizes) / CAP)
            est_lb = max(est_v, m)
            rows.append({"big_items": m, "day": d, "items": len(sizes), "volume": vol, "trucks": trucks,
                         "est_volume": est_v, "est_volume_or_big": est_lb, "load": vol / trucks})
    return pd.DataFrame(rows)


def run_vary(rng, days, lam, big_lo, big_hi, med):
    rows = []
    for d in range(days):
        m = int(rng.poisson(lam))
        sizes = make_day(rng, m, big_lo, big_hi, med)
        vol = sum(sizes) / CAP
        trucks = pack(sizes)
        rows.append({"lam": lam, "day": d, "big_items": m, "volume": vol, "trucks": trucks,
                     "est_volume": math.ceil(sum(sizes) / CAP), "est_volume_or_big": max(math.ceil(sum(sizes) / CAP), m)})
    return pd.DataFrame(rows)


def vary_summary(df, lam):
    plan = max(math.ceil(V_TARGET), lam)      # 平均の数で見込んだ台数
    return {"lam": lam, "plan_by_mean": plan, "trucks_mean": df.trucks.mean(),
            "trucks_minus_plan": df.trucks.mean() - plan,
            "share_days_over_plan": (df.trucks > plan).mean(),
            "est_volume_or_big_mean": df.est_volume_or_big.mean(),
            "big_items_mean": df.big_items.mean(),
            "load_total": df.volume.sum() / df.trucks.sum()}


def by_m(df):
    g = df.groupby("big_items")
    out = pd.DataFrame({
        "volume_mean": g.volume.mean(),
        "items_mean": g["items"].mean(),
        "trucks_mean": g.trucks.mean(),
        "est_volume_mean": g.est_volume.mean(),
        "est_volume_or_big_mean": g.est_volume_or_big.mean(),
        "trucks_minus_est_volume": g.apply(lambda x: (x.trucks - x.est_volume).mean()),
        "trucks_minus_est_volume_or_big": g.apply(lambda x: (x.trucks - x.est_volume_or_big).mean()),
        "share_days_over_est_volume_or_big": g.apply(lambda x: (x.trucks > x.est_volume_or_big).mean()),
        "load_total": g.apply(lambda x: x.volume.sum() / x.trucks.sum()),
    }).reset_index()
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    base = run(rng, DAYS, BASE["big_lo"], BASE["big_hi"], BASE["small_median"])
    base.to_csv(DATA / "days_base.csv", index=False, float_format="%.6f")
    bm = by_m(base)
    bm.to_csv(RES / "base_by_big_items.csv", index=False, float_format="%.4f")

    grid_rows = []
    grid_by = []
    for gi, (lo, hi) in enumerate(BIG_RANGES):
        for si, med in enumerate(SMALL_MEDIANS):
            g = run(np.random.default_rng(SEED * 100 + gi * 10 + si), GRID_DAYS, lo, hi, med)
            b = by_m(g)
            b.insert(0, "small_median", med); b.insert(0, "big_range", f"{lo}-{hi}")
            grid_by.append(b)
            r0 = b[b.big_items == 0].iloc[0]; r10 = b[b.big_items == 10].iloc[0]
            r20 = b[b.big_items == 20].iloc[0]; r24 = b[b.big_items == 24].iloc[0]
            imax = b.trucks_minus_est_volume_or_big.idxmax()
            grid_rows.append({"big_range": f"{lo}-{hi}", "small_median": med,
                              "trucks_m0": r0.trucks_mean, "trucks_m10": r10.trucks_mean,
                              "trucks_m20": r20.trucks_mean, "trucks_m24": r24.trucks_mean,
                              "load_m0": r0.load_total, "load_m10": r10.load_total,
                              "load_m20": r20.load_total, "load_m24": r24.load_total,
                              "over_lb_max": b.trucks_minus_est_volume_or_big.max(),
                              "over_lb_max_at_m": int(b.loc[imax, "big_items"]),
                              "over_lb_m20": r20.trucks_minus_est_volume_or_big,
                              "share_days_over_lb_m20": r20.share_days_over_est_volume_or_big})
            pg = run_vary(np.random.default_rng(SEED * 1000 + gi * 10 + si), GRID_DAYS, 20, lo, hi, med)
            ps = vary_summary(pg, 20)
            grid_rows[-1].update({"vary20_trucks_mean": ps["trucks_mean"],
                                  "vary20_minus_plan": ps["trucks_minus_plan"],
                                  "vary20_load": ps["load_total"]})
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False, float_format="%.4f")
    gb = pd.concat(grid_by)
    gb.to_csv(RES / "grid_by_big_items.csv", index=False, float_format="%.4f")

    prng = np.random.default_rng(SEED + 1)
    pois = [vary_summary(run_vary(prng, DAYS, lam, BASE["big_lo"], BASE["big_hi"], BASE["small_median"]), lam)
            for lam in LAMS]
    pois = pd.DataFrame(pois)
    pois.to_csv(RES / "vary_by_mean.csv", index=False, float_format="%.4f")

    def row(m):
        r = bm[bm.big_items == m].iloc[0]
        return {k: (float(v) if not isinstance(v, (int, np.integer)) else int(v)) for k, v in r.items()}

    imax = bm.trucks_minus_est_volume_or_big.idxmax()
    main_res = {
        "setting": {"volume_target": V_TARGET, "big_range": [BASE["big_lo"], BASE["big_hi"]],
                    "small_median": BASE["small_median"], "small_sigma_log": SMALL_SIGMA, "small_max": SMALL_MAX,
                    "days_per_m": DAYS, "m_list": M_LIST},
        "m0": row(0), "m10": row(10), "m16": row(16), "m20": row(20), "m24": row(24),
        "over_lb_max": float(bm.trucks_minus_est_volume_or_big.max()),
        "over_lb_max_at_m": int(bm.loc[imax, "big_items"]),
        "days_trucks_below_big_items": int((base.trucks < base.big_items).sum()),
        "vary": {str(int(r["lam"])): {k: float(v) for k, v in r.items()} for r in pois.to_dict("records")},
        "grid_range": {
            "trucks_m20_min": float(grid.trucks_m20.min()), "trucks_m20_max": float(grid.trucks_m20.max()),
            "load_m20_min": float(grid.load_m20.min()), "load_m20_max": float(grid.load_m20.max()),
            "load_m24_min": float(grid.load_m24.min()), "load_m24_max": float(grid.load_m24.max()),
            "over_lb_max_min": float(grid.over_lb_max.min()), "over_lb_max_max": float(grid.over_lb_max.max()),
            "over_lb_max_at_m_min": int(grid.over_lb_max_at_m.min()),
            "over_lb_max_at_m_max": int(grid.over_lb_max_at_m.max()),
            "trucks_m0_min": float(grid.trucks_m0.min()), "trucks_m0_max": float(grid.trucks_m0.max()),
            "volume_m24_max": float(gb[gb.big_items == 24].volume_mean.max()),
            "vary20_minus_plan_min": float(grid.vary20_minus_plan.min()),
            "vary20_minus_plan_max": float(grid.vary20_minus_plan.max()),
            "vary20_load_min": float(grid.vary20_load.min()),
            "vary20_load_max": float(grid.vary20_load.max()),
        },
    }
    with open(RES / "a1296_main.json", "w", encoding="utf-8") as f:
        json.dump(main_res, f, ensure_ascii=False, indent=1)

    # 図1：台数
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(bm.big_items, bm.trucks_mean, color=BLUE, lw=2.2, marker="o", ms=4, label="大きい順に詰めた台数（200日の平均）")
    ax.plot(bm.big_items, bm.est_volume_mean, color=GRAY, lw=1.8, ls="--", label="大きさの合計÷容量の切り上げ")
    ax.plot(bm.big_items, bm.est_volume_or_big_mean, color=ORANGE, lw=1.6, ls=":", label="切り上げと大きな荷物の数の大きいほう")
    ax.set_xlabel("荷台の半分を超える大きな荷物の数（1日、大きさの合計は約20台分）")
    ax.set_ylabel("車の台数")
    ax.set_ylim(0, 27)
    ax.set_title("大きな荷物が20個を超えると、台数は大きな荷物の数で決まる")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1296_trucks.png", SRC + "。大きな荷物は容量の0.5〜0.8、小さな荷物は中央値0.04")

    # 図2：積載率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(bm.big_items, bm.load_total * 100, color=BLUE, lw=2.2, marker="o", ms=4)
    ax.set_xlabel("荷台の半分を超える大きな荷物の数（1日）")
    ax.set_ylabel("積載率（大きさの合計÷台数×容量、%）")
    ax.set_ylim(0, 105)
    ax.set_title("積載率は、大きな荷物が約20個まではほぼ横ばい、その先で下がる")
    for m in [0, 20, 24]:
        r = bm[bm.big_items == m].iloc[0]
        ax.annotate(f"{r.load_total*100:.2f}%", (m, r.load_total * 100), textcoords="offset points",
                    xytext=(0, -16), ha="center", fontsize=9, color=INK)
    save(fig, "a1296_load.png", SRC)

    # 図3：大きな荷物の数が日ごとに散らばるとき
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    w = 0.38
    xs = np.arange(len(pois))
    ax.bar(xs - w / 2, pois.plan_by_mean, w, color=GRAY, label="平均の数で見込んだ台数")
    ax.bar(xs + w / 2, pois.trucks_mean, w, color=BLUE, label="実際の台数（200日の平均）")
    for x, r in zip(xs, pois.itertuples()):
        ax.text(x + w / 2, r.trucks_mean + 0.3, fmt(r.trucks_mean), ha="center", va="bottom", fontsize=8.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{int(l)}個" for l in pois.lam])
    ax.set_xlabel("大きな荷物の1日の平均の数（日ごとに散らばる）")
    ax.set_ylabel("車の台数")
    ax.set_ylim(0, 31)
    ax.set_title("平均が20個前後のとき、散らばりの分だけ台数が見込みを上回る")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1296_vary.png", SRC + "。大きさの合計は毎日約20台分")
    print(json.dumps(main_res, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
