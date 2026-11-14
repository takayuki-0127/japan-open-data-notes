"""答え合わせの期待値を、dbt の SQL とは別に pandas で計算して seeds/expected_r*.csv に書く。
既定の定義（dbt_project.yml の vars の既定値）と、答え合わせ用データ data/fixture_2751 を使う。
使い方: python3 tools/make_expected.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spec import load, reports

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = dict(mon="cal", st="cancel", test=False, tax=False, ret="return", grp="old", gap=13, cust="receipt")

if __name__ == "__main__":
    out = reports(load(os.path.join(ROOT, "data", "fixture_2751")), BASE)
    for k, df in out.items():
        df.to_csv(os.path.join(ROOT, "seeds", f"expected_{k.lower()}.csv"), index=False, float_format="%.10f")
        print(k, len(df))
