# -*- coding: utf-8 -*-
"""F184 02_整形：取得した CSV の確認（年ごとの路線数・欠け・往復の整合）"""
import os
import pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data"); R = os.path.join(ROOT, "results"); os.makedirs(R, exist_ok=True)
a = pd.read_csv(os.path.join(D, "air_routes_annual.csv"))
m = pd.read_csv(os.path.join(D, "air_routes_monthly.csv"))
cov = a.groupby("year").agg(routes=("route", "nunique"), pax_total=("pax", "sum")).reset_index()
ms = m.groupby(["year", "route"]).pax.sum().rename("pax_month_sum").reset_index()
chk = a.merge(ms, on=["year", "route"], how="left")
chk["ratio"] = chk.pax_month_sum / chk.pax
cov = cov.merge(chk.groupby("year").ratio.median().rename("月の合計÷年計（中央値）").reset_index(), on="year")
cov.to_csv(os.path.join(R, "coverage.csv"), index=False, encoding="utf-8-sig")
print(cov.to_string())
