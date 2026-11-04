# F173 分析：2つの年の所得分布が「どれだけ動いたか」を、最適輸送（Wasserstein 距離）と分位点の差で比べる
# 実行：python src/03_分析.py （data/ の3ファイルだけを使う。乱数の種は固定）
import os, json
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from common import (SCHEMES, coarsen, fit_pchip_pareto, fit_uniform_pareto, fit_param, GRID)

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DATA, RES = os.path.join(ROOT, 'data'), os.path.join(ROOT, 'results')
os.makedirs(RES, exist_ok=True)
rng = np.random.default_rng(173)

bins = pd.read_csv(os.path.join(DATA, 'bins_long.csv'))
pub = pd.read_csv(os.path.join(DATA, 'published.csv')).set_index('year')
cpi = pd.read_csv(os.path.join(DATA, 'cpi_annual.csv')).set_index('year')
YEARS = sorted(bins.year.unique())
CUTS = SCHEMES['S25']
BASE_PRICE_YEAR = 2024

def shares_of(y):
    b = bins[bins.year == y].sort_values('lo')
    assert list(b.lo) == CUTS
    return b.share.values

# 物価の調整：所得の年の CPI（持家の帰属家賃を除く総合、暦年平均）で 2024年の価格にそろえる
def deflator(y, col='cpi_ex_rent'):
    return cpi.loc[BASE_PRICE_YEAR, col] / cpi.loc[y, col]

# 分位点関数 Q(u) を細かい u の格子の上で持つ（u は区間の中点。W1・W2 はこの平均で積分する）
NU = 20000
U = (np.arange(NU) + 0.5) / NU

def Q_from_dist(d):
    return d.ppf(U * d.F[-1])

def Q_midpoint(shares, cuts=CUTS, top_mult=1.5):
    s = np.asarray(shares, float); s = s / s.sum(); c = np.asarray(cuts, float)
    v = np.concatenate([(c[:-1] + c[1:]) / 2, [c[-1] * top_mult]])
    cum = np.cumsum(s); return v[np.searchsorted(cum, U).clip(0, len(v) - 1)]

def Q_capped(shares, cuts=CUTS, top_value=2000.0):
    """上の開いた階級を「全員 top_value」とみなす（裾の仮定を外したときの下限側の確認）"""
    s = np.asarray(shares, float); s = s / s.sum(); c = np.asarray(cuts, float)
    Fk = np.concatenate([[0], np.cumsum(s[:-1])])
    from scipy.interpolate import PchipInterpolator
    f = PchipInterpolator(c, Fk); xs = np.linspace(0, c[-1], 40001); Fs = f(xs)
    Fs = np.maximum.accumulate(Fs)
    q = np.interp(U, Fs, xs); q[U > Fk[-1]] = top_value
    return q

def get_Q(y, method='pchip', cuts_name='S25', real=True, cpi_col='cpi_ex_rent', shares=None):
    s = shares_of(y) if shares is None else shares
    cuts = SCHEMES[cuts_name]
    if cuts_name != 'S25': s = coarsen(CUTS, s, cuts)
    if method == 'pchip':     q = Q_from_dist(fit_pchip_pareto(cuts, s)[0])
    elif method == 'uniform': q = Q_from_dist(fit_uniform_pareto(cuts, s)[0])
    elif method == 'gb2':
        sm = fit_param(cuts, s, 'singh_maddala')[1]; dg = fit_param(cuts, s, 'dagum')[1]
        q = Q_from_dist(fit_param(cuts, s, 'gb2', [[sm[0], sm[1], 0.0, sm[2]], [dg[0], dg[1], dg[2], 0.0]])[0])
    elif method == 'midpoint': q = Q_midpoint(s, cuts)
    elif method == 'cap2000':  q = Q_capped(s, cuts, 2000.0)
    elif method == 'cap3000':  q = Q_capped(s, cuts, 3000.0)
    else: raise ValueError(method)
    return q * (deflator(y, cpi_col) if real else 1.0)

def cdf_on(q, x):
    """分位点関数から累積分布を作る（KS 用）"""
    return np.searchsorted(np.sort(q), x, side='right') / len(q)

XGRID = np.arange(0, 4000.01, 1.0)

