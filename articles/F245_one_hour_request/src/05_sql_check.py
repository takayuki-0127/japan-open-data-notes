import duckdb, pandas as pd, json, os
B=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
con=duckdb.connect(); con.execute(f"CREATE TABLE drugstore_monthly AS SELECT * FROM read_csv_auto('{B}/data/drugstore_monthly.csv')")
qs=[q for q in open(f'{B}/src/05_sql_check.sql').read().split(';') if 'SELECT' in q]
r1=con.execute(qs[0]).df(); r2=con.execute(qs[1]).df(); R=json.load(open(f'{B}/results/main.json'))
d1=max(abs(r1.set_index('地域').yoy[k]-(R['A_industry_aug_yoy'] if k=='全国' else R['A_region_aug_yoy'][k])) for k in r1.地域)
d2=max(abs(r2.set_index('品目').contrib_pt[k]-R['B_item_contrib'][k]) for k in r2.品目)
txt=f"地域の前年比: 最大差 {d1:.4f}（pandas は小数2桁に丸め）\n品目の寄与: 最大差 {d2:.4f}\n"
open(f'{B}/results/F_sql_check.txt','w').write(txt+r1.round(4).to_string()+"\n\n"+r2.round(4).to_string()); print(txt)
