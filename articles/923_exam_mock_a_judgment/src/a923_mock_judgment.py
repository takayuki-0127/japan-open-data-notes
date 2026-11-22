"""923 模試の「A判定」は、何%の確率で受かるという意味なのか？（架空のデータ）

架空の資格試験と、その模擬試験（模試）。受験者ごとに実力を置き、模試の点と本番の点は
「実力＋その回の振れ」、本番までに実力が伸びる量は人ごとに違うと置く。本番は合格点65点（固定）、
年ごとに問題の難しさが上下する。模試の判定は、作成者が置いた物差し
（前の年の模試の点5点きざみの帯ごとに、本番に受かった人の割合が A 80%以上・B 60%以上・C 40%以上・D 20%以上）で作り、
次の年の受験者に当てたとき、A判定の人が実際に何%受かるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 923
SRC = "架空の資格試験と模擬試験（作成者が乱数で作成、seed 923）"
rng = np.random.default_rng(SEED)
LEVELS = [("A", 0.8), ("B", 0.6), ("C", 0.4), ("D", 0.2)]
JUDG = ["A", "B", "C", "D", "E"]
CUT = 65.0
BASE = {"year_sd": 3.0, "growth_sd": 4.0, "mock_sd": 5.0, "n_calib": 2000}
MIN_BAND = 10                          # 判定を決めるのに使う帯の最少の人数
N_YEAR = 5000                          # 1年の模試の受験者（全員が本番も受ける）


def one_year(rng, n, year_sd, growth_sd, mock_sd):
    theta = rng.normal(55, 12, n)                                   # 模試の時点の実力
    mock = np.clip(np.round(theta + rng.normal(0, mock_sd, n)), 0, 100)
    growth = rng.normal(3, growth_sd, n)                            # 本番までの伸び（人ごと）
    d = rng.normal(0, year_sd)                                      # その年の本番の難しさ（全員共通）
    exam = theta + growth + rng.normal(0, 5, n) - d
    return mock, exam >= CUT, theta, d


def thresholds(mock, passed):
    """前の年のデータから、判定の下限の点を決める：その帯より上のどの帯（10人以上いる帯）も合格の割合が基準以上になる、いちばん低い帯"""
    band = (mock // 5).astype(int)
    bs, cnt = np.unique(band, return_counts=True)
    bs = bs[cnt >= MIN_BAND]                       # 人が少なすぎる帯は使わない
    rate = np.array([passed[band == b].mean() for b in bs])
    th = {}
    for name, lv in LEVELS:
        ok = rate >= lv
        # 上から見て、基準を下回る帯が初めて出るところの1つ上
        bad = np.where(~ok)[0]
        start = bs[bad.max() + 1] if len(bad) and bad.max() + 1 < len(bs) else (bs[0] if not len(bad) else 200)
        th[name] = int(start) * 5          # 1000 は「その判定の帯がない」
    return th


def judge(mock, th):
    j = np.full(mock.shape, "E", dtype="<U1")
    for name in ["D", "C", "B", "A"]:
        j[mock >= th[name]] = name
    return j


def run(rng, reps, year_sd, growth_sd, mock_sd, n_calib, keep=False):
    recs, bands = [], []
    for r in range(reps):
        m0, p0, _, _ = one_year(rng, n_calib, year_sd, growth_sd, mock_sd)
        th = thresholds(m0, p0)
        m1, p1, t1, d1 = one_year(rng, N_YEAR, year_sd, growth_sd, mock_sd)
        j = judge(m1, th)
        rec = {"rep": r, "th_A": th["A"], "year_d": d1, "pass_all": p1.mean()}
        for k in JUDG:
            s = j == k
            rec[f"n_{k}"] = int(s.sum())
            rec[f"pass_{k}"] = p1[s].mean() if s.any() else np.nan
            rec[f"share_of_passers_{k}"] = (s & p1).sum() / max(p1.sum(), 1)
        lo = (m1 >= th["A"]) & (m1 < th["A"] + 5)
        rec["pass_A_lowest_band"] = p1[lo].mean() if lo.any() else np.nan
        hi = m1 >= th["A"] + 15
        rec["pass_A_15plus"] = p1[hi].mean() if hi.any() else np.nan
        recs.append(rec)
        if keep:
            b = (m1 // 5).astype(int) * 5
            for v in np.unique(b):
                bands.append({"rep": r, "band": int(v), "pass": float(p1[b == v].mean()), "n": int((b == v).sum()),
                              "rel_A": int(v - th["A"])})
    return pd.DataFrame(recs), (pd.DataFrame(bands) if keep else None)


def below(s, v=0.8):
    s = s.dropna()
    return round(float((s < v).mean()), 4)


def q(s, p):
    return round(float(np.nanquantile(s, p)), 4)


def main():
    t0 = time.time()
    df, bands = run(rng, 2000, **BASE, keep=True)
    df.round(4).to_csv(RES / "years_base.csv", index=False)

    by_j = []
    for k in JUDG:
        by_j.append({"judgment": k, "ruler": {"A": "80%以上", "B": "60〜80%", "C": "40〜60%", "D": "20〜40%", "E": "20%未満"}[k],
                     "share_of_examinees": round(float((df[f"n_{k}"] / N_YEAR).mean()), 4),
                     "pass_mean": round(float(df[f"pass_{k}"].mean()), 4),
                     "pass_p10": q(df[f"pass_{k}"], .1), "pass_p90": q(df[f"pass_{k}"], .9),
                     "share_of_passers": round(float(df[f"share_of_passers_{k}"].mean()), 4)})
    by_j = pd.DataFrame(by_j)
    by_j.to_csv(RES / "by_judgment.csv", index=False)

    rel = bands[(bands.rel_A >= -15) & (bands.rel_A <= 25)].groupby("rel_A").agg(
        pass_mean=("pass", "mean"), pass_p10=("pass", lambda s: s.quantile(.1)), pass_p90=("pass", lambda s: s.quantile(.9)),
        n_mean=("n", "mean")).round(4).reset_index()
    rel.to_csv(RES / "pass_by_band_relative_to_A.csv", index=False)

    base = {"A_pass_mean": round(float(df.pass_A.mean()), 4), "A_pass_p10": q(df.pass_A, .1), "A_pass_p90": q(df.pass_A, .9),
            "A_pass_min": round(float(df.pass_A.min()), 4),
            "A_year_below80_note": "A判定の人がいない年は数えない",
            "A_year_below80": below(df.pass_A),
            "A_lowest_band_mean": round(float(df.pass_A_lowest_band.mean()), 4),
            "A_lowest_band_p10": q(df.pass_A_lowest_band, .1), "A_lowest_band_p90": q(df.pass_A_lowest_band, .9),
            "A_lowest_band_below80": below(df.pass_A_lowest_band),
            "A_15plus_mean": round(float(df.pass_A_15plus.mean()), 4),
            "th_A_values": {(str(int(k)) if k < 1000 else "A判定なし"): round(float(v), 4) for k, v in df.th_A.value_counts(normalize=True).sort_index().items()},
            "pass_all_mean": round(float(df.pass_all.mean()), 4), "pass_all_p10": q(df.pass_all, .1),
            "pass_all_p90": q(df.pass_all, .9),
            "years_no_A": round(float(df.pass_A.isna().mean()), 4),
            "passers_not_A": round(float(1 - df.share_of_passers_A.mean()), 4)}

    # 確かめ：年ごとの難しさ×伸びのばらつき×模試の振れ×前の年の人数
    rob = []
    for ysd in [0.0, 3.0, 6.0]:
        for gsd in [0.0, 4.0, 8.0]:
            for msd in [3.0, 5.0, 8.0]:
                for nc in [200, 2000]:
                    d, _ = run(rng, 300, ysd, gsd, msd, nc)
                    rob.append({"year_sd": ysd, "growth_sd": gsd, "mock_sd": msd, "n_calib": nc,
                                "A_share": round(float((d.n_A / N_YEAR).mean()), 4),
                                "A_pass_mean": round(float(d.pass_A.mean()), 4), "A_pass_p10": q(d.pass_A, .1),
                                "A_pass_p90": q(d.pass_A, .9), "A_year_below80": below(d.pass_A),
                                "years_no_A": round(float(d.pass_A.isna().mean()), 4),
                                "A_lowest_band_mean": round(float(d.pass_A_lowest_band.mean()), 4),
                                "passers_not_A": round(float(1 - d.share_of_passers_A.mean()), 4)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    y0 = rob[rob.year_sd == 0]
    robs = {"A_pass_mean_min": float(rob.A_pass_mean.min()), "A_pass_mean_max": float(rob.A_pass_mean.max()),
            "A_year_below80_min": float(rob.A_year_below80.min()), "A_year_below80_max": float(rob.A_year_below80.max()),
            "A_lowest_band_min": float(rob.A_lowest_band_mean.min()), "A_lowest_band_max": float(rob.A_lowest_band_mean.max()),
            "passers_not_A_min": float(rob.passers_not_A.min()), "passers_not_A_max": float(rob.passers_not_A.max()),
            "years_no_A_max": float(rob.years_no_A.max()),
            "year_sd0_A_year_below80_max": float(y0.A_year_below80.max()),
            "year_sd0_A_pass_p10_min": float(y0.A_pass_p10.min()),
            "by_n_calib": {str(k): {"A_pass_mean_min": float(g.A_pass_mean.min()), "A_pass_mean_max": float(g.A_pass_mean.max()),
                                    "A_year_below80_min": float(g.A_year_below80.min()),
                                    "A_year_below80_max": float(g.A_year_below80.max()),
                                    "A_lowest_band_min": float(g.A_lowest_band_mean.min()),
                                    "A_lowest_band_max": float(g.A_lowest_band_mean.max()),
                                    "years_no_A_min": float(g.years_no_A.min()), "years_no_A_max": float(g.years_no_A.max())}
                           for k, g in rob.groupby("n_calib")},
            "by_year_sd": {str(k): {"A_pass_p10_min": float(g.A_pass_p10.min()), "A_pass_p10_max": float(g.A_pass_p10.max()),
                                    "A_year_below80_min": float(g.A_year_below80.min()),
                                    "A_year_below80_max": float(g.A_year_below80.max())}
                           for k, g in rob.groupby("year_sd")}}

    # 1年分の受験者（data）
    m0, p0, _, _ = one_year(rng, BASE["n_calib"], BASE["year_sd"], BASE["growth_sd"], BASE["mock_sd"])
    th = thresholds(m0, p0)
    m1, p1, t1, d1 = one_year(rng, N_YEAR, BASE["year_sd"], BASE["growth_sd"], BASE["mock_sd"])
    j = judge(m1, th)
    one = pd.DataFrame({"id": np.arange(1, N_YEAR + 1), "mock": m1.astype(int), "judgment": j, "passed": p1.astype(int)})
    one.to_csv(DATA / "one_year_examinees.csv", index=False)
    one_res = {"thresholds": th, "year_difficulty": round(float(d1), 2), "pass_rate": round(float(p1.mean()), 4),
               "A_n": int((j == "A").sum()), "A_pass": round(float(p1[j == "A"].mean()), 4)}

    out = {"base": base, "by_judgment": by_j.to_dict("records"), "robust": robs, "one_year": one_res}
    json.dump(out, open(RES / "a923_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：判定ごとの今年の合格の割合（年ごとの10〜90%）と作成者の物差し
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = np.arange(5)
    ax.bar(x, by_j.pass_mean * 100, color=[BLUE, LIGHT, LIGHT, LIGHT, LIGHT], width=0.6)
    ax.errorbar(x, by_j.pass_mean * 100, yerr=[(by_j.pass_mean - by_j.pass_p10) * 100, (by_j.pass_p90 - by_j.pass_mean) * 100],
                fmt="none", ecolor=INK, capsize=4, lw=1)
    for i, (lo, hi) in enumerate([(80, 100), (60, 80), (40, 60), (20, 40), (0, 20)]):
        ax.plot([i - 0.38, i + 0.38], [lo, lo], color=ORANGE, lw=1.4, ls="--")
    ax.plot([], [], color=ORANGE, ls="--", label="判定の物差しの下限（作成者が置いた値）")
    ax.set_xticks(x); ax.set_xticklabels([f"{k}判定" for k in JUDG])
    ax.set_ylabel("今年の本番で受かった割合（%）"); ax.set_ylim(0, 105)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title(f"A判定の人が受かった割合は平均{base['A_pass_mean']*100:.1f}%（線は年ごとの10〜90%）")
    save(fig, "a923_by_judgment.png", SRC)

    # 図2：A判定の下限からの距離ごとの合格の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.fill_between(rel.rel_A, rel.pass_p10 * 100, rel.pass_p90 * 100, color=LIGHT, alpha=.6, lw=0, label="年ごとの10〜90%")
    ax.plot(rel.rel_A, rel.pass_mean * 100, color=BLUE, marker="o", ms=4, label="平均")
    ax.axvline(-0.5, color=ORANGE, lw=1, ls="--"); ax.text(0.5, 8, "ここから上がA判定", color=ORANGE, fontsize=9)
    ax.axhline(80, color=GRAY, lw=0.8, ls=":")
    ax.set_xlabel("模試の点の帯（A判定の下限から何点上か、5点きざみ）"); ax.set_ylabel("今年の本番で受かった割合（%）")
    ax.set_ylim(0, 102); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("A判定の下の端の帯では、受かった割合は80%前後にとどまる")
    save(fig, "a923_by_band.png", SRC)

    # 図3：年ごとの難しさの振れ（year_sd）と、A判定の合格の割合が80%を下回った年
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    sub = rob[(rob.n_calib == 2000) & (rob.mock_sd == 5.0)]
    cols = {0.0: LIGHT, 4.0: BLUE, 8.0: INK}
    for gsd, g in sub.groupby("growth_sd"):
        ax.plot(g.year_sd, g.A_year_below80 * 100, marker="o", color=cols[gsd], label=f"伸びのばらつき {gsd:.0f}点")
    ax.set_xticks([0, 3, 6]); ax.set_xticklabels(["0点", "3点", "6点"])
    ax.set_xlabel("本番の難しさの年ごとの振れ（標準偏差）"); ax.set_ylabel("A判定の人の合格が80%を下回った年（%）")
    ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("本番の難しさが年ごとに振れるほど、A判定でも80%を下回る年が増える")
    save(fig, "a923_by_year_sd.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rel)
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
