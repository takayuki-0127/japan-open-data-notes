"""02 整形：処置（保育所の在所児の変化）・媒介（女性の労働力率の変化）・結果（出生率の変化）をそろえる"""
import numpy as np, pandas as pd
from common import ROOT

raw = ROOT / 'data/raw'
a = pd.read_csv(raw / 'f16_analysis_2010_2015.csv', dtype={'code': str})
a['code'] = a.code.str.zfill(5)
a = a.rename(columns={'D': 'T', 'Y': 'M'})  # T：在所児の変化（10人単位）、M：女性の労働力率の変化（pt）

# 就業率の変化（頑健性の媒介変数）
p = pd.read_csv(raw / 'f16_panel_long.csv', dtype={'code': str})
p['code'] = p.code.str.zfill(5)
def emp(g):
    return 100 * g.F110202 / (g.F110102 + g.F110802)
w = {y: g.set_index('code') for y, g in p.groupby('year')}
a['M_emp'] = (emp(w[2015]) - emp(w[2010])).reindex(a.code).values

t1 = pd.read_csv(raw / 'f20_tfr_2013_17.csv', dtype={'code': str})[['code', 'tfr', 'pop']].rename(columns={'tfr': 'tfr_1317', 'pop': 'pop_f20'})
t2 = pd.read_csv(raw / 'f20_tfr_2018_22.csv', dtype={'code': str})[['code', 'tfr']].rename(columns={'tfr': 'tfr_1822'})
d = a.merge(t1, on='code').merge(t2, on='code').dropna(subset=['tfr_1317', 'tfr_1822', 'M', 'T'])
d['Y'] = d.tfr_1822 - d.tfr_1317            # 出生率の変化（2013〜17年 → 2018〜22年）
d['pop2010'] = np.exp(d['log人口'])
d.to_csv(ROOT / 'data/analysis.csv', index=False)
print(len(d), d[['T', 'M', 'Y']].describe().round(3))
