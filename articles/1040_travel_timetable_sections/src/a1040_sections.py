"""1040 計画の時刻表どおりに動く割合は、区間の数でどう変わるのか？（架空のデータ）

架空のバスの路線。始発から k 区間（停留所 k か所）を走る。1区間の走る時間は、中央値3分の右に長い分布（対数正規）。
時刻表の1区間の時間は3.2分（平均より少し長い＝余裕）。早く着いたら時刻表の時刻まで待って発車する（早発しない）。
停留所に「時刻表から1分以内の遅れ」で発車したら、その停留所では定時と数える。
区間の数が増えると、終点で定時の割合・全部の停留所で定時の割合がどう変わるかを、
1区間の定時率を区間の数だけ掛けた値と比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1040
SRC = "架空のバスの路線（作成者が乱数で作成、seed 1040）"
MED = 3.0          # 1区間の走る時間の中央値（分）
SIG = 0.25         # 1区間ごとの振れ（対数の標準偏差）
SIG_C = 0.10       # その便の全区間に共通の振れ（対数の標準偏差）
SCHED = 3.2        # 時刻表の1区間の時間（分）
TOL = 1.0          # 定時とみなす遅れ（分以内）
K_MAX = 30
N_TRIP = 100000
KS = [1, 2, 3, 5, 8, 10, 15, 20, 25, 30]


def simulate(rng, n=N_TRIP, k_max=K_MAX, med=MED, sig=SIG, sig_c=SIG_C, sched=SCHED, hold=True):
    """返り値：停留所ごとの遅れ（便, 停留所1..k_max）。遅れ＝発車の時刻−時刻表の時刻"""
    common = rng.normal(0, sig_c, n)
    x = med * np.exp(common[:, None] + rng.normal(0, sig, (n, k_max)))
    delay = np.empty((n, k_max)); d = np.zeros(n)
    for i in range(k_max):
        d = d + x[:, i] - sched
        if hold:
            d = np.maximum(d, 0.0)          # 早く着いたら時刻表の時刻まで待つ
        delay[:, i] = d
    return delay, x


def by_k(delay, tol=TOL, hold=True):
    ontime = (delay <= tol) if hold else (np.abs(delay) <= tol)
    p1 = float(ontime[:, 0].mean())
    rows = []
    allok = np.cumprod(ontime, axis=1)
    for k in KS:
        rows.append({"k": k, "p_end_ontime_pct": round(float(ontime[:, k - 1].mean()) * 100, 2),
                     "p_all_stops_ontime_pct": round(float(allok[:, k - 1].mean()) * 100, 2),
                     "p_stops_avg_ontime_pct": round(float(ontime[:, :k].mean()) * 100, 2),
                     "product_p1_pow_k_pct": round(p1 ** k * 100, 2),
                     "mean_end_delay_min": round(float(delay[:, k - 1].mean()), 3),
                     "p90_end_delay_min": round(float(np.quantile(delay[:, k - 1], .9)), 3)})
    return pd.DataFrame(rows), p1


def main():
    rng = np.random.default_rng(SEED)
    delay, x = simulate(rng)
    base, p1 = by_k(delay)
    base.to_csv(RES / "by_sections_base.csv", index=False)
    mean_x = float(x.mean())
    # data：最初の2,000便の30停留所の遅れ
    dd = pd.DataFrame(np.round(delay[:2000], 3), columns=[f"stop{i+1}" for i in range(K_MAX)])
    dd.insert(0, "trip", np.arange(1, 2001))
    dd.to_csv(DATA / "trips_delay_2000.csv", index=False)

    # 確かめ：時刻表の1区間の時間・区間ごとの振れ・共通の振れ・早発の扱い
    rows = []
    def add(label, value, **kw):
        hold = kw.get("hold", True)
        dl, xx = simulate(np.random.default_rng(SEED * 100 + len(rows)), n=40000, **kw)
        t, q1 = by_k(dl, hold=hold)
        r10 = t[t.k == 10].iloc[0]; r30 = t[t.k == 30].iloc[0]
        rows.append({"change": label, "value": value, "p1_pct": round(q1 * 100, 2),
                     "sched_minus_mean_min": round(kw.get("sched", SCHED) - float(xx.mean()), 3),
                     "end10_pct": r10.p_end_ontime_pct, "all10_pct": r10.p_all_stops_ontime_pct,
                     "prod10_pct": r10.product_p1_pow_k_pct, "avg10_pct": r10.p_stops_avg_ontime_pct,
                     "end30_pct": r30.p_end_ontime_pct, "all30_pct": r30.p_all_stops_ontime_pct,
                     "prod30_pct": r30.product_p1_pow_k_pct, "mean_end30_delay_min": r30.mean_end_delay_min})
    add("基本", "3.2分・振れ0.25・共通0.10")
    for s in [3.0, 3.1, 3.4, 3.6]:
        add("時刻表の1区間の時間（分）", s, sched=s)
    for sg in [0.15, 0.4]:
        add("区間ごとの振れ（対数の標準偏差）", sg, sig=sg)
    for sc in [0.0, 0.2]:
        add("便に共通の振れ（対数の標準偏差）", sc, sig_c=sc)
    add("早く着いても待たない（早発あり、前後1分以内を定時）", "早発あり", hold=False)
    sens = pd.DataFrame(rows)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    b = base.set_index("k")
    sh = sens[sens.change != "早く着いても待たない（早発あり、前後1分以内を定時）"]
    res = {
        "setup": {"median_section_min": MED, "sigma_section": SIG, "sigma_common": SIG_C, "sched_section_min": SCHED,
                  "ontime_tol_min": TOL, "trips": N_TRIP, "max_sections": K_MAX,
                  "mean_section_min_formula": round(MED * np.exp((SIG ** 2 + SIG_C ** 2) / 2), 4)},
        "mean_section_min_data": round(mean_x, 4),
        "p1_ontime_pct": round(p1 * 100, 2),
        "by_sections": base.to_dict("records"),
        "k10": b.loc[10].to_dict(), "k30": b.loc[30].to_dict(),
        "k10_avg_minus_all_pts": round(float(b.loc[10, "p_stops_avg_ontime_pct"] - b.loc[10, "p_all_stops_ontime_pct"]), 2),
        "sensitivity": sens.to_dict("records"),
        "sens_range_end30_pct": [float(sens.end30_pct.min()), float(sens.end30_pct.max())],
        "sens_range_all10_pct": [float(sens.all10_pct.min()), float(sens.all10_pct.max())],
        "sens_range_prod10_pct": [float(sens.prod10_pct.min()), float(sens.prod10_pct.max())],
        "sens_all10_over_prod10_count": int((sens.all10_pct > sens.prod10_pct).sum()),
        "sens_rows": int(len(sens)),
        "sens_hold_range_end10_pct": [float(sh.end10_pct.min()), float(sh.end10_pct.max())],
        "sens_hold_range_end30_pct": [float(sh.end30_pct.min()), float(sh.end30_pct.max())],
        "sens_hold_range_all10_pct": [float(sh.all10_pct.min()), float(sh.all10_pct.max())],
        "sens_hold_range_all30_pct": [float(sh.all30_pct.min()), float(sh.all30_pct.max())],
        "sens_hold_range_p1_pct": [float(sh.p1_pct.min()), float(sh.p1_pct.max())],
        "sens_hold_all30_over_prod30_count": int((sh.all30_pct > sh.prod30_pct).sum()),
        "sens_hold_all10_over_prod10_count": int((sh.all10_pct > sh.prod10_pct).sum()),
        "sens_hold_rows": int(len(sh)),
        "base_cross_k_all_over_product": int(base[base.p_all_stops_ontime_pct > base.product_p1_pow_k_pct].k.min()),
    }
    json.dump(res, open(RES / "a1040_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：区間の数と定時の割合（3つの数え方と掛け算）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.plot(base.k, base.p_stops_avg_ontime_pct, "o-", color=GREEN, label="停留所ごとの定時の平均")
    ax.plot(base.k, base.p_end_ontime_pct, "o-", color=BLUE, label="終点で定時")
    ax.plot(base.k, base.p_all_stops_ontime_pct, "s-", color=ORANGE, label="全部の停留所で定時")
    ax.plot(base.k, base.product_p1_pow_k_pct, "--", color=GRAY, label="1区間の定時率の k 乗（掛け算）")
    ax.set_xlabel("区間の数（停留所の数）"); ax.set_ylabel("便の割合（%）"); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("同じ便でも、数え方で「時刻表どおり」の割合は大きく違う（基本の置き方）")
    save(fig, "a1040_by_sections.png", SRC, y=-0.04)

    # 図2：終点で定時の割合と、時刻表の余裕
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    ks = np.arange(1, K_MAX + 1)
    curves = {"k": ks}
    for s, col in [(3.0, ORANGE), (3.2, BLUE), (3.4, GREEN), (3.6, GRAY)]:
        dl, _ = simulate(np.random.default_rng(SEED * 7 + int(s * 10)), n=40000, sched=s)
        cv = (dl <= TOL).mean(0) * 100
        curves[f"end_ontime_pct_sched_{s:.1f}"] = np.round(cv, 2)
        ax.plot(ks, cv, color=col, lw=1.8, label=f"時刻表の1区間 {s:.1f}分")
    pd.DataFrame(curves).to_csv(RES / "slack_curves.csv", index=False)
    ax.set_xlabel("区間の数（停留所の数）"); ax.set_ylabel("終点で定時の便（%）"); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title(f"時刻表の1区間を長く組むほど、終点の定時の下がり方はゆるやかになる")
    save(fig, "a1040_slack.png", SRC, y=-0.04)

    # 図3：確かめ（10区間で、全部の停留所で定時と掛け算）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    lab = [f"{r.change}：{r.value}" if r.change != "基本" else "基本" for r in sens.itertuples()]
    lab = [l.replace("（対数の標準偏差）", "").replace("（早発あり、前後1分以内を定時）", "") for l in lab]
    y = np.arange(len(sens))[::-1]
    ax.barh(y + 0.2, sens.all10_pct, height=0.4, color=ORANGE, label="全部の停留所で定時（数えた値）")
    ax.barh(y - 0.2, sens.prod10_pct, height=0.4, color=GRAY, label="1区間の定時率の10乗")
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8.5)
    ax.set_xlabel("10区間の便の割合（%）"); ax.set_xlim(0, 105)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("掛け算は、置き方によって上にも下にも外れる（10区間）")
    save(fig, "a1040_robust.png", SRC, y=-0.03)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
