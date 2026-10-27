"""03 分析：都道府県の順位はどれくらい当てにならないか。

1. 年ごとの順位の相関（スピアマン）と、上位5・上位10の入れ替わり
2. 都道府県ごとの順位の幅（7回の最高位と最低位）
3. 標本誤差だけから見た順位の幅（パラメトリック・ブートストラップ）
4. 公表値（整数）での同点の多さ
5. 全国との差の分散を「ずっと続く差」「年ごとの揺れ」「標本誤差」に分ける
6. 同じ学年（小6 → 3年後の中3）の順位の相関
7. 頑健性
"""
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(59)

df = pd.read_csv(ROOT / "data/pref_scores.csv")
SERIES = [("小", "国語"), ("小", "算数・数学"), ("中", "国語"), ("中", "算数・数学")]
YEARS = sorted(df.year.unique())


def wide(lv, sb, col="rate", d=df):
    x = d[(d.level == lv) & (d.subject == sb)]
    return x.pivot(index="pref_code", columns="year", values=col)


out = {}

# 1 年ごとの順位の相関
rows = []
for lv, sb in SERIES:
    w = wide(lv, sb)
    for a, b in combinations(YEARS, 2):
        rows.append(dict(level=lv, subject=sb, y1=a, y2=b, spearman=stats.spearmanr(w[a], w[b])[0],
                         kendall=stats.kendalltau(w[a], w[b])[0], consecutive=YEARS.index(b) - YEARS.index(a) == 1))
cor = pd.DataFrame(rows)
cor.to_csv(RES / "rank_correlations.csv", index=False)
cons = cor[cor.consecutive].groupby(["level", "subject"])[["spearman", "kendall"]].mean()
out["連続する回のスピアマン（系列ごとの平均）"] = cons.round(3).to_dict()
out["連続する回のスピアマン（全体の平均・最小・最大）"] = [round(cor[cor.consecutive].spearman.mean(), 3),
                                          round(cor[cor.consecutive].spearman.min(), 3), round(cor[cor.consecutive].spearman.max(), 3)]
out["2019と2026のスピアマン（系列ごと）"] = cor[(cor.y1 == 2019) & (cor.y2 == 2026)].set_index(["level", "subject"]).spearman.round(3).to_dict()

# 上位5・上位10が次の回も残る割合、中位（16〜32位）が上位10に入る割合
keep = []
for lv, sb in SERIES:
    w = wide(lv, sb)
    r = w.rank(ascending=False)
    for a, b in zip(YEARS[:-1], YEARS[1:]):
        for k in (5, 10):
            top_a = set(r.index[r[a] <= k]); top_b = set(r.index[r[b] <= k])
            keep.append(dict(level=lv, subject=sb, y1=a, k=k, stay=len(top_a & top_b) / k))
        bot_a = set(r.index[r[a] > 37]); bot_b = set(r.index[r[b] > 37])
        keep.append(dict(level=lv, subject=sb, y1=a, k="下位10", stay=len(bot_a & bot_b) / 10))
keep = pd.DataFrame(keep)
keep.to_csv(RES / "top_retention.csv", index=False)
out["次の回も残る割合（平均）"] = keep.groupby("k").stay.mean().round(3).to_dict()

# 2 都道府県ごとの順位の幅
rr = []
for lv, sb in SERIES:
    r = wide(lv, sb).rank(ascending=False)
    rr.append(pd.DataFrame(dict(level=lv, subject=sb, pref_code=r.index, mean_rank=r.mean(1), best=r.min(1), worst=r.max(1),
                                range=r.max(1) - r.min(1), sd_rank=r.std(1))))
