"""02 整形：都道府県×年度（1955〜2022）と市区町村×年度（2005・2010・2015・2017・2020）の相対所得を作る"""
import numpy as np, pandas as pd
from common import ROOT
R = ROOT / 'data/raw'
q = pd.read_csv(R / 'f71_panel_rel_income.csv')
# 都道府県：F71 の相対所得 r は47（1971年度までは46）県の対数平均との差。
# 長い期間をそろえるため、沖縄を除く46都道府県の対数平均との差に計算し直す（段差を消したつなぎ方 r と、消さない r_naive の両方）
q = q[q.code != 47].copy()
for col in ['r', 'r_naive']:
    q[col] = q[col] - q.groupby('year')[col].transform('mean')
q['rel'] = np.exp(q['r'])           # 平均（幾何平均）＝1
q['rel_naive'] = np.exp(q['r_naive'])
q[['code', 'name', 'year', 'y', 'r', 'r_naive', 'rel', 'rel_naive']].to_csv(ROOT / 'data/pref_panel.csv', index=False)
# 47都道府県（1975年度以降）
q47 = pd.read_csv(R / 'f71_panel_rel_income.csv'); q47 = q47[q47.year >= 1975].copy()
q47['r'] = q47['r'] - q47.groupby('year')['r'].transform('mean'); q47['rel'] = np.exp(q47['r'])
q47[['code', 'name', 'year', 'y', 'r', 'rel']].to_csv(ROOT / 'data/pref47_panel.csv', index=False)
# 市区町村：納税者1人あたり課税対象所得（万円）、相対所得は全市区町村の対数平均との差
m = pd.read_csv(R / 'f40_municipal_panel.csv', dtype={'code': str})
m = m.rename(columns={'A1101': 'pop', 'C120120': 'taxpayers'})
m['r'] = np.log(m.inc_tp) - m.groupby('year').inc_tp.transform(lambda s: np.log(s).mean())
m['rel'] = np.exp(m.r)
m[['code', 'pref', 'year', 'pop', 'taxpayers', 'inc_tp', 'r', 'rel']].to_csv(ROOT / 'data/muni_panel.csv', index=False)
print(q.groupby('year').size().describe()[['min', 'max']].to_dict(), len(m), m.groupby('year').size().to_dict())