def metrics(q1, q2, s1=None, s2=None):
    d = q2 - q1
    up, down = d.clip(min=0).mean(), (-d).clip(min=0).mean()
    w1 = np.abs(d).mean(); w2 = np.sqrt((d ** 2).mean()); dmu = d.mean()
    shape = (d - dmu); w2_shape = np.sqrt((shape ** 2).mean())
    lw1 = np.abs(np.log(np.maximum(q2, 1)) - np.log(np.maximum(q1, 1))).mean()
    # 上位1%の部分が W1 にどれだけ寄与しているか
    top1 = np.abs(d[U > 0.99]).sum() / NU / w1 if w1 > 0 else np.nan
    ks = np.max(np.abs(cdf_on(q1, XGRID) - cdf_on(q2, XGRID)))
    out = dict(W1=w1, up=up, down=down, dmean=dmu, W2=w2, W2_shape=w2_shape,
               shape_share_W2sq=(w2_shape ** 2) / (w2 ** 2) if w2 > 0 else np.nan,
               logW1=lw1, top1_share_of_W1=top1, KS=ks,
               dmedian=np.median(q2) - np.median(q1))
    if s1 is not None:
        a, b = np.asarray(s1) / np.sum(s1), np.asarray(s2) / np.sum(s2)
        out['TV_bins'] = 0.5 * np.abs(a - b).sum()
        out['Hellinger_bins'] = np.sqrt(0.5 * ((np.sqrt(a) - np.sqrt(b)) ** 2).sum())
    return out

# ---------- 0. 分位点関数の答え合わせ（名目、公表の五分位値・中央値・平均と比べる） ----------
chk = []
for y in YEARS:
    q = get_Q(y, real=False)
    for name, u in [('p20', .2), ('p40', .4), ('median', .5), ('p60', .6), ('p80', .8)]:
        est = np.quantile(q, u); chk.append(dict(year=y, stat=name, published=pub.loc[y, name], estimate=est))
    chk.append(dict(year=y, stat='mean', published=pub.loc[y, 'mean'], estimate=q.mean()))
chk = pd.DataFrame(chk); chk['rel_err_pct'] = 100 * (chk.estimate / chk.published - 1)
chk.to_csv(os.path.join(RES, 'check_vs_published.csv'), index=False)

# ---------- 1. 主な比較：各年の分位点関数（実質、単調スプライン＋パレート） ----------
QS = {y: get_Q(y) for y in YEARS}
QS_nom = {y: get_Q(y, real=False) for y in YEARS}
pairs_main = [(1994, 2024), (1985, 2024), (2004, 2024), (2014, 2024), (1985, 1994), (1994, 2004), (2004, 2014), (2014, 2024), (2021, 2024)]
rows = []
for a, b in pairs_main:
    for lab, Qd in [('real', QS), ('nominal', QS_nom)]:
        m = metrics(Qd[a], Qd[b], shares_of(a), shares_of(b)); m.update(y1=a, y2=b, price=lab); rows.append(m)
pairs = pd.DataFrame(rows); pairs.to_csv(os.path.join(RES, 'pairs_main.csv'), index=False)

# 分位点ごとの差（1994→2024、実質）。図2と、公表値どうしの差との比較に使う
a, b = 1994, 2024
prof = pd.DataFrame(dict(u=U, q1994=QS[a], q2024=QS[b], diff=QS[b] - QS[a]))
prof.iloc[::20].to_csv(os.path.join(RES, 'profile_1994_2024.csv'), index=False)
pubdiff = []
for name, u in [('p20', .2), ('p40', .4), ('median', .5), ('p60', .6), ('p80', .8)]:
    pubdiff.append(dict(stat=name, u=u,
                        published_diff_real=pub.loc[b, name] * deflator(b) - pub.loc[a, name] * deflator(a),
                        estimated_diff_real=np.quantile(QS[b], u) - np.quantile(QS[a], u)))
pubdiff.append(dict(stat='mean', u=np.nan, published_diff_real=pub.loc[b, 'mean'] * deflator(b) - pub.loc[a, 'mean'] * deflator(a),
                    estimated_diff_real=QS[b].mean() - QS[a].mean()))
pd.DataFrame(pubdiff).to_csv(os.path.join(RES, 'profile_vs_published_1994_2024.csv'), index=False)

# 十分位ごとの、上向き・下向きの寄与（どこの世帯の位置が、どちら向きに動いたか）
dec = []
for k in range(10):
    m = (U >= k / 10) & (U < (k + 1) / 10); d = (QS[b] - QS[a])[m]
    dec.append(dict(decile=k + 1, mean_diff=d.mean(), share_of_W1=np.abs(d).sum() / NU / np.abs(QS[b] - QS[a]).mean()))
pd.DataFrame(dec).to_csv(os.path.join(RES, 'deciles_1994_2024.csv'), index=False)

