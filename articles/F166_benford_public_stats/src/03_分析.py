"""03 分析：市区町村の公的統計は、ベンフォードの法則にどこまで従うか。

目的は「おかしな市区町村を見つける」ことではなく、
自然に生まれる数字でも、ベンフォードからどれくらいずれるのが普通かを測ること。
個々の市区町村の値・順位は出力しない（系列ごとの集計だけ）。

主な指標
- MAD（平均絶対偏差）: Nigrini の目安で判定（第1桁 0.006/0.012/0.015、第2桁 0.008/0.010/0.012、先頭2桁 0.0012/0.0018/0.0022）
- カイ二乗適合度検定
比較の物差し
- 標本の揺れだけ：本当にベンフォードに従う数字を同じ件数だけ引いたときの MAD
- 桁の広がりだけ：その系列と同じ平均・標準偏差（log10）の対数正規から同じ件数を引いたときの MAD
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parents[1]
RES = BASE / "results"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(166)

MAIN = {
    "A1101": "総人口",
    "A7101": "世帯数",
    "A4101": "出生数",
    "C2108": "事業所数",
    "C2208": "従業者数",
    "D3201": "歳入決算総額",
    "D3203": "歳出決算総額",
    "D320101": "地方税",
    "D1202": "一般行政職員数",
    "B1101": "総面積",
}
TH = {"d1": (0.006, 0.012, 0.015), "d2": (0.008, 0.010, 0.012), "d12": (0.0012, 0.0018, 0.0022)}
LABEL = ["よく合う", "おおむね合う", "ぎりぎり", "合わない"]

P1 = np.log10(1 + 1 / np.arange(1, 10))
P2 = np.array([sum(np.log10(1 + 1 / (10 * a + b)) for a in range(1, 10)) for b in range(10)])
P12 = np.log10(1 + 1 / np.arange(10, 100))


def digits(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x) & (x > 0)]
    e = np.floor(np.log10(x))
    m = np.round(x / 10.0 ** e, 9)
    # 丸め誤差で 10.0 になったものを補正
    e = np.where(m >= 10, e + 1, e)
    m = np.where(m >= 10, m / 10, m)
    d12 = np.floor(m * 10 + 1e-9).astype(int)
    return d12 // 10, d12 % 10, d12, x


def freq(d, lo, hi):
    c = np.bincount(d, minlength=hi + 1)[lo:hi + 1]
    return c, c / c.sum()


def mad(obs_p, exp_p):
    return float(np.mean(np.abs(obs_p - exp_p)))


def judge(v, kind):
    t = TH[kind]
    return LABEL[int(np.searchsorted(t, v))]


def summarize(x):
    d1, d2, d12, xx = digits(x)
    c1, p1 = freq(d1, 1, 9)
    # 10未満の整数には第2桁がない（5 は 5.0 となり第2桁0に数えられてしまう）ので、第2桁・先頭2桁は10以上だけで数える
    big = xx >= 10
    c2, p2 = freq(d2[big], 0, 9)
    c12, p12 = freq(d12[big], 10, 99)
    n = len(xx)
    n2 = int(big.sum())
    chi = stats.chisquare(c1, P1 * n)
    lx = np.log10(xx)
    return {
        "n": n,
        "mad_d1": mad(p1, P1), "mad_d2": mad(p2, P2), "mad_d12": mad(p12, P12),
        "chi2_d1": float(chi.statistic), "p_d1": float(chi.pvalue),
        "p_d2": float(stats.chisquare(c2, P2 * n2).pvalue), "n2": n2,
        "share_below_10": float(np.mean(xx < 10)),
        "log10_mean": float(lx.mean()), "log10_sd": float(lx.std(ddof=1)),
        "orders_p5_p95": float(np.percentile(lx, 95) - np.percentile(lx, 5)),
        "p1": p1.tolist(), "p2": p2.tolist(),
    }


def benford_sample(n, size):
    """本当にベンフォードに従う数（log10 が一様）を引く。"""
    return 10 ** rng.uniform(0, 6, size=(size, n))


def mad_all_rows(X):
    """第1桁・第2桁・先頭2桁の MAD を行ごとに返す（10以上だけで第2桁を数える点も本番と同じ）。"""
    out = []
    for row in X:
        s = summarize(row)
        out.append((s["mad_d1"], s["mad_d2"], s["mad_d12"]))
    return np.array(out)


def mad_d1_rows(X):
    out = []
    for row in X:
        d1, _, _, _ = digits(row)
        out.append(mad(freq(d1, 1, 9)[1], P1))
    return np.array(out)


m26 = pd.read_csv(BASE / "data" / "muni_2026.csv", dtype={"area_code": str})
m21 = pd.read_csv(BASE / "data" / "muni_2021.csv", dtype={"area_code": str})
it26 = pd.read_csv(BASE / "data" / "items_2026.csv")
it21 = pd.read_csv(BASE / "data" / "items_2021.csv")

# ---- 1. 主な10系列 ------------------------------------------------------
rows, digit_rows = [], []
for code, name in MAIN.items():
    s = summarize(m26[code])
    # 標本の揺れだけ（1,000回、3つの桁の位置）
    nall = mad_all_rows(benford_sample(s["n"], 1000))
    null = nall[:, 0]
    # 桁の広がりだけ：同じ log10 平均・SD の対数正規（1,000回）
    ln = mad_d1_rows(10 ** rng.normal(s["log10_mean"], s["log10_sd"], size=(1000, s["n"])))
    rows.append({
        "code": code, "series": name, "n": s["n"], "n_d2": s["n2"], "share_below_10": s["share_below_10"],
        "mad_d1": s["mad_d1"], "judge_d1": judge(s["mad_d1"], "d1"),
        "mad_d2": s["mad_d2"], "judge_d2": judge(s["mad_d2"], "d2"),
        "mad_d12": s["mad_d12"], "judge_d12": judge(s["mad_d12"], "d12"),
        "chi2_d1": s["chi2_d1"], "p_d1": s["p_d1"], "p_d2": s["p_d2"],
        "log10_sd": s["log10_sd"], "orders_p5_p95": s["orders_p5_p95"],
        "null_mad_median": float(np.median(null)), "null_mad_p95": float(np.percentile(null, 95)),
        "null_mad_d2_p95": float(np.percentile(nall[:, 1], 95)), "null_mad_d12_median": float(np.median(nall[:, 2])),
        "null_mad_d12_p95": float(np.percentile(nall[:, 2], 95)),
        "null_judge_d12_share_ok": float(np.mean(nall[:, 2] < TH["d12"][1])),
        "lognorm_mad_median": float(np.median(ln)),
        "lognorm_mad_p05": float(np.percentile(ln, 5)), "lognorm_mad_p95": float(np.percentile(ln, 95)),
    })
    for d in range(9):
        digit_rows.append({"series": name, "digit": d + 1, "share": s["p1"][d], "benford": P1[d]})
main = pd.DataFrame(rows)
main.to_csv(RES / "main10_summary.csv", index=False)
pd.DataFrame(digit_rows).to_csv(RES / "main10_first_digit.csv", index=False)

# ---- 2. SSDSE-A の全項目（件数300以上、正の値） --------------------------
allrows = []
for code in m26.columns[1:]:
    x = m26[code]
    if (x > 0).sum() < 300:
        continue
    s = summarize(x)
    name = it26.loc[it26.code == code, "name"].iloc[0]
    is_ratio = "比率" in name
    allrows.append({"code": code, "name": name, "n": s["n"], "is_ratio": is_ratio, "share_below_10": s["share_below_10"],
                    "mad_d1": s["mad_d1"], "judge_d1": judge(s["mad_d1"], "d1"),
                    "mad_d2": s["mad_d2"], "judge_d2": judge(s["mad_d2"], "d2"),
                    "p_d1": s["p_d1"], "log10_sd": s["log10_sd"], "orders_p5_p95": s["orders_p5_p95"],
                    "main": code in MAIN})
allser = pd.DataFrame(allrows)
allser.to_csv(RES / "all_series_2026.csv", index=False)
cnt = allser[~allser.is_ratio]
rho = stats.spearmanr(cnt.log10_sd, cnt.mad_d1)

# ---- 3. 件数を変える（主な10系列から抜き出し、各1,000回） ----------------
ss_rows = []
for code, name in MAIN.items():
    x = m26[code].to_numpy(float)
    x = x[np.isfinite(x) & (x > 0)]
    for n in (50, 100, 200, 500, 1000):
        mads, rej = [], 0
        for _ in range(1000):
            sub = rng.choice(x, n, replace=False)
            d1, _, _, _ = digits(sub)
            c, p = freq(d1, 1, 9)
            mads.append(mad(p, P1))
            rej += stats.chisquare(c, P1 * n).pvalue < 0.05
        ss_rows.append({"series": name, "n": n, "mad_median": float(np.median(mads)), "reject_share": rej / 1000})
for n in (50, 100, 200, 500, 1000, 1741):
    X = benford_sample(n, 1000)
    mads, rej = [], 0
    for row in X:
        d1, _, _, _ = digits(row)
        c, p = freq(d1, 1, 9)
        mads.append(mad(p, P1))
        rej += stats.chisquare(c, P1 * n).pvalue < 0.05
    ss_rows.append({"series": "（本当のベンフォード）", "n": n, "mad_median": float(np.median(mads)), "reject_share": rej / 1000})
ss = pd.DataFrame(ss_rows)
ss.to_csv(RES / "sample_size.csv", index=False)

# ---- 4. 年を変える（SSDSE-A-2021、同じ項目） ------------------------------
yr_rows = []
for code, name in MAIN.items():
    if code not in m21.columns:
        continue
    s = summarize(m21[code])
    y21 = it21.loc[it21.code == code, "year"].iloc[0]
    y26 = it26.loc[it26.code == code, "year"].iloc[0]
    r26 = main.loc[main.code == code].iloc[0]
    yr_rows.append({"series": name, "year_old": y21, "mad_d1_old": s["mad_d1"], "judge_old": judge(s["mad_d1"], "d1"),
                    "year_new": y26, "mad_d1_new": r26.mad_d1, "judge_new": r26.judge_d1})
yr = pd.DataFrame(yr_rows)
yr.to_csv(RES / "year_compare.csv", index=False)

# ---- 5. 単位を変える（スケール不変性） --------------------------------------
sc_rows = []
for code, name in MAIN.items():
    x = m26[code].to_numpy(float)
    x = x[np.isfinite(x) & (x > 0)]
    base = summarize(x)["mad_d1"]
    k = 10 ** rng.uniform(0, 1, 200)  # 1〜10倍の200通り（円→ドルのような換算に相当）
    mads = [summarize(x * kk)["mad_d1"] for kk in k]
    sc_rows.append({"series": name, "mad_d1": base, "scaled_median": float(np.median(mads)),
                    "scaled_min": float(np.min(mads)), "scaled_max": float(np.max(mads)),
                    "share_judge_same": float(np.mean([judge(v, "d1") == judge(base, "d1") for v in mads]))})
sc = pd.DataFrame(sc_rows)
sc.to_csv(RES / "scale_invariance.csv", index=False)

# ---- まとめ -----------------------------------------------------------------
summary = {
    "n_municipalities": int(len(m26)),
    "main_judge_d1": main.judge_d1.value_counts().to_dict(),
    "main_judge_d2": main.judge_d2.value_counts().to_dict(),
    "main_judge_d12": main.judge_d12.value_counts().to_dict(),
    "main_p_d1_below_005": int((main.p_d1 < 0.05).sum()),
    "main_above_null_p95": int((main.mad_d1 > main.null_mad_p95).sum()),
    "main_above_null_d2_p95": int((main.mad_d2 > main.null_mad_d2_p95).sum()),
    "main_above_null_d12_p95": int((main.mad_d12 > main.null_mad_d12_p95).sum()),
    "null_d12_median_mean": float(main.null_mad_d12_median.mean()),
    "null_d12_share_judged_ok": float(main.null_judge_d12_share_ok.mean()),
    "main_within_lognorm_90": int(((main.mad_d1 >= main.lognorm_mad_p05) & (main.mad_d1 <= main.lognorm_mad_p95)).sum()),
    "all_series_count": int(len(allser)), "all_series_counts_only": int(len(cnt)),
    "all_counts_judge_d1": cnt.judge_d1.value_counts().to_dict(),
    "all_ratio_judge_d1": allser[allser.is_ratio].judge_d1.value_counts().to_dict(),
    "spearman_sd_vs_mad": [float(rho.statistic), float(rho.pvalue)],
    "counts_sd_lt_05_judge": cnt[cnt.log10_sd < 0.5].judge_d1.value_counts().to_dict(),
    "counts_sd_ge_05_judge": cnt[cnt.log10_sd >= 0.5].judge_d1.value_counts().to_dict(),
    "bad_counts": cnt[cnt.judge_d1 == "合わない"][["name", "log10_sd", "share_below_10", "mad_d1"]].round(3).values.tolist(),
    "counts_small_ge_10pct_judge": cnt[cnt.share_below_10 >= 0.1].judge_d1.value_counts().to_dict(),
    "counts_small_lt_10pct_judge": cnt[cnt.share_below_10 < 0.1].judge_d1.value_counts().to_dict(),
    "spearman_small_vs_mad": [float(v) for v in stats.spearmanr(cnt.share_below_10, cnt.mad_d1)],
    "year_same_judge": int((yr.judge_old == yr.judge_new).sum()), "year_n": int(len(yr)),
}
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250)
print(main[["series", "n", "mad_d1", "judge_d1", "mad_d2", "judge_d2", "mad_d12", "judge_d12", "p_d1",
            "log10_sd", "null_mad_p95", "lognorm_mad_median", "lognorm_mad_p05", "lognorm_mad_p95"]].round(4).to_string())
print(ss.pivot(index="series", columns="n", values="reject_share").round(2).to_string())
print(yr.round(4).to_string())
print(sc.round(4).to_string())
print(json.dumps(summary, ensure_ascii=False, indent=1))
