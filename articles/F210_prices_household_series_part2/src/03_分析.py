"""03 分析
A 円安が品目の値段に届くまでの時間（局所射影, 2015/1〜2026/9）
B 家計と企業の物価の見通し（2014/3〜2026/9, 四半期）
"""
import os, json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')

np.random.seed(0)
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(H, 'data')
R = os.path.join(H, 'results')
os.makedirs(R, exist_ok=True)
HMAX = 24
P = pd.read_csv(os.path.join(D, 'monthly_panel.csv'), index_col=0)
P.index = pd.PeriodIndex(P.index, freq='M')
SPECIAL = ['2019-10', '2020-04', '2021-04', '2023-02']  # 消費税、幼保・高等教育の無償化、携帯料金、電気・ガスの補助


def lp(y, x, ctrl, hmax=HMAX, nlag=3, sample=None, hs=None):
    """y, x: 対数水準(×100)。h ごとに y_{t+h}-y_{t-1} を Δx_t に回帰。
    コントロール：Δx・Δy のラグ nlag、ctrl（Δの外生変数, 当月とラグ）、月ダミー、特殊月ダミー"""
    dy = y.diff(); dx = x.diff()
    base = pd.DataFrame({'dx': dx})
    for k in range(1, nlag + 1):
        base[f'dx{k}'] = dx.shift(k); base[f'dy{k}'] = dy.shift(k)
    for c in ctrl:
        dc = c.diff()
        base[f'{c.name}_0'] = dc
        for k in range(1, nlag + 1):
            base[f'{c.name}_{k}'] = dc.shift(k)
    md = pd.get_dummies(base.index.month, prefix='m', drop_first=True).astype(float)
    md.index = base.index
    base = base.join(md)
    for s in SPECIAL:
        base['sp' + s] = (base.index == pd.Period(s, 'M')).astype(float)
    out = []
    for h in (hs if hs is not None else range(hmax + 1)):
        lhs = y.shift(-h) - y.shift(1)
        df = base.copy(); df['lhs'] = lhs
        if sample is not None:
            df = df[(df.index >= pd.Period(sample[0], 'M')) & (df.index <= pd.Period(sample[1], 'M'))]
        df = df.dropna()
        df = df.loc[:, df.std() > 0] if len(df) else df
        if len(df) < 30 or 'dx' not in df:
            out.append((h, np.nan, np.nan, 0)); continue
        X = sm.add_constant(df.drop(columns='lhs'), has_constant='add')
        r = sm.OLS(df['lhs'], X).fit(cov_type='HAC', cov_kwds={'maxlags': h + 1})
        out.append((h, r.params['dx'], r.bse['dx'], len(df)))
    return pd.DataFrame(out, columns=['h', 'b', 'se', 'n'])


lg = lambda s: 100 * np.log(s)
fx = lg(P['usdjpy']).rename('fx')
impc = lg(P['imp_contract']).rename('impc')
impy = lg(P['imp_yen']).rename('impy')

# 為替自身の反応（1か月の1%円安が、その後どれだけ続くか）で割ってパススルー率にする
fxself = lp(fx, fx, [impc])
fxself.to_csv(os.path.join(R, 'A0_fx_self.csv'), index=False)


_SELF = {}


def passthrough(y, driver=fx, ctrl=(impc,), sample=None, nlag=3):
    a = lp(y, driver, list(ctrl), sample=sample, nlag=nlag)
    key = (driver.name, tuple(c.name for c in ctrl), sample, nlag)
    if key not in _SELF:
        _SELF[key] = lp(driver, driver, list(ctrl), sample=sample, nlag=nlag)
    s = _SELF[key]
    a['fx_cum'] = s['b']
    a['pt'] = a['b'] / s['b']
    a['pt_se'] = a['se'] / s['b']
    return a


GROUPS = ['総合', '輸入物価（円）', '食料工業製品', '他の工業製品', '耐久消費財', '石油製品', '電気・都市ガス・水道', '外食', 'サービス']
rows = []
for gname in GROUPS:
    if gname == '輸入物価（円）':
        a = passthrough(impy, ctrl=())  # 円ベースの輸入物価は契約通貨×為替なので、契約通貨では調整しない
    else:
        a = passthrough(lg(P[gname]))
    a['group'] = gname
    rows.append(a)