# ---------- 2. 年×年の距離の表（実質 W1）と、前の年からの動き ----------
Y = YEARS; n = len(Y); W = np.zeros((n, n))
for i in range(n):
    for j in range(i + 1, n):
        W[i, j] = W[j, i] = np.abs(QS[Y[j]] - QS[Y[i]]).mean()
pd.DataFrame(W, index=Y, columns=Y).round(2).to_csv(os.path.join(RES, 'W1_matrix_real.csv'))

seq = []
for i in range(1, n):
    a_, b_ = Y[i - 1], Y[i]
    m = metrics(QS[a_], QS[b_], shares_of(a_), shares_of(b_)); m.update(y1=a_, y2=b_); seq.append(m)
seq = pd.DataFrame(seq); seq.to_csv(os.path.join(RES, 'consecutive_years.csv'), index=False)

# 1994年からの動き（各年 vs 1994）
from94 = []
for y in Y:
    m = metrics(QS[1994], QS[y], shares_of(1994), shares_of(y)); m.update(year=y); from94.append(m)
pd.DataFrame(from94).to_csv(os.path.join(RES, 'from_1994.csv'), index=False)

# ---------- 3. 頑健性 ----------
# 3a. 階級の扱い（分布のつなぎ方・上の裾）と、階級の粗さ
rob = []
for meth in ['pchip', 'uniform', 'gb2', 'midpoint', 'cap2000', 'cap3000']:
    q1, q2 = get_Q(1994, meth), get_Q(2024, meth)
    m = metrics(q1, q2); m.update(check='method', variant=meth); rob.append(m)
for cn in ['S14', 'S8', 'S5', 'S21top1000']:
    q1, q2 = get_Q(1994, 'pchip', cn), get_Q(2024, 'pchip', cn)
    m = metrics(q1, q2); m.update(check='coarsen', variant=cn); rob.append(m)
for col in ['cpi_all']:
    q1, q2 = get_Q(1994, cpi_col=col), get_Q(2024, cpi_col=col)
    m = metrics(q1, q2); m.update(check='deflator', variant=col); rob.append(m)
# 上位1%を除いた範囲（u<0.99）だけで測る
d = QS[2024] - QS[1994]; mm = U < 0.99
rob.append(dict(check='trim', variant='u<0.99', W1=np.abs(d[mm]).mean(), up=d[mm].clip(min=0).mean(),
                down=(-d[mm]).clip(min=0).mean(), dmean=d[mm].mean()))
rob = pd.DataFrame(rob); rob.to_csv(os.path.join(RES, 'robustness_1994_2024.csv'), index=False)

# 3b. 距離の種類：前の年からの動きを、どの距離で測ると、どの年が「大きく動いた」になるか
cols = ['W1', 'W2', 'logW1', 'KS', 'TV_bins', 'Hellinger_bins']
seq_abs = seq.assign(abs_dmean=seq.dmean.abs(), abs_dmedian=seq.dmedian.abs())
cc = []
for c1 in cols + ['abs_dmean', 'abs_dmedian']:
    row = {'metric': c1}
    for c2 in cols + ['abs_dmean', 'abs_dmedian']:
        row[c2] = spearmanr(seq_abs[c1], seq_abs[c2]).correlation
    cc.append(row)
pd.DataFrame(cc).to_csv(os.path.join(RES, 'metric_rank_corr_consecutive.csv'), index=False)
top3 = {c: seq_abs.sort_values(c, ascending=False).head(3).apply(lambda r: f"{int(r.y1)}→{int(r.y2)}", axis=1).tolist()
        for c in cols + ['abs_dmean', 'abs_dmedian']}

# 3c. 年の選び方：基準の年を変えて「2024年との距離」の大きさと向き
base = []
for y0 in [1985, 1990, 1994, 1997, 2000, 2005, 2010, 2015]:
    m = metrics(QS[y0], QS[2024]); m.update(base=y0); base.append(m)
pd.DataFrame(base).to_csv(os.path.join(RES, 'base_year_vs_2024.csv'), index=False)

# 3d. 数字の揺れの目安：0.1%単位の四捨五入と、標本の大きさ（2,000/5,000/20,000世帯）による「動いていなくても出る距離」
#     答え：2024年の分布（単調スプライン＋パレート）から世帯を引き、25階級・0.1%単位にして、もう一度推定
d24, _ = fit_pchip_pareto(CUTS, shares_of(2024)); q24 = QS[2024]
noise = []
for nhh in [2000, 5000, 20000]:
    vals = []
    for r in range(80):
        x = d24.ppf(rng.random(nhh) * d24.F[-1])
        idx = np.searchsorted(CUTS, x, side='right') - 1
        s = np.bincount(idx, minlength=len(CUTS)) / nhh * 100
        s = np.round(s, 1)
        q = get_Q(2024, shares=s)
        vals.append(np.abs(q - q24).mean())
    noise.append(dict(households=nhh, W1_mean=np.mean(vals), W1_p95=np.quantile(vals, .95)))
