"""F04 データを整える：宿泊旅行統計（日本人延べ宿泊者数）＋ 月別の新規陽性者数 ＋ 緊急事態宣言の日数割合"""
import numpy as np, pandas as pd
from common import RAW, DATA, PREFS, EMERG

d = pd.read_csv(RAW / "lodging_pref_monthly_2011_2025.csv")
d["pref"] = d.pref.str.replace(r"^\d\d", "", regex=True).str.replace("　", "").str.replace(" ", "")
d["pref"] = d.pref.replace({"全国": "全国", "東京都": "東京", "京都府": "京都", "大阪府": "大阪"}).str.replace("県$", "", regex=True)
assert set(d.pref) == set(PREFS) | {"全国"}, set(d.pref) ^ (set(PREFS) | {"全国"})
d["date"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
d["days"] = d.date.dt.days_in_month

c = pd.read_csv(RAW / "covid_newly_confirmed_cases_daily.csv")
c.columns = [x.strip() for x in c.columns]
c["Date"] = pd.to_datetime(c.Date)
cols = list(c.columns[2:])
assert len(cols) == 47
c = c.rename(columns=dict(zip(cols, PREFS))).rename(columns={"ALL": "全国"})
for k in ["全国"] + PREFS:
    c[k] = pd.to_numeric(c[k].astype(str).str.strip(), errors="coerce").fillna(0)
cm = c.set_index("Date")[["全国"] + PREFS].resample("MS").sum().stack().rename("cases").reset_index()
cm.columns = ["date", "pref", "cases"]
d = d.merge(cm, on=["date", "pref"], how="left")
d["cases"] = d.cases.fillna(0)
d.loc[d.date > "2023-05-01", "cases"] = np.nan          # 全数把握は2023年5月8日まで
d["emerg"] = d.date.dt.strftime("%Y-%m").map(EMERG).fillna(0.0)
d["jp_per_day"] = d.japanese / d.days
d["y"] = np.log(d.jp_per_day)
d["x_cases"] = np.log1p(d.cases / d.days)
d[["date", "pref", "total", "japanese", "foreign", "days", "jp_per_day", "y", "cases", "x_cases", "emerg"]].to_csv(DATA / "monthly_pref.csv", index=False)
n = d[d.pref == "全国"].set_index("date")
print(n.loc["2019-01":"2021-12", ["japanese", "cases", "emerg"]].to_string())
print(len(d), d.pref.nunique())
