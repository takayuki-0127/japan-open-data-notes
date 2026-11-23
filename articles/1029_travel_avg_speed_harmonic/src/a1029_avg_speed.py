"""1029 行きは時速40km、帰りは60kmなら、平均は50kmなのか？（架空のデータ）

(1) 行き40km/h・帰り v km/h の往復で、速さの単純平均と、合計距離÷合計時間を式で並べる。
(2) 架空の配送車の300日。片道15km を0.5kmずつ30区間に分け、区間ごとの速さを作成者が置く
    （道の種類ごとの速さ×行き帰りの混み×日ごとの振れ×区間ごとの振れ）。
    1日の平均の速さを、いくつかの数え方で出し、合計距離÷合計時間と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1029
SRC = "架空の配送車の記録（作成者が乱数で作成、seed 1029）"
N_DAY = 300
SEG_KM = 0.5
N_SEG = 30                      # 片道 30区間 × 0.5km = 15km
ROAD = ["住宅地", "一般道", "幹線"]
BASE_V = {"住宅地": 20.0, "一般道": 32.0, "幹線": 50.0}   # 中央値（km/h）
MIX = {"基本": (6, 12, 12), "全部一般道": (0, 30, 0), "住宅地多め": (15, 9, 6)}
OUT_F, BACK_F = 0.8, 1.0        # 行き（朝）は混んで0.8倍、帰りは1.0倍
DAY_SD = 0.12                   # 日ごとの振れ（対数の標準偏差）
SEG_SD = 0.35                   # 区間ごとの振れ（対数の標準偏差、基本）
SAMPLE_SEC = 10                 # 時間ごとの記録の間隔（秒）


def make_days(rng, n_day=N_DAY, seg_sd=SEG_SD, mix="基本", out_f=OUT_F, back_f=BACK_F):
    cnt = MIX[mix]
    road = np.repeat(np.arange(3), cnt)                     # 片道の区間の道の種類
    road2 = np.concatenate([road, road[::-1]])               # 行き→帰り（帰りは逆順）
    dirf = np.r_[np.full(N_SEG, out_f), np.full(N_SEG, back_f)]
    base = np.array([BASE_V[r] for r in ROAD])[road2] * dirf
    dayf = np.exp(rng.normal(0, DAY_SD, n_day))[:, None]
    noise = np.exp(rng.normal(0, seg_sd, (n_day, 2 * N_SEG)))
    v = np.clip(base[None, :] * dayf * noise, 3, 90)           # km/h
    t = SEG_KM / v * 60                                        # 分
    return v, t, road2


def day_methods(v, t, road2):
    """1日ごとの平均の速さ（km/h）を数え方ごとに"""
    total_km = SEG_KM * v.shape[1]
    T = t.sum(1)
    true = total_km / (T / 60)
    seg_mean = v.mean(1)                                       # 0.5kmごとの速さの平均
    # 10秒ごとの記録の平均（時間ごとの記録）
    ts = []
    for vi, ti in zip(v, t):
        c = np.cumsum(ti) * 60
        pts = np.arange(SAMPLE_SEC / 2, c[-1], SAMPLE_SEC)
        ts.append(vi[np.searchsorted(c, pts)].mean())
    ts = np.array(ts)
    h = v.shape[1] // 2
    v_out = SEG_KM * h / (t[:, :h].sum(1) / 60)
    v_back = SEG_KM * h / (t[:, h:].sum(1) / 60)
    dir_mean = (v_out + v_back) / 2
    tv = []
    for r in np.unique(road2):
        m = road2 == r
        tv.append(SEG_KM * m.sum() / (t[:, m].sum(1) / 60))
    type_mean = np.mean(tv, axis=0)
    return {"true": true, "seg": seg_mean, "time10s": ts, "dir": dir_mean, "type": type_mean,
            "T": T, "v_out": v_out, "v_back": v_back}


NAMES = [("pooled", "合計距離÷合計時間（300日まとめて）"),
         ("true", "1日ごとの合計距離÷合計時間を、300日で平均"),
         ("time10s", "10秒ごとの記録の速さの平均"),
         ("dir", "行きの速さと帰りの速さの平均"),
         ("type", "道の種類（3つ）ごとの速さの平均"),
         ("seg", "0.5kmごとの記録の速さの平均")]


def summarize(m, total_km):
    pooled = total_km * len(m["T"]) / (m["T"].sum() / 60)
    actual = float(m["T"].mean())
    rows = []
    for k, name in NAMES:
        sp = pooled if k == "pooled" else float(m[k].mean())
        plan = total_km / sp * 60
        rows.append({"key": k, "method": name, "speed_kmh": round(sp, 2),
                     "vs_pooled_pct": round((sp / pooled - 1) * 100, 2),
                     "plan_min_30km": round(plan, 2), "actual_mean_min": round(actual, 2),
                     "plan_error_pct": round((plan / actual - 1) * 100, 2)})
    return pd.DataFrame(rows), pooled, actual


def main():
    rng = np.random.default_rng(SEED)

    # (1) 往復の式
    pairs = []
    for v2 in [20, 30, 40, 50, 60, 80, 100]:
        d = 12.0
        hm = 2 * d / (d / 40 + d / v2)
        am = (40 + v2) / 2
        pairs.append({"go_kmh": 40, "back_kmh": v2, "simple_mean": am, "same_distance": round(hm, 2),
                      "same_time": am, "time_error_pct_if_simple": round((hm / am - 1) * 100, 2),
                      "go_min_12km": round(d / 40 * 60, 2), "back_min_12km": round(d / v2 * 60, 2),
                      "round_trip_min_12km": round((d / 40 + d / v2) * 60, 2),
                      "plan_min_if_simple": round(2 * d / am * 60, 2)})
    pairs = pd.DataFrame(pairs)
    pairs.to_csv(RES / "pairs.csv", index=False)

    # (2) 架空の配送車の300日
    v, t, road2 = make_days(rng)
    m = day_methods(v, t, road2)
    total_km = SEG_KM * v.shape[1]
    meth, pooled, actual = summarize(m, total_km)
    meth.to_csv(RES / "methods.csv", index=False)

    seg_rows = []
    for d in range(N_DAY):
        for j in range(v.shape[1]):
            seg_rows.append((d + 1, "行き" if j < N_SEG else "帰り", j % N_SEG + 1, ROAD[road2[j]], SEG_KM,
                             round(float(v[d, j]), 3), round(float(t[d, j]), 4)))
    pd.DataFrame(seg_rows, columns=["day", "direction", "seg_no", "road", "km", "speed_kmh", "minutes"]) \
        .to_csv(DATA / "segments.csv", index=False)

    road_sum = []
    for r in range(3):
        mk = road2 == r
        road_sum.append({"road": ROAD[r], "km_per_day": float(SEG_KM * mk.sum()),
                         "share_of_distance_pct": round(mk.mean() * 100, 2),
                         "share_of_time_pct": round(float(t[:, mk].sum() / t.sum() * 100), 2),
                         "speed_kmh": round(float(SEG_KM * mk.sum() * N_DAY / (t[:, mk].sum() / 60)), 2)})
    day_gap = (m["seg"] / m["true"] - 1) * 100

    # 速い区間・遅い区間の、距離と時間の割合
    q = np.quantile(v, [1 / 3, 2 / 3])
    fast = v >= q[1]; slow = v < q[0]
    dist_time = {"slow_third_share_distance_pct": round(float(slow.mean() * 100), 2),
                 "slow_third_share_time_pct": round(float(t[slow].sum() / t.sum() * 100), 2),
                 "fast_third_share_distance_pct": round(float(fast.mean() * 100), 2),
                 "fast_third_share_time_pct": round(float(t[fast].sum() / t.sum() * 100), 2)}

    # (3) 確かめ：区間ごとの振れ × 道の混ざり方（各300日を10回）
    rob = []
    for mix in MIX:
        for sd in [0.1, 0.2, 0.35, 0.5]:
            gs, es, gt, gd = [], [], [], []
            for r in range(10):
                g = np.random.default_rng(SEED * 100 + r + int(sd * 100) * 7 + list(MIX).index(mix) * 1000)
                vv, tt, rr = make_days(g, seg_sd=sd, mix=mix)
                mm = day_methods(vv, tt, rr)
                s, _, _ = summarize(mm, SEG_KM * vv.shape[1])
                s = s.set_index("key")
                gs.append(s.loc["seg", "vs_pooled_pct"]); es.append(s.loc["seg", "plan_error_pct"])
                gt.append(s.loc["type", "vs_pooled_pct"]); gd.append(s.loc["dir", "vs_pooled_pct"])
            rob.append({"mix": mix, "seg_sd": sd, "seg_vs_pooled_pct": round(float(np.mean(gs)), 2),
                        "seg_plan_error_pct": round(float(np.mean(es)), 2),
                        "type_vs_pooled_pct": round(float(np.mean(gt)), 2),
                        "dir_vs_pooled_pct": round(float(np.mean(gd)), 2)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # (4) 式との照らし合わせ：全部一般道・行き帰りの混みが同じなら、0.5kmごとの平均÷本当 ≒ exp(σ²)
    chk = []
    for sd in [0.1, 0.2, 0.35, 0.5]:
        g = np.random.default_rng(SEED * 7 + int(sd * 100))
        vv, tt, rr = make_days(g, n_day=3000, seg_sd=sd, mix="全部一般道", out_f=1.0, back_f=1.0)
        ratio = float((vv.mean(1) / (SEG_KM * vv.shape[1] / (tt.sum(1) / 60))).mean())
        chk.append({"seg_sd": sd, "sim_ratio": round(ratio, 4), "formula_exp_sd2": round(float(np.exp(sd ** 2)), 4)})

    out = {"pairs": pairs.to_dict("records"),
           "fleet_300days": {"km_per_day": total_km, "pooled_speed_kmh": round(pooled, 2),
                             "actual_mean_min": round(actual, 2),
                             "methods": meth.to_dict("records"),
                             "road": road_sum,
                             "go_speed_pooled_kmh": round(float(15 * N_DAY / (t[:, :N_SEG].sum() / 60)), 2),
                             "back_speed_pooled_kmh": round(float(15 * N_DAY / (t[:, N_SEG:].sum() / 60)), 2),
                             "seg_vs_true_by_day_pct": {"min": round(float(day_gap.min()), 2),
                                                        "p10": round(float(np.quantile(day_gap, .1)), 2),
                                                        "median": round(float(np.median(day_gap)), 2),
                                                        "p90": round(float(np.quantile(day_gap, .9)), 2),
                                                        "max": round(float(day_gap.max()), 2),
                                                        "share_days_positive_pct": round(float((day_gap > 0).mean() * 100), 2)},
                             "slow_fast_thirds": dist_time},
           "robustness": rob.to_dict("records"),
           "robustness_range": {"seg_vs_pooled_pct_min": float(rob.seg_vs_pooled_pct.min()),
                                "seg_vs_pooled_pct_max": float(rob.seg_vs_pooled_pct.max()),
                                "seg_plan_error_pct_min": float(rob.seg_plan_error_pct.min()),
                                "seg_plan_error_pct_max": float(rob.seg_plan_error_pct.max())},
           "formula_check_all_ordinary_road": chk}
    json.dump(out, open(RES / "a1029_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：行き40km/h、帰りの速さを変えたとき
    vv2 = np.linspace(20, 100, 81)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(vv2, (40 + vv2) / 2, color=GRAY, lw=2, label="速さの単純平均（同じ時間ずつ走ったときの平均）")
    ax.plot(vv2, 2 / (1 / 40 + 1 / vv2), color=BLUE, lw=2.4, label="同じ距離を往復したときの平均（合計距離÷合計時間）")
    ax.scatter([60, 60], [50, 48], color=[GRAY, BLUE], zorder=3)
    ax.annotate("帰り60km/h：単純平均50", (60, 50), xytext=(63, 55.5), fontsize=9, color=INK,
                arrowprops=dict(arrowstyle="-", color=GRAY, lw=.8))
    ax.annotate("合計距離÷合計時間48", (60, 48), xytext=(66, 43), fontsize=9, color=BLUE,
                arrowprops=dict(arrowstyle="-", color=BLUE, lw=.8))
    ax.set_xlabel("帰りの速さ（km/h）、行きは40km/h"); ax.set_ylabel("往復の平均の速さ（km/h）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("同じ距離の往復では、平均の速さは単純平均より遅い（式どおり）")
    save(fig, "a1029_pairs.png", "式による計算（作成者が作成）")

    # 図2：数え方ごとの平均の速さ（300日）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    s = meth.iloc[::-1]
    col = [ORANGE if k in ("seg", "type") else (LIGHT if k in ("dir",) else BLUE) for k in s.key]
    ax.barh(s.method, s.speed_kmh, color=col)
    for i, (sp, g) in enumerate(zip(s.speed_kmh, s.vs_pooled_pct)):
        ax.text(sp + 0.2, i, f"{sp:.2f}km/h（{g:+.2f}%）", va="center", fontsize=8.5)
    ax.axvline(pooled, color=INK, lw=.8, ls="--")
    ax.set_xlim(0, max(s.speed_kmh) * 1.3)
    ax.set_xlabel("1日（往復30km）の平均の速さ（km/h、300日）。括弧は合計距離÷合計時間との差")
    ax.set_title("0.5kmごとの記録を平均すると、速く出る")
    save(fig, "a1029_methods.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for mix, c in zip(MIX, [BLUE, GRAY, ORANGE]):
        r = rob[rob.mix == mix]
        ax.plot(r.seg_sd, r.seg_vs_pooled_pct, marker="o", color=c, lw=2, label=f"0.5kmごとの平均（{mix}）")
    xs = np.linspace(0.1, 0.5, 41)
    ax.plot(xs, (np.exp(xs ** 2) - 1) * 100, color=INK, lw=1, ls="--", label="式 exp(σ²)−1（一般道だけ・行き帰り同じ混み）")
    ax.set_xlabel("区間ごとの速さの振れ σ（対数の標準偏差）"); ax.set_ylabel("合計距離÷合計時間より速く出る割合（%）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("区間ごとの速さの振れが大きいほど、0.5kmごとの平均は速く出る")
    save(fig, "a1029_robust.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
