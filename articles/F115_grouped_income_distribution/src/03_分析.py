# F115 03 分析：1985〜2024年（所得の年）の階級別の世帯割合から分布を推定し、公表されている平均・中央値・五分位値・五分位階級の平均と比べる
import json, numpy as np, pandas as pd
from pathlib import Path
from common import *
A = Path(__file__).resolve().parents[1]; R = A / 'results'; R.mkdir(exist_ok=True)
bins = pd.read_csv(A / 'data' / 'bins_long.csv'); pub = pd.read_csv(A / 'data' / 'published.csv').set_index('year')
TARGETS = ['mean', 'median', 'p20', 'p40', 'p60', 'p80', 'qmean1', 'qmean2', 'qmean3', 'qmean4', 'qmean5']
rng = np.random.default_rng(115)

# 1) 年 × 階級の区切り方 × 方法
rows = []
for y, d in bins.groupby('year'):
    for sc, cuts in SCHEMES.items():
        sh = coarsen(d.lo, d.share, cuts)
        for m, (sm, extra) in estimate_all(cuts, sh).items():
            rows.append(dict(year=y, scheme=sc, method=m, **sm, alpha=extra.get('alpha', np.nan)))
est = pd.DataFrame(rows); est.to_csv(R / 'estimates_long.csv', index=False)

# 公表値との差（％）
err = est.melt(id_vars=['year', 'scheme', 'method'], value_vars=TARGETS, var_name='target', value_name='est')
err['pub'] = [pub.at[y, t] for y, t in zip(err.year, err.target)]
err['pct'] = (err.est / err.pub - 1) * 100
err.to_csv(R / 'errors_long.csv', index=False)
summ = err.assign(abs_pct=err.pct.abs()).groupby(['scheme', 'method', 'target']).agg(mean_pct=('pct', 'mean'), mae_pct=('abs_pct', 'mean'), max_abs=('abs_pct', 'max')).reset_index()
summ.to_csv(R / 'error_summary.csv', index=False)

# 2) ジニ係数・上位10%の割合（公表値がないので、方法どうしの幅だけを見る）
spread = est[est.scheme == 'S25'].groupby('year').agg(gini_min=('gini', 'min'), gini_max=('gini', 'max'), top10_min=('top10', 'min'), top10_max=('top10', 'max'))
spread.to_csv(R / 'gini_spread_S25.csv')

# 3) 0.1%の四捨五入の影響（2024年、公表の25階級）：各割合に ±0.05 の一様な誤差を足して200回
d24 = bins[bins.year == 2024]; cuts = SCHEMES['S25']; base = coarsen(d24.lo, d24.share, cuts)
rr = []
for k in range(200):
    sh = np.maximum(base + rng.uniform(-0.05, 0.05, len(base)), 1e-4)
    for m, (sm, _) in estimate_all(cuts, sh, fams=('lognorm', 'gb2')).items():
        rr.append(dict(rep=k, method=m, **sm))
rr = pd.DataFrame(rr); rr.to_csv(R / 'rounding_2024.csv', index=False)

# 4) 上の裾（パレートの α）の決め方：2024年、公表の25階級
ra = []
for lab, a in [('1500と2000から（基本）', None), ('1200と2000から', np.log(base[-3:].sum() / base[-1]) / np.log(2000 / 1200)), ('α=2', 2.0), ('α=2.5', 2.5), ('α=3', 3.0), ('α=4', 4.0)]:
    for fn, nm in [(fit_uniform_pareto, 'uniform_pareto'), (fit_pchip_pareto, 'pchip_pareto')]:
        dd, aa = fn(cuts, base, alpha=a); ra.append(dict(choice=lab, method=nm, alpha=aa, **dd.summary()))
pd.DataFrame(ra).to_csv(R / 'pareto_alpha_2024.csv', index=False)

# 要約を表示
s25 = summ[summ.scheme == 'S25'].pivot(index='method', columns='target', values='mae_pct')[TARGETS].round(2)
print('S25 平均絶対誤差（％、39年）\n', s25)
key = summ[summ.target.isin(['median', 'mean', 'qmean5', 'qmean1'])].pivot_table(index=['method'], columns=['target', 'scheme'], values='mae_pct').round(1)
print(key.to_string())
print('ジニの幅（S25）：最小幅', (spread.gini_max - spread.gini_min).min().round(3), '最大幅', (spread.gini_max - spread.gini_min).max().round(3))
print('2024 四捨五入：', rr.groupby('method')[['median', 'mean', 'qmean5', 'gini']].agg(lambda v: v.quantile(.975) - v.quantile(.025)).round(2).to_string())
print(pd.DataFrame(ra)[['choice', 'method', 'alpha', 'mean', 'qmean5', 'gini', 'top10']].round(3).to_string())