rr = pd.concat(rr)
rr.to_csv(RES / "rank_range_by_pref.csv", index=False)
rr["band"] = pd.cut(rr.mean_rank, [0, 10, 37, 48], labels=["上位10付近", "中位", "下位10付近"])
out["7回の順位の幅（中央値）"] = float(rr.range.median())
out["順位の幅の中央値（平均順位の帯ごと）"] = rr.groupby("band", observed=True).range.median().to_dict()
out["順位の幅が20位以上の割合"] = round(float((rr.range >= 20).mean()), 3)
out["平均順位と順位の幅の相関（中位ほど広いか：|平均順位-24|との相関）"] = round(float(stats.spearmanr((rr.mean_rank - 24).abs(), rr.range)[0]), 3)

# 3 標本誤差だけから見た順位の幅
B = 2000
bs = []
for (y, lv, sb), x in df.groupby(["year", "level", "subject"]):
    sim = x.rate.values[None, :] + rng.normal(size=(B, len(x))) * x.se_rate.values[None, :]
    ranks = (-sim).argsort(1).argsort(1) + 1
    lo, hi = np.percentile(ranks, [5, 95], axis=0)
    bs.append(pd.DataFrame(dict(year=y, level=lv, subject=sb, pref_code=x.pref_code.values, rank=x["rank"].values,
                                lo=lo, hi=hi, width=hi - lo, se=x.se_rate.values)))
bs = pd.concat(bs)
bs.to_csv(RES / "rank_interval_sampling.csv", index=False)
# 年ごとの順位の変化の大きさ（中央値）と比べる
chg = []
for lv, sb in SERIES:
    r = wide(lv, sb).rank(ascending=False)
    chg.append((r.diff(axis=1).abs()).stack())
chg = pd.concat(chg)
out["標本誤差による順位の90%幅（中央値）"] = float(bs.width.median())
out["標本誤差による順位の90%幅（90%点）"] = float(bs.width.quantile(.9))
out["前回からの順位の変化（中央値・平均）"] = [float(chg.median()), round(float(chg.mean()), 2)]
out["正答率の標準誤差（中央値, pt）"] = round(float(df.se_rate.median()), 3)

# 4 公表値（整数）での同点
tie = []
for (y, lv, sb), x in df.groupby(["year", "level", "subject"]):
    vc = x.rate_pub.value_counts()
    tie.append(dict(year=y, level=lv, subject=sb, distinct=len(vc), share_tied=float((x.rate_pub.map(vc) > 1).mean()),
                    max_group=int(vc.max()), within1=float((x["diff"].abs() < 1).mean()),
                    within2=float((x["diff"].abs() < 2).mean()), gap_med=float(np.median(np.diff(np.sort(x.rate.values))))))
tie = pd.DataFrame(tie)
tie.to_csv(RES / "ties_published.csv", index=False)
out["公表値（整数）の異なる値の数（平均）"] = round(tie.distinct.mean(), 1)
out["同点の県がある割合（平均）"] = round(tie.share_tied.mean(), 3)
out["全国との差が±1pt未満の県の割合（平均）"] = round(tie.within1.mean(), 3)
out["全国との差が±2pt未満の県の割合（平均）"] = round(tie.within2.mean(), 3)
out["隣り合う順位の正答率の差（中央値, pt）"] = round(float(tie.gap_med.median()), 3)

# 5 全国との差の分散分解
dec = []
for lv, sb in SERIES:
    d = wide(lv, sb, "diff")
    se2 = wide(lv, sb, "se_rate") ** 2
    T = d.shape[1]
    within = d.sub(d.mean(1), axis=0).pow(2).sum(1).sum() / (d.shape[0] * (T - 1))
    samp = float(se2.values.mean())
    between_obs = d.mean(1).var(ddof=1)
    persist = between_obs - within / T
    dec.append(dict(level=lv, subject=sb, persistent=persist, year_to_year=within - samp, sampling=samp,
                    share_persist=persist / (persist + within), icc=persist / (persist + within),
                    yearly_sd=np.sqrt(within), sampling_sd=np.sqrt(samp)))
