"""03 分析：空き家の増え方を「住宅ストックの増加」「人口の減少」「世帯の小型化」などに分け、都道府県パネルで回帰する。
出力 results/*.csv, results/summary.json
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'results'; R.mkdir(exist_ok=True)
np.random.seed(127)
df = pd.read_csv(ROOT/'data/panel_pref.csv')
REG = {1:'北海道',2:'東北',3:'東北',4:'東北',5:'東北',6:'東北',7:'東北'}
for c in range(8,15): REG[c]='関東'
for c in range(15,24): REG[c]='中部'
for c in range(24,31): REG[c]='近畿'
for c in range(31,36): REG[c]='中国'
for c in range(36,40): REG[c]='四国'
for c in range(40,48): REG[c]='九州・沖縄'
df['region'] = df.code.map(REG)
# 住宅に住んでいる世帯（主世帯＋同居）と居住世帯ありの住宅の差＝同居など。空き家以外の「居住世帯なし」＝一時現在者のみ・建築中
df['other_unocc'] = df.stock - df.occupied - df.vacant
df['hh_minus_occ'] = df.households - df.occupied

def L(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(np.isclose(a, b), a, (a - b) / (np.log(a) - np.log(b)))

def decompose(g, y0, y1):
    a = g[g.year == y0].set_index('code'); b = g[g.year == y1].set_index('code')
    out = pd.DataFrame(index=a.index)
    out['pref'] = a.pref; out['region'] = a.region
    out['dV'] = b.vacant - a.vacant
    out['dStock'] = b.stock - a.stock
    lh = L(b.households.values, a.households.values)
    out['dHH'] = b.households - a.households
    out['hh_pop'] = lh * np.log(b.pop_hh / a.pop_hh)          # 人口の増減による世帯数の変化
    out['hh_size'] = lh * np.log(a.hh_size / b.hh_size)       # 世帯の小型化による世帯数の変化
    out['d_hh_minus_occ'] = b.hh_minus_occ - a.hh_minus_occ
    out['d_other_unocc'] = b.other_unocc - a.other_unocc
    # 恒等式：dV = dStock - dHH + d(HH-Occ) - d(他の居住世帯なし)
    out['c_stock'] = out.dStock
    out['c_pop'] = -out.hh_pop          # 人口が減ると空き家は増える方向（正）
    out['c_size'] = -out.hh_size        # 世帯が小さくなると空き家は減る方向（負）
    out['c_rest'] = out.d_hh_minus_occ - out.d_other_unocc
    resid = out.dV - (out.c_stock + out.c_pop + out.c_size + out.c_rest)
    assert resid.abs().max() < 1, resid.abs().max()
    out['dPop'] = b.pop_hh - a.pop_hh
    out['pop_g'] = b.pop_hh / a.pop_hh - 1
    out['stock_g'] = b.stock / a.stock - 1
    out['hh_g'] = b.households / a.households - 1
    out['d_vac_rate'] = (b.vac_rate - a.vac_rate) * 100
    out['d_other_rate'] = (b.vac_other_rate - a.vac_other_rate) * 100
    out['d_rent_rate'] = (b.vac_rent_rate - a.vac_rent_rate) * 100
    out['vac_rate0'] = a.vac_rate * 100
    out['dV_other'] = b.vac_other - a.vac_other
    out['dV_rent'] = b.vac_rent - a.vac_rent
    return out

S = {}
for (y0, y1) in [(2003, 2023), (2008, 2023), (2003, 2018), (2018, 2023)]:
    dd = decompose(df, y0, y1)
    dd.to_csv(R/f'decomp_pref_{y0}_{y1}.csv')
    nat = dd[['dV','c_stock','c_pop','c_size','c_rest','dPop','dHH','dStock','dV_other','dV_rent']].sum()
    S[f'nat_{y0}_{y1}'] = {k: float(v) for k, v in nat.items()}
    # 人口が減った県だけ
    dec = dd[dd.dPop < 0]
    S[f'pop_decline_{y0}_{y1}'] = dict(n=int(len(dec)), dV=float(dec.dV.sum()), c_pop=float(dec.c_pop.sum()),
        c_stock=float(dec.c_stock.sum()), c_size=float(dec.c_size.sum()), c_rest=float(dec.c_rest.sum()),
        share_pop_in_dV=float(dec.c_pop.sum() / dec.dV.sum()))
    # 県ごとに「人口要因 ÷ 空き家の増加」
    pos = dd[dd.dV > 0]
    S[f'pref_ratio_{y0}_{y1}'] = dict(
        n_dV_pos=int(len(pos)),
        median_pop_share=float((pos.c_pop / pos.dV).median()),
        n_pop_ge_dV=int((dd.c_pop >= dd.dV).sum()),
        n_stock_gt_pop=int((dd.c_stock > dd.c_pop).sum()))
# 地方ブロック別（2008→2023）
blk = pd.read_csv(R/'decomp_pref_2008_2023.csv').groupby('region')[['dV','c_stock','c_pop','c_size','c_rest','dPop']].sum()
blk.to_csv(R/'decomp_region_2008_2023.csv')

# ---------- パネル回帰（5年ごとの差分） ----------
df = df.sort_values(['code','year'])
g = df.groupby('code')
p = pd.DataFrame({
    'code': df.code, 'year': df.year, 'region': df.region,
    'dV_s': g.vacant.diff() / g.stock.shift() * 100,          # 空き家の増加（期首ストック比、%）
    'dVo_s': g.vac_other.diff() / g.stock.shift() * 100,
    'dVr_s': g.vac_rent.diff() / g.stock.shift() * 100,
    'dV_h': g.vacant.diff() / g.households.shift() * 100,     # 分母を世帯数に
    'dVrate': g.vac_rate.diff() * 100,                        # 空き家率の変化（ポイント）
    'popl_s': -g.pop_hh.diff() / g.hh_size.shift() / g.stock.shift() * 100,  # 人口減を世帯数に直した分（期首ストック比）
    'popl_h': -g.pop_hh.diff() / g.hh_size.shift() / g.households.shift() * 100,
    'size_s': (df.pop_hh / df.hh_size - df.pop_hh / g.hh_size.shift()) / g.stock.shift() * 100,  # 世帯の小型化で増えた世帯数（期首ストック比）
    'stock_s': g.stock.diff() / g.stock.shift() * 100,
    'stock_h': g.stock.diff() / g.households.shift() * 100,
    'popg': (df.pop_hh / g.pop_hh.shift() - 1) * 100,
    'stockg': (df.stock / g.stock.shift() - 1) * 100,
    'hhg': (df.households / g.households.shift() - 1) * 100,
    'w': g.stock.shift(),
}).dropna()
p.to_csv(R/'panel_diff.csv', index=False)

def fit(formula, data, label, coef):
    m = smf.ols(formula, data).fit(cov_type='cluster', cov_kwds={'groups': data.code})
    return dict(spec=label, coef=coef, b=float(m.params[coef]), se=float(m.bse[coef]),
                lo=float(m.conf_int().loc[coef, 0]), hi=float(m.conf_int().loc[coef, 1]), n=int(m.nobs), r2=float(m.rsquared))
rows = []
# 主分析：人口減（世帯数換算）1戸分あたり、空き家は何戸増えたか
rows.append(fit('dV_s ~ popl_s + C(year)', p, '主：年の固定効果のみ', 'popl_s'))
rows.append(fit('dV_s ~ popl_s + C(year) + C(code)', p, '県の固定効果も入れる', 'popl_s'))
rows.append(fit('dV_s ~ popl_s + stock_s + size_s + C(year)', p, 'ストックの増加・世帯の小型化をそろえる', 'popl_s'))
rows.append(fit('dVo_s ~ popl_s + C(year)', p, '種類：その他の空き家', 'popl_s'))
rows.append(fit('dVr_s ~ popl_s + C(year)', p, '種類：賃貸用の空き家', 'popl_s'))
rows.append(fit('dV_h ~ popl_h + C(year)', p, '分母：世帯数', 'popl_h'))
rows.append(fit('dV_s ~ popl_s + C(year)', p[p.year >= 2013], '年：2008年以降の差分', 'popl_s'))
rows.append(fit('dV_s ~ popl_s + C(year)', p[p.year <= 2018], '年：2023年を除く', 'popl_s'))
pw = p.copy()
m = smf.wls('dV_s ~ popl_s + C(year)', pw, weights=pw.w).fit(cov_type='cluster', cov_kwds={'groups': pw.code})
rows.append(dict(spec='住宅数で重みづけ', coef='popl_s', b=float(m.params.popl_s), se=float(m.bse.popl_s),
                 lo=float(m.conf_int().loc['popl_s',0]), hi=float(m.conf_int().loc['popl_s',1]), n=int(m.nobs), r2=float(m.rsquared)))
# ストックの増加の係数（参考）
rows.append(fit('dV_s ~ stock_s + popl_s + size_s + C(year)', p, '参考：住宅ストック増加の係数', 'stock_s'))
# 人口の伸びと住宅の伸び：住宅は人口に合わせて増えたか
rows.append(fit('stockg ~ popg + C(year)', p, '参考：人口の伸び→住宅の伸び', 'popg'))
rows.append(fit('stockg ~ hhg + C(year)', p, '参考：世帯の伸び→住宅の伸び', 'hhg'))
reg = pd.DataFrame(rows); reg.to_csv(R/'regression.csv', index=False)
S['regression'] = rows

# 空き家率の変化と人口の伸びの相関（2008→2023）
dd = pd.read_csv(R/'decomp_pref_2008_2023.csv')
S['corr_2008_2023'] = dict(
    popg_vs_dvacrate=float(np.corrcoef(dd.pop_g, dd.d_vac_rate)[0,1]),
    popg_vs_dother=float(np.corrcoef(dd.pop_g, dd.d_other_rate)[0,1]),
    popg_vs_drent=float(np.corrcoef(dd.pop_g, dd.d_rent_rate)[0,1]),
    stockg_minus_hhg_vs_dvacrate=float(np.corrcoef(dd.stock_g - dd.hh_g, dd.d_vac_rate)[0,1]),
    n_pop_decline=int((dd.dPop < 0).sum()), n_hh_decline=int((dd.dHH < 0).sum()), n_stock_decline=int((dd.dStock < 0).sum()))
# 全国の推移
nat = df.groupby('year')[['stock','households','occupied','vacant','vac_other','vac_rent','vac_sale','vac_second','pop_hh']].sum()
nat['vac_rate'] = nat.vacant / nat.stock * 100; nat['other_rate'] = nat.vac_other / nat.stock * 100; nat['rent_rate'] = nat.vac_rent / nat.stock * 100
nat.to_csv(R/'national_trend.csv')
json.dump(S, open(R/'summary.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in S.items() if k != 'regression'}, ensure_ascii=False, indent=1))
print(reg[['spec','b','lo','hi','n','r2']].round(3).to_string())
print(blk.round(0))
print(nat.round(2))
