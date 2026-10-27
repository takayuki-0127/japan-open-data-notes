"""F69 整形：5つの表を「1セル1行」の形にそろえ、記号のセルだけを書き出す（03 の点検の入力の確認用）"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
from common import *

out = ROOT / 'data'
s = load_ssds(); s[s.value.isna()].to_csv(out / 't1_symbol_cells.csv', index=False)
k = load_kakei(); k[k.value.isna()].to_csv(out / 't2_symbol_cells.csv', index=False)
i = load_idwr(); i[i.reports.map(sym).notna()].to_csv(out / 't3_symbol_cells.csv', index=False)
v = load_vital(); v[(v.raw == '…')].to_csv(out / 't4_symbol_cells.csv', index=False)
c = load_census()
cc = c.melt(id_vars=['area', 'nat', 'sex', 'age'], value_vars=CENSUS_COLS, var_name='column', value_name='raw')
cc[cc.raw.map(sym).notna()].to_csv(out / 't5_symbol_cells.csv', index=False)
for f in sorted(out.glob('t*_symbol_cells.csv')):
    print(f.name, sum(1 for _ in open(f, encoding='utf-8')) - 1)