dec = pd.DataFrame(dec)
dec.to_csv(RES / "variance_decomposition.csv", index=False)
out["分散分解（ずっと続く差の割合）"] = dec.set_index(["level", "subject"]).share_persist.round(3).to_dict()
out["年ごとの揺れのSD（pt）"] = dec.set_index(["level", "subject"]).yearly_sd.round(2).to_dict()
out["標本誤差のSD（pt）"] = dec.set_index(["level", "subject"]).sampling_sd.round(3).to_dict()

# 6 同じ学年：小6（t）→ 中3（t+3）
coh = []
for sb in ["国語", "算数・数学"]:
    p = wide("小", sb); m = wide("中", sb)
    for y in YEARS:
        if y + 3 in m.columns:
            coh.append(dict(subject=sb, p_year=y, m_year=y + 3, spearman=stats.spearmanr(p[y], m[y + 3])[0],
                            same_year_m=stats.spearmanr(m[y], m[y + 3])[0] if y in m.columns else np.nan))
coh = pd.DataFrame(coh)
coh.to_csv(RES / "cohort_correlations.csv", index=False)
out["小6→3年後の中3のスピアマン（平均）"] = round(coh.spearman.mean(), 3)
out["同じ年の中3→3年後の中3のスピアマン（平均）"] = round(coh.same_year_m.mean(), 3)

# 同じ年の教科間・学校種間
cross = []
for y in YEARS:
    a = wide("小", "国語")[y]; b = wide("小", "算数・数学")[y]; c = wide("中", "国語")[y]; e = wide("中", "算数・数学")[y]
    cross.append(dict(year=y, p_kokugo_sansu=stats.spearmanr(a, b)[0], m_kokugo_sugaku=stats.spearmanr(c, e)[0],
                      p_m_kokugo=stats.spearmanr(a, c)[0], p_m_math=stats.spearmanr(b, e)[0]))
cross = pd.DataFrame(cross)
cross.to_csv(RES / "cross_subject.csv", index=False)
out["同じ年の教科間・学校種間のスピアマン（平均）"] = cross.drop(columns="year").mean().round(3).to_dict()

# 7 頑健性：連続する回のスピアマンの平均
rob = {}
c = cor[cor.consecutive]
rob["基本（小数の正答率）"] = c.spearman.mean()
rows = []
for lv, sb in SERIES:
    w = wide(lv, sb, "rate_pub")
    for a, b in zip(YEARS[:-1], YEARS[1:]):
        rows.append(stats.spearmanr(w[a], w[b])[0])
rob["公表値（整数、同点あり）"] = np.mean(rows)
rob["ケンドールのτ"] = c.kendall.mean()
rob["2026年度を除く"] = c[c.y2 < 2026].spearman.mean()
rob["2019年度を除く（コロナ後のみ）"] = c[c.y1 > 2019].spearman.mean()
# 平均で上下3県を除く
rows = []
for lv, sb in SERIES:
    w = wide(lv, sb)
    keep_idx = w.mean(1).rank().between(4, 44)
    w = w[keep_idx]
    for a, b in zip(YEARS[:-1], YEARS[1:]):
        rows.append(stats.spearmanr(w[a], w[b])[0])
rob["平均の上下3県を除く（41県）"] = np.mean(rows)
# 全国との差を年ごとのSDで割った z でも同じ（順位は不変）→ 代わりに2回おき
rob["2回あと（t→t+2）"] = cor[cor.y2.map(YEARS.index) - cor.y1.map(YEARS.index) == 2].spearman.mean()
rob["国語のみ"] = c[c.subject == "国語"].spearman.mean()
rob["算数・数学のみ"] = c[c.subject == "算数・数学"].spearman.mean()
rob = {k: round(float(v), 3) for k, v in rob.items()}
pd.Series(rob).to_csv(RES / "robustness.csv", header=["mean_spearman_consecutive"])
out["頑健性（連続する回のスピアマンの平均）"] = rob

import json


def fix(o):
    if isinstance(o, dict):
        return {("/".join(map(str, k)) if isinstance(k, tuple) else str(k)): fix(v) for k, v in o.items()}
    return o


out = fix(out)
(RES / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
