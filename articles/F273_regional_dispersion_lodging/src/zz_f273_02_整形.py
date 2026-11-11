"""02 整形：都道府県×年（暦年・年度）の延べ宿泊者数の表を作る"""
import pathlib
import pandas as pd
R = pathlib.Path(__file__).resolve().parents[1]
d = pd.read_csv(R / "data/lodging_pref_monthly_2011_2025.csv", parse_dates=["date"])
d["code"] = d.pref.str[:2].astype(int)
d["name"] = d.pref.str[2:]
d["year"] = d.date.dt.year
d["fy"] = d.date.dt.year - (d.date.dt.month <= 3).astype(int)
cy = d.groupby(["year", "code", "name"])[["total", "japanese", "foreign"]].sum().reset_index()
fy = d[(d.fy >= 2011) & (d.fy <= 2024)].groupby(["fy", "code", "name"])[["total", "japanese", "foreign"]].sum().reset_index()
assert cy.groupby("year").size().eq(47).all()
cy.to_csv(R / "data/pref_year.csv", index=False)
fy.to_csv(R / "data/pref_fiscal_year.csv", index=False)
print(cy.shape, fy.shape)