A = pd.concat(rows)
A.to_csv(os.path.join(R, 'A1_group_passthrough.csv'), index=False)


def half_time(pt):
    """24か月後のパススルーの半分に初めて届いた月（24か月後が正のときだけ）"""
    pt = np.asarray(pt)
    end = np.nanmean(pt[-3:])  # 22〜24か月後の平均を「行き着く先」とする
    if not np.isfinite(end) or end <= 0:
        return np.nan, end
    for h, v in enumerate(pt):
        if v >= end / 2:
            return h, end
    return np.nan, end


summ = []
for gname, a in A.groupby('group', sort=False):
    ht, end = half_time(a.pt.values)
    a12 = a[a.h == 12].iloc[0]; a24 = a[a.h == 24].iloc[0]
    summ.append(dict(group=gname, pt12=a12.pt, pt12_lo=a12.pt - 1.96 * a12.pt_se, pt12_hi=a12.pt + 1.96 * a12.pt_se,
                     pt24=a24.pt, pt24_lo=a24.pt - 1.96 * a24.pt_se, pt24_hi=a24.pt + 1.96 * a24.pt_se,
                     end=end, half_month=ht))
S = pd.DataFrame(summ)
S.to_csv(os.path.join(R, 'A2_group_summary.csv'), index=False)

# --- 品目別（F209 の582品目のうち、中分類・類を除いた品目）
IT = pd.read_csv(os.path.join(D, 'items_monthly.csv.gz'), index_col=0)
IT.index = pd.PeriodIndex(IT.index, freq='M')
meta = pd.read_csv(os.path.join(D, 'raw', 'f209_item_contrib_2020_2025.csv'))
meta['col'] = meta['key']
meta = meta[meta.col.isin(IT.columns)]
res = []
for _, r in meta.iterrows():
    s = IT[r.col]
    if s.isna().sum() > 6 or (s <= 0).any():
        continue
    a = passthrough(lg(s))
    ht, end = half_time(a.pt.values)
    a24 = a[a.h == 24].iloc[0]; a12 = a[a.h == 12].iloc[0]
    res.append(dict(item=r['item'], code=r['code'], top=r['top'], mid=r['mid'], w=r['w'], chg_2020_2025=r['chg_pct'],
                    pt12=a12.pt, pt24=a24.pt, pt24_se=a24.pt_se, t24=a24.pt / a24.pt_se if a24.pt_se > 0 else np.nan,
                    end=end, half_month=ht))
I = pd.DataFrame(res)
I.to_csv(os.path.join(R, 'A3_item_passthrough.csv'), index=False)

# 品目の要約
sig = I[(I.t24 > 1.96)]
iw = I.w / I.w.sum()
item_sum = dict(n_items=int(len(I)), n_sig_pos=int(len(sig)), n_sig_neg=int((I.t24 < -1.96).sum()),
                share_w_sig_pos=float(I.loc[I.t24 > 1.96, 'w'].sum() / I.w.sum()),
                median_half_sig=float(sig.half_month.median()) if len(sig) else None,
                q25_half_sig=float(sig.half_month.quantile(.25)) if len(sig) else None,
                q75_half_sig=float(sig.half_month.quantile(.75)) if len(sig) else None,
                weighted_pt24=float((I.pt24 * iw).sum()))
by_top = I.assign(sig=I.t24 > 1.96).groupby('top').apply(
    lambda d: pd.Series(dict(n=len(d), n_sig=int(d.sig.sum()), w_share=d.w.sum() / I.w.sum(),
                             pt24_w=(d.pt24 * d.w).sum() / d.w.sum(),
                             half_med=d.loc[d.sig, 'half_month'].median())), include_groups=False).reset_index()
by_top.to_csv(os.path.join(R, 'A4_item_by_top.csv'), index=False)
top_items = sig.sort_values('pt24', ascending=False).head(15)
top_items.to_csv(os.path.join(R, 'A5_item_top15.csv'), index=False)

# 品目の「届く速さ」と、2020→2025年の値上がりの関係
cc = I.dropna(subset=['pt24', 'chg_2020_2025'])
rho_pt_chg = float(cc[['pt24', 'chg_2020_2025']].corr(method='spearman').iloc[0, 1])

