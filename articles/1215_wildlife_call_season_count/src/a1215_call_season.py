"""1215 鳴き声で数えると、よく鳴く時期と鳴かない時期で、数はどう見えるのか？（架空のデータ）

架空のB森の種A（鳥）。聞き取りの地点20か所の範囲にいる鳥の本当の数を作成者が置き、
季節のあいだは数を変えない。鳥はその日の鳴く度合い（1分あたりの鳴く回数の見込み）で鳴き、
10分の聞き取りのあいだに1回でも鳴けば「聞こえた」として数える。
鳴く度合いは季節で山の形に変わり、鳥ごとにも違う（平均1倍の散らばり、形の値2）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1215
SRC = "架空のB森の種A（作成者が置いた鳥の数・鳴く度合いからの乱数、seed 1215）"
rng = np.random.default_rng(SEED)

T = 10.0          # 1回の聞き取り（分）
K = 2.0           # 鳥ごとの鳴く度合いの散らばり（形の値。平均1倍）
BASE = 0.01       # 鳴かない時期の1分あたりの見込み
PEAK = 0.15       # いちばん鳴く日の1分あたりの見込み
P_DAY = 40        # いちばん鳴く日（季節のはじめを0日目とした日）
W = 12            # 山の幅（日）
N1 = 150          # 1年目の本当の数
VISITS = [30, 40, 50]


def rate(d, peak_day=P_DAY, w=W, peak=PEAK, base=BASE):
    d = np.asarray(d, float)
    return base + (peak - base) * np.exp(-0.5 * ((d - peak_day) / w) ** 2)


def p_formula(d, **kw):
    """数えた数÷本当の数の式：1−(1+鳴く度合い×10分÷形の値)^(−形の値)"""
    return 1 - (1 + rate(d, **kw) * T / K) ** (-K)


def count(rng, n, days, reps, **kw):
    """reps 回 × days の数えた数（鳥ごとの度合いは回ごとに引き直す）"""
    g = rng.gamma(K, 1 / K, size=(reps, n))
    lam = rate(days, **kw)                       # (len(days),)
    p = 1 - np.exp(-g[:, :, None] * lam[None, None, :] * T)
    heard = rng.random(p.shape) < p
    return heard.sum(1), g, heard


def main():
    out = {}
    q = rng.gamma(K, 1 / K, 200000)
    out["call_level_spread"] = {"p10": round(float(np.quantile(q, .1)), 3), "p90": round(float(np.quantile(q, .9)), 3)}

    # 1) 季節のあいだ5日ごとに数える（本当の数は150のまま）
    days = np.arange(0, 91, 5)
    c, g, heard = count(rng, N1, days, 200)
    season = pd.DataFrame({"day": days, "rate_per_min": np.round(rate(days), 4),
                           "count_mean": np.round(c.mean(0), 2), "count_p10": np.round(np.quantile(c, .1, axis=0), 1),
                           "count_p90": np.round(np.quantile(c, .9, axis=0), 1),
                           "share_of_true_pct": np.round(c.mean(0) / N1 * 100, 2),
                           "formula_share_pct": np.round(p_formula(days) * 100, 2)})
    season.to_csv(RES / "season_counts.csv", index=False)
    out["season"] = {"true": N1, "max_share_pct": float(season.share_of_true_pct.max()),
                     "max_day": int(season.day[season.share_of_true_pct.idxmax()]),
                     "min_share_pct": float(season.share_of_true_pct.min()),
                     "share_day30": float(season.share_of_true_pct[season.day == 30].iloc[0]),
                     "share_day50": float(season.share_of_true_pct[season.day == 50].iloc[0]),
                     "share_day20": float(season.share_of_true_pct[season.day == 20].iloc[0]),
                     "count_day0": float(season.count_mean[0]), "count_day40": float(season.count_mean[season.day == 40].iloc[0]),
                     "max_abs_diff_formula_pt": round(float((season.share_of_true_pct - season.formula_share_pct).abs().max()), 2)}
    one = pd.DataFrame({"bird_id": np.arange(1, N1 + 1), "call_level": np.round(g[0], 4)})
    for j, d in enumerate(days):
        if d in (20, 30, 40, 50, 60):
            one[f"heard_day{d}"] = heard[0, :, j].astype(int)
    one.to_csv(DATA / "birds_year1_example.csv", index=False)
    out["one_draw_counts"] = {f"day{d}": int(one[f"heard_day{d}"].sum()) for d in (20, 30, 40, 50, 60)}

    # 2) 2年の比べ：1年目は40日目が山。2年目は山がずれ、本当の数は−10%
    REPS = 500
    rows = []
    for shift in [-14, -7, 0, 7, 14]:
        for change in [0.0, -0.10]:
            n2 = int(round(N1 * (1 + change)))
            c1, _, _ = count(rng, N1, np.array(VISITS), REPS)
            c2, _, _ = count(rng, n2, np.array(VISITS), REPS, peak_day=P_DAY + shift)
            for meth, f in [("40日目の1回", lambda x: x[:, 1]), ("3回のうち多い回", lambda x: x.max(1)),
                            ("3回の平均", lambda x: x.mean(1))]:
                a = f(c2) / f(c1) - 1
                rows.append({"peak_shift_days": shift, "true_change_pct": round(change * 100, 1), "method": meth,
                             "apparent_change_pct": round(float(a.mean() * 100), 2),
                             "p10_pct": round(float(np.quantile(a, .1) * 100), 2),
                             "p90_pct": round(float(np.quantile(a, .9) * 100), 2),
                             "share_looks_up_pct": round(float((a > 0).mean() * 100), 2)})
            fm = p_formula(40, peak_day=P_DAY + shift) / p_formula(40)
            rows[-3]["formula_apparent_pct"] = round(float(((1 + change) * fm - 1) * 100), 2)
    yr = pd.DataFrame(rows)
    yr.to_csv(RES / "two_years.csv", index=False)
    out["two_years"] = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()} for r in yr.to_dict("records")]

    # 3) 確かめ：山のずれ5×数える日3×本当の増減4×山の幅3×いちばん鳴く日の度合い3＝540通り（各40回）
    grid = []
    gr = np.random.default_rng(SEED * 7)
    for w in [6, 12, 24]:
        for pk in [0.08, 0.15, 0.4]:
            for sday in [30, 40, 50]:
                vis = np.array([sday - 10, sday, sday + 10])
                for shift in [-14, -7, 0, 7, 14]:
                    for change in [0.2, 0.1, 0.0, -0.1, -0.2]:
                        if change == 0.2:
                            continue
                        n2 = int(round(N1 * (1 + change)))
                        c1, _, _ = count(gr, N1, vis, 40, w=w, peak=pk)
                        c2, _, _ = count(gr, n2, vis, 40, peak_day=P_DAY + shift, w=w, peak=pk)
                        rec = {"width_days": w, "peak_rate": pk, "survey_day": sday, "peak_shift_days": shift,
                               "true_change_pct": round(change * 100, 1)}
                        for key, f in [("one", lambda x: x[:, 1]), ("max3", lambda x: x.max(1)), ("mean3", lambda x: x.mean(1))]:
                            a = f(c2) / f(c1) - 1
                            rec[f"apparent_{key}_pct"] = round(float(a.mean() * 100), 2)
                            if change != 0:
                                rec[f"wrong_dir_{key}_pct"] = round(float((np.sign(a) != np.sign(change)).mean() * 100), 2)
                            else:
                                rec[f"off10_{key}_pct"] = round(float((np.abs(a) > 0.10).mean() * 100), 2)
                            rec[f"abs_err_{key}_pt"] = round(float(np.abs(a - change).mean() * 100), 2)
                        grid.append(rec)
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid.csv", index=False)
    ch = gd[gd.true_change_pct != 0]
    rob = {"n_settings": int(len(gd)), "n_changed_settings": int(len(ch)), "n_no_change_settings": int((gd.true_change_pct == 0).sum())}
    for key, lab in [("one", "one"), ("max3", "max3"), ("mean3", "mean3")]:
        rob[f"apparent_{lab}_range_change_m10"] = [float(gd[gd.true_change_pct == -10][f"apparent_{key}_pct"].min()),
                                                   float(gd[gd.true_change_pct == -10][f"apparent_{key}_pct"].max())]
        rob[f"wrong_dir_{lab}_mean_pct"] = round(float(ch[f"wrong_dir_{key}_pct"].mean()), 2)
        rob[f"abs_err_{lab}_mean_pt"] = round(float(gd[f"abs_err_{key}_pt"].mean()), 2)
        rob[f"wrong_dir_{lab}_by_abs_shift"] = {str(s): round(float(ch[ch.peak_shift_days.abs() == s][f"wrong_dir_{key}_pct"].mean()), 2)
                                                for s in [0, 7, 14]}
    rob["wrong_dir_one_by_width"] = {str(w): round(float(ch[ch.width_days == w]["wrong_dir_one_pct"].mean()), 2) for w in [6, 12, 24]}
    rob["wrong_dir_one_by_peak_rate"] = {str(p): round(float(ch[ch.peak_rate == p]["wrong_dir_one_pct"].mean()), 2) for p in [0.08, 0.15, 0.4]}
    z = gd[gd.true_change_pct == 0]
    rob["off10_one_shift0_pct"] = round(float(z[z.peak_shift_days == 0]["off10_one_pct"].mean()), 2)
    rob["off10_one_shift14_pct"] = round(float(z[z.peak_shift_days.abs() == 14]["off10_one_pct"].mean()), 2)
    rob["off10_max3_shift14_pct"] = round(float(z[z.peak_shift_days.abs() == 14]["off10_max3_pct"].mean()), 2)
    out["robust"] = rob

    b = yr[(yr.true_change_pct == -10)]
    out["headline"] = {"season_share_range_pct": [out["season"]["min_share_pct"], out["season"]["max_share_pct"]],
                       "one_visit_change_m10_range_pct": [float(b[b.method == "40日目の1回"].apparent_change_pct.min()),
                                                          float(b[b.method == "40日目の1回"].apparent_change_pct.max())],
                       "max3_change_m10_range_pct": [float(b[b.method == "3回のうち多い回"].apparent_change_pct.min()),
                                                     float(b[b.method == "3回のうち多い回"].apparent_change_pct.max())]}
    json.dump(out, open(RES / "a1215_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：季節のあいだの数えた数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.fill_between(season.day, season.count_p10, season.count_p90, color=LIGHT, alpha=.6, lw=0, label="10〜90%の範囲（200回）")
    ax.plot(season.day, season.count_mean, color=BLUE, marker="o", ms=4, label="数えた数（平均）")
    ax.axhline(N1, color=ORANGE, ls="--", lw=1.2, label="本当の数（150羽のまま）")
    ax.set_ylim(0, 165); ax.set_xlabel("季節のはじめからの日数（40日目がいちばん鳴く日）"); ax.set_ylabel("聞こえた鳥の数（羽）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("本当の数は同じでも、数えた数は鳴く時期に合わせて上下した")
    save(fig, "a1215_season.png", SRC)

    # 図2：2年の比べ（本当は−10%）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    meths = ["40日目の1回", "3回のうち多い回", "3回の平均"]
    cols = [ORANGE, BLUE, LIGHT]
    xs = np.arange(5)
    for i, m in enumerate(meths):
        v = b[b.method == m].apparent_change_pct.values
        ax.bar(xs + (i - 1) * 0.27, v, width=0.27, color=cols[i], label=m)
    ax.axhline(-10, color=INK, ls="--", lw=1); ax.text(4.45, -9.0, "本当 −10%", fontsize=9, ha="right")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_xticks(xs); ax.set_xticklabels(["14日早い", "7日早い", "同じ", "7日遅い", "14日遅い"])
    ax.set_xlabel("2年目のいちばん鳴く日（1年目との差）"); ax.set_ylabel("数えた数の増減（%、500回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower center")
    ax.set_title("40日目の1回だけ数えると、鳴く時期のずれで−10%の減りが大きく見えた")
    save(fig, "a1215_two_years.png", SRC)

    # 図3：確かめ（向きを読み違えた割合、山のずれの大きさ別）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for i, (key, lab) in enumerate([("one", "1回"), ("max3", "3回のうち多い回"), ("mean3", "3回の平均")]):
        v = [rob[f"wrong_dir_{key}_by_abs_shift"][s] for s in ["0", "7", "14"]]
        ax.bar(np.arange(3) + (i - 1) * 0.27, v, width=0.27, color=cols[i], label=lab)
    ax.set_xticks(range(3)); ax.set_xticklabels(["ずれなし", "7日ずれ", "14日ずれ"])
    ax.set_ylim(0, 50); ax.set_ylabel("増減の向きを読み違えた割合（%）")
    ax.set_xlabel("いちばん鳴く日の年ごとのずれ（本当は+10・−10・−20%の増減、405通り）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("鳴く時期のずれが大きいほど、増減の向きを読み違えやすい")
    save(fig, "a1215_grid.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False), json.dumps(rob, ensure_ascii=False))


if __name__ == "__main__":
    main()
