"""1226 小さな改善の差は、検索語を何語そろえれば偶然と見分けられるのか？（架空のデータ）

架空の社内の文書の集まりと架空の検索語2万語。語ごとに候補の文書215件の「正しさ」（0・1・2）を作成者が決める。
今の検索 A と、直した検索 B を比べる。B の直しが効くのは一部の語（基本30%）だけで、ほかの語では A と同じ10件を出す。
直しが効く語では、正しい文書の上乗せを k 倍にし、乱数の一部を引き直す（良くなる語も悪くなる語も出る）。
k は、全体の改善（10件の点の平均の差）が +1・+2・+5 ポイントになるよう決める。
良さは「10件の点」：上位10件の正しさ（0・1・2）を、順位 r で 1/log2(r+1) 倍して足し、理想の並びの値で割る（0〜1）。
n 語を2万語の中からでたらめに選び（同じ語が2回選ばれることもある）、差の平均が偶然の幅（±1.96×標準誤差）の外に出た割合を数える。
  ・同じ語で比べる：同じ n 語で A と B を両方出し、語ごとの差で数える
  ・別々の語で比べる：A は n 語、B は別の n 語で数え、平均どうしの差で数える
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1226
SRC = "架空の社内の文書と検索語（作成者が置いた正しさと検索の点からの乱数、seed 1226）"
M = 215
NPOP = 20000
MIX = 0.4                # 1つを探す語の割合
A = (2.8, 1.8)           # 正しさ2・正しさ1の上乗せ
WIG = 0.5                # 直しが効く語で引き直す乱数の重み
BASE_F = 0.3
BASE_GAIN = 2.0
NS = [25, 50, 100, 200, 400, 800, 1600, 3200, 6400]
REPS = 1000
DISC = 1 / np.log2(np.arange(2, 12))
Z = 1.96


def make_queries(rng, nq):
    one = rng.random(nq) < MIX
    g = np.zeros((nq, M), dtype=np.int8)
    g[:, 0] = 2
    g[~one, 1:3] = 2
    g[~one, 3:15] = 1
    h = rng.uniform(0.6, 1.4, (nq, 1))
    e = rng.standard_normal((nq, M)).astype(np.float32)
    e2 = rng.standard_normal((nq, M)).astype(np.float32)
    ideal = -np.sort(-g, axis=1)[:, :10]
    idcg = (ideal * DISC).sum(1)
    return dict(one=one, g=g, h=h, e=e, e2=e2, idcg=idcg)


def w10(g, s, idcg):
    part = np.argpartition(-s, 10, axis=1)[:, :10]
    order = np.argsort(-np.take_along_axis(s, part, 1), axis=1, kind="stable")
    idx = np.take_along_axis(part, order, 1)
    gt = np.take_along_axis(g, idx, 1)
    return (gt * DISC).sum(1) / idcg, (gt[:, 0] >= 1).astype(float)


def score_a(q, rows=None):
    sl = slice(None) if rows is None else rows
    g, h = q["g"][sl], q["h"][sl]
    s = h * (A[0] * (g == 2) + A[1] * (g == 1)) + q["e"][sl]
    return w10(g, s, q["idcg"][sl])


def score_b_changed(q, rows, k, wig=WIG):
    g, h = q["g"][rows], q["h"][rows]
    e = np.sqrt(1 - wig ** 2) * q["e"][rows] + wig * q["e2"][rows]
    s = h * (k * A[0] * (g == 2) + k * A[1] * (g == 1)) + e
    return w10(g, s, q["idcg"][rows])


def calibrate(q, base_w, base_t, changed, target_pt, wig=WIG):
    rows = np.where(changed)[0]
    lo, hi = 0.5, 6.0
    for _ in range(30):
        k = (lo + hi) / 2
        bw, _ = score_b_changed(q, rows, k, wig)
        gain = (bw - base_w[rows]).sum() / len(base_w) * 100
        lo, hi = (k, hi) if gain < target_pt else (lo, k)
    k = (lo + hi) / 2
    bw, bt = score_b_changed(q, rows, k, wig)
    w_b = base_w.copy(); w_b[rows] = bw
    t_b = base_t.copy(); t_b[rows] = bt
    return k, w_b, t_b


def detect(rng, a, b, n, reps=REPS):
    N = len(a)
    d = b - a
    pair = 0; unpair = 0
    for _ in range(reps):
        i = rng.integers(0, N, n)
        di = d[i]
        se = di.std(ddof=1) / np.sqrt(n)
        if se > 0 and di.mean() > Z * se:
            pair += 1
        j = rng.integers(0, N, 2 * n)
        ja, jb = j[:n], j[n:]
        se2 = np.sqrt(a[ja].var(ddof=1) / n + b[jb].var(ddof=1) / n)
        if b[jb].mean() - a[ja].mean() > Z * se2:
            unpair += 1
    return pair / reps * 100, unpair / reps * 100


def two_sided_pair(rng, d, n, reps=REPS):
    cnt = 0
    for _ in range(reps):
        di = d[rng.integers(0, len(d), n)]
        se = di.std(ddof=1) / np.sqrt(n)
        if se > 0 and abs(di.mean()) > Z * se:
            cnt += 1
    return cnt / reps * 100


def r2(x):
    return float(round(float(x), 2))


def r4(x):
    return float(round(float(x), 4))


def formula_n(sd, delta):
    return int(np.ceil(((1.96 + 0.8416) * sd / delta) ** 2))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    q = make_queries(rng, NPOP)
    base_w, base_t = score_a(q)
    u_changed = rng.random(NPOP)
    res = {"setting": {"n_pop": NPOP, "candidates": M, "mix_one": MIX, "A": A, "wiggle": WIG, "base_changed_share": BASE_F,
                       "base_gain_pt": BASE_GAIN, "ns": NS, "reps": REPS}}
    res["A_mean_w10_pct"] = r2(base_w.mean() * 100)
    res["A_sd_w10_pt"] = r2(base_w.std() * 100)

    # 基本：30%の語に効く、+2ポイント
    changed = u_changed < BASE_F
    k, wb, tb = calibrate(q, base_w, base_t, changed, BASE_GAIN)
    d = wb - base_w
    base = {"k": r4(k), "true_gain_pt": r2(d.mean() * 100), "changed_share_pct": r2(changed.mean() * 100),
            "diff_zero_pct": r2((np.abs(d) < 1e-12).mean() * 100), "diff_pos_pct": r2((d > 1e-12).mean() * 100),
            "diff_neg_pct": r2((d < -1e-12).mean() * 100),
            "sd_diff_pt": r2(d.std() * 100), "sd_A_pt": r2(base_w.std() * 100), "sd_B_pt": r2(wb.std() * 100),
            "gain_in_changed_pt": r2(d[changed].mean() * 100),
            "B_mean_w10_pct": r2(wb.mean() * 100),
            "top1_gain_pt": r2((tb - base_t).mean() * 100), "top1_sd_diff_pt": r2((tb - base_t).std() * 100)}
    base["formula_n_pair"] = formula_n(d.std(), d.mean())
    base["formula_n_unpair_each"] = formula_n(np.sqrt(base_w.var() + wb.var()), d.mean())
    base["formula_n_top1_pair"] = formula_n((tb - base_t).std(), (tb - base_t).mean())
    curve = []
    for n in NS:
        p, u = detect(rng, base_w, wb, n)
        curve.append({"n_queries": n, "pair_pct": r2(p), "unpair_pct": r2(u)})
    base["curve"] = curve
    base["sim_n80_pair"] = next((c["n_queries"] for c in curve if c["pair_pct"] >= 80), None)
    base["sim_n80_unpair"] = next((c["n_queries"] for c in curve if c["unpair_pct"] >= 80), None)
    res["base"] = base
    pd.DataFrame({"query": np.arange(1, 2001), "kind": np.where(q["one"][:2000], "one", "broad"), "changed": changed[:2000].astype(int),
                  "w10_A": np.round(base_w[:2000], 4), "w10_B": np.round(wb[:2000], 4)}).to_csv(DATA / "query_scores_2000.csv", index=False)

    # 改善0（直しは効く語で乱数を引き直すが、平均の差は0）での誤った「改善」
    k0, wb0, _ = calibrate(q, base_w, base_t, changed, 0.0)
    d0 = wb0 - base_w
    res["null"] = {"k": r4(k0), "true_gain_pt": r2(d0.mean() * 100),
                   "false_alarm_two_sided_pct": {str(n): r2(two_sided_pair(rng, d0, n)) for n in [50, 200, 800]}}

    # 改善の大きさ・効く語の割合・引き直す乱数の重みを変える（27通り）
    grows = []
    for f in [0.1, 0.3, 0.6]:
        ch = u_changed < f
        for gain in [0.5, 1.0, 2.0]:
            for wig in [0.25, 0.5, 0.75]:
                kk, wbb, tbb = calibrate(q, base_w, base_t, ch, gain, wig)
                dd = wbb - base_w
                dt = tbb - base_t
                row = {"changed_share_pct": int(round(f * 100)), "target_gain_pt": gain, "wiggle": wig, "k": r4(kk),
                       "true_gain_pt": r2(dd.mean() * 100),
                       "diff_zero_pct": r2((np.abs(dd) < 1e-12).mean() * 100), "diff_neg_pct": r2((dd < -1e-12).mean() * 100),
                       "sd_diff_pt": r2(dd.std() * 100),
                       "formula_n_pair": formula_n(dd.std(), dd.mean()),
                       "formula_n_unpair_each": formula_n(np.sqrt(base_w.var() + wbb.var()), dd.mean()),
                       "top1_gain_pt": r2(dt.mean() * 100),
                       "formula_n_top1_pair": formula_n(dt.std(), dt.mean()) if dt.mean() > 0 else None}
                p, u = detect(rng, base_w, wbb, row["formula_n_pair"], reps=500)
                row["sim_pct_at_formula_n_pair"] = r2(p)
                grows.append(row)
    gdf = pd.DataFrame(grows)
    gdf["ratio_unpair_over_pair"] = (gdf.formula_n_unpair_each / gdf.formula_n_pair).round(2)
    gdf.to_csv(RES / "grid.csv", index=False)
    res["grid"] = {"n": len(gdf), "formula_n_pair_range": [int(gdf.formula_n_pair.min()), int(gdf.formula_n_pair.max())],
                   "formula_n_unpair_range": [int(gdf.formula_n_unpair_each.min()), int(gdf.formula_n_unpair_each.max())],
                   "ratio_unpair_over_pair_range": [float(gdf.ratio_unpair_over_pair.min()), float(gdf.ratio_unpair_over_pair.max())],
                   "sim_pct_at_formula_n_range": [float(gdf.sim_pct_at_formula_n_pair.min()), float(gdf.sim_pct_at_formula_n_pair.max())],
                   "true_gain_range": [float(gdf.true_gain_pt.min()), float(gdf.true_gain_pt.max())],
                   "top1_over_w10_n_range": [float((gdf.formula_n_top1_pair / gdf.formula_n_pair).min().round(2)), float((gdf.formula_n_top1_pair / gdf.formula_n_pair).max().round(2))],
                   "by_gain_pair_range": {str(k): [int(g.formula_n_pair.min()), int(g.formula_n_pair.max())] for k, g in gdf.groupby("target_gain_pt")},
                   "by_gain_unpair_range": {str(k): [int(g.formula_n_unpair_each.min()), int(g.formula_n_unpair_each.max())] for k, g in gdf.groupby("target_gain_pt")},
                   "gain2_by_wiggle_and_share": gdf[gdf.target_gain_pt == 2.0][["changed_share_pct", "wiggle", "formula_n_pair", "sd_diff_pt", "diff_neg_pct"]].to_dict("records"),
                   "smaller_share_fewer_n_count": int(sum(1 for (g_, w_), g in gdf.groupby(["target_gain_pt", "wiggle"]) if g.sort_values("changed_share_pct").formula_n_pair.is_monotonic_increasing)),
                   "n_gain_wiggle_groups": int(gdf.groupby(["target_gain_pt", "wiggle"]).ngroups)}
    pd.DataFrame(curve).to_csv(RES / "curve_base.csv", index=False)

    # 図1：語数と見分けられた割合
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    cdf = pd.DataFrame(curve)
    ax.plot(cdf.n_queries, cdf.pair_pct, "o-", color=BLUE, label="同じ語で A と B を比べる")
    ax.plot(cdf.n_queries, cdf.unpair_pct, "s-", color=ORANGE, label="A と B を別々の語で比べる")
    ax.axhline(80, color=GRAY, lw=1, ls="--")
    ax.text(NS[0], 82, "80%", color=GRAY, fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks(NS, [f"{n:,}" for n in NS])
    ax.minorticks_off()
    ax.set_ylim(0, 100)
    ax.set_xlabel("検索語の数（片方あたり、対数の目盛り）")
    ax.set_ylabel("改善と見分けられた割合（%）")
    ax.set_title(f"全体で+{BASE_GAIN:g}ポイントの改善（効く語{int(BASE_F*100)}%）を見分けられた割合\n（{REPS:,}回引き直す）")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "a1226_curve.png", SRC)

    # 図2：語ごとの差の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    nz = d[np.abs(d) > 1e-12] * 100
    bins = np.arange(-100, 102, 4)
    cnt, _ = np.histogram(nz, bins=bins)
    ax.bar(bins[:-1] + 2, cnt / len(d) * 100, width=3.6, color=BLUE)
    ax.set_xlabel("語ごとの差（B−A、10件の点のポイント）")
    ax.set_ylabel("語に占める割合（%）")
    ax.set_title(f"語ごとの差：{base['diff_zero_pct']}%の語は差0（図は差0以外）\n上がった語{base['diff_pos_pct']}%・下がった語{base['diff_neg_pct']}%")
    save(fig, "a1226_diffs.png", SRC)

    # 図3：27通りの見込んだ語数（同じ語で比べる）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    cols = {10: ORANGE, 30: BLUE, 60: GREEN}
    for f, g in gdf.groupby("changed_share_pct"):
        gm = g[g.wiggle == 0.5].sort_values("target_gain_pt")
        lo_ = g.groupby("target_gain_pt").formula_n_pair.min()
        hi_ = g.groupby("target_gain_pt").formula_n_pair.max()
        ax.fill_between(lo_.index, lo_.values, hi_.values, color=cols[f], alpha=0.15, lw=0)
        ax.plot(gm.target_gain_pt, gm.formula_n_pair, "o-", color=cols[f], label=f"効く語{f}%")
    ax.set_yscale("log")
    ax.set_yticks([100, 300, 1000, 3000, 10000], ["100", "300", "1,000", "3,000", "10,000"])
    ax.minorticks_off()
    ax.set_xticks([0.5, 1, 2], ["+0.5", "+1", "+2"])
    ax.set_xlabel("全体の改善（10件の点、ポイント）")
    ax.set_ylabel("見分けるのに要る語数（対数の目盛り）")
    ax.set_title("同じ語で比べるときに要る語数（式で見込んだ値、見込み80%）\n線：引き直す乱数の重み0.5、帯：0.25〜0.75")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "a1226_grid.png", SRC)

    with open(RES / "a1226_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ["A_mean_w10_pct", "base", "null", "grid"]}, ensure_ascii=False, indent=1))
    print(gdf.to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