pd.DataFrame(noise).to_csv(os.path.join(RES, 'noise_floor.csv'), index=False)

# 3e. 前後3年の平均の割合で比べ直す（1年ごとの揺れをならす）：1993〜95年 vs 2022〜24年
def avgQ(ys):
    s = np.mean([shares_of(y) * 1.0 for y in ys], axis=0)
    dfl = np.mean([deflator(y) for y in ys])
    return Q_from_dist(fit_pchip_pareto(CUTS, s)[0]) * dfl
m3 = metrics(avgQ([1993, 1994, 1995]), avgQ([2022, 2023, 2024])); m3.update(check='3yr_avg', variant='1993-95 vs 2022-24')
pd.DataFrame([m3]).to_csv(os.path.join(RES, 'three_year_avg.csv'), index=False)

summary = dict(
    check_max_abs_err_pct=chk.groupby('stat').rel_err_pct.apply(lambda s: float(s.abs().max())).to_dict(),
    check_median_abs_err_pct=chk.groupby('stat').rel_err_pct.apply(lambda s: float(s.abs().median())).to_dict(),
    pair_1994_2024_real=pairs[(pairs.y1 == 1994) & (pairs.y2 == 2024) & (pairs.price == 'real')].iloc[0].to_dict(),
    top3_by_metric=top3,
    consecutive_W1_median=float(seq.W1.median()), consecutive_W1_max=float(seq.W1.max()),
)
with open(os.path.join(RES, 'summary.json'), 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=1, default=float)
print(json.dumps(summary, ensure_ascii=False, indent=1, default=float))

# ---------- 4. すべての年の組（741組）で、W1 が平均の差より大きくなるのはどんなときか ----------
#   1次元の W1 = ∫|Q2−Q1|du、平均の差 = ∫(Q2−Q1)du。分位点関数が交わらなければ（どの分位点も同じ向きに動けば）両者は一致する
allp = []
for lab, Qd in [('real', QS), ('nominal', QS_nom)]:
    for i in range(n):
        for j in range(i + 1, n):
            q1, q2 = Qd[Y[i]], Qd[Y[j]]; d = q2 - q1
            w1 = np.abs(d).mean(); dm = d.mean()
            up, down = d.clip(min=0).mean(), (-d).clip(min=0).mean()
            # 形だけの距離：平均で割ってから比べる（水準をそろえたあとの「形の違い」。単位は平均の何倍か）
            wn = np.abs(q2 / q2.mean() - q1 / q1.mean()).mean()
            # 比で見た動き：log の分位点の差（何%動いたか）
            dl = np.log(np.maximum(q2, 1)) - np.log(np.maximum(q1, 1))
            allp.append(dict(price=lab, y1=Y[i], y2=Y[j], gap=Y[j] - Y[i], W1=w1, abs_dmean=abs(dm), up=up, down=down,
                             ratio=w1 / abs(dm) if abs(dm) > 0 else np.inf,
                             minor_share=min(up, down) / w1 if w1 > 0 else 0,
                             W1_shape_norm=wn, logW1=np.abs(dl).mean(), abs_mean_dlog=abs(dl.mean()),
                             dlog_p10=np.log(np.quantile(q2, .1) / np.quantile(q1, .1)),
                             dlog_p90=np.log(np.quantile(q2, .9) / np.quantile(q1, .9))))
allp = pd.DataFrame(allp); allp.to_csv(os.path.join(RES, 'all_pairs.csv'), index=False)
cross = allp.groupby('price').apply(lambda g: pd.Series(dict(
    pairs=len(g), cross_1pct=(g.minor_share > 0.01).mean(), cross_10pct=(g.minor_share > 0.10).mean(),
    ratio_median=g.ratio.replace(np.inf, np.nan).median(), ratio_p90=g.ratio.replace(np.inf, np.nan).quantile(.9),
    log_cross_10pct=((g.logW1 - g.abs_mean_dlog) / g.logW1 > 0.10).mean())))
cross.to_csv(os.path.join(RES, 'crossing_summary.csv'))
print(cross)