# --- 頑健性（総合・食料工業製品・他の工業製品の24か月後）
rob = []
for gname in ['総合', '食料工業製品', '他の工業製品', '耐久消費財', '石油製品', '電気・都市ガス・水道']:
    y = lg(P[gname])
    specs = {
        '基本（ドル円、契約通貨の輸入物価で調整、ラグ3）': passthrough(y),
        '輸入物価（円ベース）を起点にする': passthrough(y, driver=impy, ctrl=()),
        '契約通貨の輸入物価で調整しない': passthrough(y, ctrl=()),
        'ラグ6': passthrough(y, nlag=6),
        '2015〜2021年だけ': passthrough(y, sample=('2015-01', '2021-12')),
        '2018年以降だけ': passthrough(y, sample=('2018-01', '2026-09')),
    }
    for k, a in specs.items():
        r12 = a[a.h == 12].iloc[0]; r24 = a[a.h == 24].iloc[0]
        ht, end = half_time(a.pt.values)
        rob.append(dict(group=gname, spec=k, pt12=r12.pt, pt24=r24.pt, pt24_se=r24.pt_se, half_month=ht))
ROB = pd.DataFrame(rob)
ROB.to_csv(os.path.join(R, 'A6_robustness.csv'), index=False)

# 品目数の数え方（|t|>1.96 の基準）の頑健性：ブロック並べ替え（為替の系列を12か月ブロックで並べ替えた偽の為替）
def perm_count(nperm=100, seed=0):
    rng = np.random.default_rng(seed)
    dfx = fx.diff()
    blocks = [dfx.iloc[i:i + 12] for i in range(1, len(dfx), 12)]
    cnts = []
    sample_items = meta.sample(n=min(150, len(meta)), random_state=seed)
    for p in range(nperm):
        order = rng.permutation(len(blocks))
        sh = pd.concat([blocks[i].reset_index(drop=True) for i in order]).values[:len(dfx) - 1]
        fake = pd.Series(np.r_[fx.iloc[0], fx.iloc[0] + np.cumsum(sh)], index=fx.index, name='fx')
        c = 0; n = 0
        sf = lp(fake, fake, [impc], hs=[24])
        for _, r in sample_items.iterrows():
            s = IT[r.col]
            if s.isna().sum() > 6 or (s <= 0).any():
                continue
            a = lp(lg(s), fake, [impc], hs=[24])
            b, se = a.iloc[-1].b / sf.iloc[-1].b, a.iloc[-1].se / sf.iloc[-1].b
            n += 1; c += int(b / se > 1.96) if se > 0 else 0
        cnts.append(c / n)
    return np.array(cnts), n


# 実測（同じ120品目）
samp = meta.sample(n=min(150, len(meta)), random_state=0)
obs = I[I.item.isin(samp['item'])]
obs_share = float((obs.t24 > 1.96).mean())
pc, pn = perm_count()
perm = dict(n_items_sample=int(pn), observed_share_sig_pos=obs_share, perm_mean=float(pc.mean()),
            perm_p95=float(np.quantile(pc, .95)), perm_p=float((pc >= obs_share).mean()))

# ================= B 家計と企業の見通し =================
Q = pd.read_csv(os.path.join(D, 'expectations_quarterly.csv'), index_col=0)
Q['period'] = np.where(Q.index < '2022-01', '2014〜2021年', '2022年〜')
B1 = Q.groupby('period')[['hh_1y', 'firm_1y', 'firm_3y', 'firm_5y', 'all_now', 'all_t12', 'core_t12']].mean()
B1.loc['全期間'] = Q[['hh_1y', 'firm_1y', 'firm_3y', 'firm_5y', 'all_now', 'all_t12', 'core_t12']].mean()
B1.to_csv(os.path.join(R, 'B1_levels_by_period.csv'))

v = Q.dropna(subset=['all_t12'])
err = pd.DataFrame({
    'who': ['家計（1年後）', '企業（1年後）', '「いまの物価」がそのまま続く'],
    'mean_err': [(v.hh_1y - v.all_t12).mean(), (v.firm_1y - v.all_t12).mean(), (v.all_now - v.all_t12).mean()],
    'mae': [(v.hh_1y - v.all_t12).abs().mean(), (v.firm_1y - v.all_t12).abs().mean(), (v.all_now - v.all_t12).abs().mean()],
    'corr_realized': [v[['hh_1y', 'all_t12']].corr().iloc[0, 1], v[['firm_1y', 'all_t12']].corr().iloc[0, 1], v[['all_now', 'all_t12']].corr().iloc[0, 1]],
    'corr_now': [v[['hh_1y', 'all_now']].corr().iloc[0, 1], v[['firm_1y', 'all_now']].corr().iloc[0, 1], 1.0],
    'n': [len(v)] * 3})
