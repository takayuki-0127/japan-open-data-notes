"""02 整形：月次パネル（為替・輸入物価・CPI）と四半期の見通しパネルを作る"""
import os
import numpy as np
import pandas as pd

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(H, 'data', 'raw')
OUT = os.path.join(H, 'data')

# --- 日本銀行（輸入物価・為替・短観）
b = pd.read_csv(os.path.join(RAW, 'boj_import_prices_fx_tankan.csv'))
b['value'] = pd.to_numeric(b['value'], errors='coerce')
m = b[b.db != 'CO'].pivot_table(index='date', columns='code', values='value')
m.index = pd.PeriodIndex([f'{str(d)[:4]}-{str(d)[4:]}' for d in m.index], freq='M')
ren = {'FXERM07': 'usdjpy', 'PRCG20_2600000000': 'imp_yen', 'PRCG20_2500000000': 'imp_contract',
       'PRCG20_2600120001': 'imp_food', 'PRCG20_2600520001': 'imp_energy', 'PRCG20_2600820001': 'imp_elec',
       'PRCG20_2600620001': 'imp_chem', 'PRCG20_2600220001': 'imp_textile', 'PRCG20_2600320001': 'imp_metal',
       'PRCG20_2600420001': 'imp_wood', 'PRCG20_2600720001': 'imp_machine', 'PRCG20_2600920001': 'imp_transport',
       'PRCG20_2601020001': 'imp_other'}
m = m.rename(columns=ren).dropna(how='all')

# --- CPI（財・サービス分類）
g = pd.read_csv(os.path.join(RAW, 'cpi_gs_monthly.csv'))
g.index = pd.PeriodIndex([f'{str(d)[:4]}-{str(d)[4:]}' for d in g.ym], freq='M')
g = g.drop(columns='ym')
g.columns = [c.split('|')[0] for c in g.columns]
g = g.loc[:, ~g.columns.duplicated()]

panel = m.join(g, how='inner')
panel = panel[panel.index <= pd.Period('2026-09', 'M')]
panel.index = panel.index.astype(str)
panel.to_csv(os.path.join(OUT, 'monthly_panel.csv'))

# --- 品目別 CPI（F209 から）
it = pd.read_csv(os.path.join(RAW, 'cpi_items_monthly.csv.gz'))
it.index = [f'{str(d)[:4]}-{str(d)[4:]}' for d in it.ym]
it = it.drop(columns='ym')
it.to_csv(os.path.join(OUT, 'items_monthly.csv.gz'), compression='gzip')

# --- 見通し（四半期）：短観の企業の見通し、家計（F72 の Carlson–Parkin 推定）
t = b[b.db == 'CO'].pivot_table(index='date', columns='code', values='value')
q = pd.DataFrame(index=t.index)
q['firm_1y'] = t['TK99F0000204HCQ00000']
q['firm_1y_large'] = t['TK99F0000204HCQ01000']
q['firm_1y_small'] = t['TK99F0000204HCQ03000']
q['firm_3y'] = t['TK99F0000205HCQ00000']
q['firm_5y'] = t['TK99F0000206HCQ00000']
# 短観の日付は YYYYQQ（01=3月調査, 02=6月, 03=9月, 04=12月）
q['ym'] = [f'{str(d)[:4]}-{int(str(d)[4:]) * 3:02d}' for d in q.index]
q = q.dropna(subset=['firm_1y']).set_index('ym')

h = pd.read_csv(os.path.join(RAW, 'f72_household_expectations.csv'))
h = h[h.hh == '二人以上'].set_index('ym')
cols = ['mu', 'sigma', 'rob_delta0.25', 'rob_delta0.5', 'rob_delta1.0', 'rob_logistic', 'rob_dk_as_zero',
        'all_now', 'all_t12', 'core_now', 'core_t12']
q = q.join(h[cols].rename(columns={'mu': 'hh_1y'}), how='left')
q.to_csv(os.path.join(OUT, 'expectations_quarterly.csv'))
print('monthly', panel.shape, panel.index.min(), panel.index.max())
print('quarterly', q.shape, q.index.min(), q.index.max())
