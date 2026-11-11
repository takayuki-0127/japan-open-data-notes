"""05 SQL（DuckDB 版）を動かし、Python の月の表・カレンダー寄与と一致するか確かめる"""
import duckdb, pandas as pd, numpy as np
from pathlib import Path
B = Path(__file__).resolve().parents[1]
import os; os.chdir(B)
con = duckdb.connect(); con.execute(open('sql/02_calendar_and_adjust_duckdb.sql', encoding='utf-8').read())
sm_ = pd.read_csv('results/H_sql_dim_month.csv'); py = pd.read_csv('data/calendar_monthly.csv')
mm = py.merge(sm_, on='ym', suffixes=('_py','_sql'))
diff = {c: int((mm[c+'_py']!=mm[c+'_sql']).sum()) for c in ['n_days','n_sat','n_sun','n_hol_wd','n_renkyu']}
adj = pd.read_csv('results/H_sql_adjusted.csv'); ct = pd.read_csv('results/C_monthly_contrib.csv')
j = ct.merge(adj, on=['ym','業態'])
out = dict(months=len(mm), mismatch=diff, rows_compared=len(j),
           max_abs_diff_yoy=float((j.y-j.yoy).abs().max()), max_abs_diff_calendar=float((j.カレンダー寄与-j.calendar_contrib).abs().max()))
print(out); pd.Series(out).to_json('results/H_sql_check.json', force_ascii=False)