err.to_csv(os.path.join(R, 'B2_accuracy.csv'), index=False)

# 「いまの物価」と「1年後の物価」への回帰（HAC）
reg = []
for who in ['hh_1y', 'firm_1y']:
    X = sm.add_constant(v[['all_now', 'all_t12']])
    r = sm.OLS(v[who], X).fit(cov_type='HAC', cov_kwds={'maxlags': 4})
    reg.append(dict(who=who, const=r.params['const'], b_now=r.params['all_now'], se_now=r.bse['all_now'],
                    b_t12=r.params['all_t12'], se_t12=r.bse['all_t12'], r2=r.rsquared, n=int(r.nobs)))
REG = pd.DataFrame(reg)
REG.to_csv(os.path.join(R, 'B3_backward_forward.csv'), index=False)

# 家計−企業の差と、物価の水準
Q['gap'] = Q.hh_1y - Q.firm_1y
gap_corr_now = float(Q[['gap', 'all_now']].corr().iloc[0, 1])

# 頑健性：家計の推定法（δ）、実績を生鮮除くにする、企業の規模
rb = []
for col, lab in [('hh_1y', '家計 基本（δ推定）'), ('rob_delta0.25', '家計 δ=0.25'), ('rob_delta1.0', '家計 δ=1.0'),
                 ('rob_logistic', '家計 ロジスティック分布'), ('rob_dk_as_zero', '家計「分からない」を0%に'),
                 ('firm_1y', '企業 全規模'), ('firm_1y_large', '企業 大企業'), ('firm_1y_small', '企業 中小企業')]:
    for tgt, tl in [('all_t12', '総合'), ('core_t12', '生鮮食品を除く総合')]:
        w = Q.dropna(subset=[tgt, col])
        for per in ['2014〜2021年', '2022年〜', '全期間']:
            ww = w if per == '全期間' else w[w.period == per]
            rb.append(dict(series=lab, realized=tl, period=per, mean=ww[col].mean(),
                           mean_err=(ww[col] - ww[tgt]).mean(), mae=(ww[col] - ww[tgt]).abs().mean(), n=len(ww)))
RB = pd.DataFrame(rb)
RB.to_csv(os.path.join(R, 'B4_robustness.csv'), index=False)

last = Q.iloc[-1]
O = dict(
    A=dict(sample='2015-01〜2026-09', hmax=HMAX,
           fx_persistence_h12=float(fxself[fxself.h == 12].b.iloc[0]), fx_persistence_h24=float(fxself[fxself.h == 24].b.iloc[0]),
           groups=S.round(4).to_dict(orient='records'), items=item_sum, rho_pt_chg=rho_pt_chg, perm=perm),
    B=dict(period=f'{Q.index.min()}〜{Q.index.max()}', n_q=int(len(Q)), n_realized=int(len(v)),
           levels=B1.round(3).reset_index().to_dict(orient='records'), accuracy=err.round(3).to_dict(orient='records'),
           regression=REG.round(3).to_dict(orient='records'), gap_corr_now=gap_corr_now,
           latest=dict(ym=Q.index[-1], hh_1y=float(last.hh_1y), firm_1y=float(last.firm_1y), firm_3y=float(last.firm_3y),
                       firm_5y=float(last.firm_5y), all_now=float(last.all_now))))
json.dump(O, open(os.path.join(R, 'main.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(S.round(3).to_string())
print(json.dumps(item_sum, ensure_ascii=False), 'rho', round(rho_pt_chg, 3), perm)
print(by_top.round(3).to_string())
print(top_items[['item', 'pt24', 't24', 'half_month']].round(3).to_string())
print(ROB.round(3).to_string())
print(B1.round(2).to_string()); print(err.round(3).to_string()); print(REG.round(3).to_string()); print('gapcorr', gap_corr_now)
print(RB[RB.realized == '総合'].round(2).to_string())
