# 06 レビュー検算（独立レビューの後で足した）：月ごとの割合・倍率の幅、同じ月での上に乗る分、物価でならした値、店頭の倍率
import pandas as pd, numpy as np, json, os
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
o = pd.read_csv(os.path.join(B, 'data', 'processed', 'stages_main.csv'), index_col=0, parse_dates=True)
p = pd.read_csv(os.path.join(B, 'data', 'processed', 'monthly_panel.csv'), index_col=0, parse_dates=True)
b = o.loc['2023'].mean(); res = {}
share = (o['aitai_kg'] - b['aitai_kg']) / (o['retail_kg'] - b['retail_kg'])
s25 = share.loc['2025']; res['share_2025_min'] = s25.min(); res['share_2025_min_month'] = str(s25.idxmin().date())
res['share_2025_max'] = s25.max(); res['share_2025_max_month'] = str(s25.idxmax().date())
s26 = share.loc['2026-01':'2026-08']; res['share_2026_1_8_min'] = s26.min(); res['share_2026_1_8_max'] = s26.max()
res['share_2026_09'] = share.loc['2026-09-01']
res['ratio_2025_mean'] = o.loc['2025', 'ratio'].mean(); res['ratio_2015_23_mean'] = o.loc['2015':'2023', 'ratio'].mean()
res['ratio_2025_03_08_min'] = o.loc['2025-03':'2025-08', 'ratio'].min(); res['ratio_2025_03_08_max'] = o.loc['2025-03':'2025-08', 'ratio'].max()
res['ratio_2026_01_08_min'] = o.loc['2026-01':'2026-08', 'ratio'].min(); res['ratio_2026_01_08_max'] = o.loc['2026-01':'2026-08', 'ratio'].max()
res['ratio_2026_09'] = o.loc['2026-09-01', 'ratio']
m = o['margin_kg']; ml = o['retail_kg'] - o['aitai_kg'].shift(1); cpi = p['cpi_all']
res['margin_same_2015_23'] = m.loc['2015':'2023'].mean(); res['margin_same_2025'] = m.loc['2025'].mean()
res['margin_same_max'] = m.max(); res['margin_same_max_month'] = str(m.idxmax().date())
res['margin_same_2026_1_9'] = m.loc['2026-01':'2026-09'].mean()
for nm, ser in [('same', m), ('lag', ml)]:
    real = ser / cpi * 100  # 消費者物価（総合、2020年=100）でならした値（2020年の円）
    res[f'real_{nm}_2015_23'] = real.loc['2015':'2023'].mean(); res[f'real_{nm}_2026'] = real.loc['2026'].dropna().mean()
res['cpi_all_2015_23'] = cpi.loc['2015':'2023'].mean(); res['cpi_all_2026_1_9'] = cpi.loc['2026'].dropna().mean()
r = p['tokyo_koshi_5kg']; res['retail_vs2023_first_2x'] = str((r / r.loc['2023'].mean()).loc['2024':].pipe(lambda z: z[z >= 2]).index.min().date())
for a, c in [('2024-06-01', '2025-06-01'), ('2024-08-01', '2025-08-01'), ('2024-04-01', '2025-04-01')]: res[f'retail_yoy_{c[:7]}'] = r[c] / r[a]
# 新潟コシヒカリでの倍率（2015〜2023年）
nk = p['tokyo_koshi_5kg'] / 5 / (p['aitai_niigata_koshi'] / 60 / 0.90); res['ratio_niigata_2015_23'] = nk.loc['2015':'2023'].mean()
json.dump(res, open(os.path.join(B, 'results', 'review_checks.json'), 'w'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(res, ensure_ascii=False, indent=0, default=lambda v: round(float(v), 3)))
