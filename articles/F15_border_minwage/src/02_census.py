"""市区町村×産業の従業者数（経済センサス）と最低賃金を整える。

- 従業者数（民営）：SSDSE-A-2021（経済センサス‐活動調査 2016年6月1日）と SSDSE-A-2026（同 2021年6月1日）
  ※ data/raw/ に手作業で置く（統計センター https://www.nstac.go.jp/use/literacy/ssdse/ ）
- 最低賃金：地域別最低賃金（厚生労働省）。調査日（6月1日）に効いていたのは前年度の改定額なので、
  2016年6月 → 2015年度の額、2021年6月 → 2020年度の額を使う
"""
import numpy as np
import pandas as pd

from common import RAW, DATA

IND = {"total": "", "food": "47", "retail": "41", "life": "48", "manuf": "37", "medical": "50"}


def load(fn, year_tag):
    h = pd.read_csv(RAW / fn, encoding="cp932", header=None, nrows=1).iloc[0].tolist()
    d = pd.read_csv(RAW / fn, encoding="cp932", header=None, skiprows=3)
    d.columns = h
    d = d.rename(columns={h[0]: "code", h[1]: "pref", h[2]: "muni"})
    d["code"] = d["code"].astype(str).str[1:].astype(int)
    out = d[["code", "pref", "muni"]].copy()
    out["pop"] = pd.to_numeric(d["A1101"], errors="coerce")
    for k, s in IND.items():
        out[f"emp_{k}"] = pd.to_numeric(d[f"C2208{s}"], errors="coerce")
        out[f"est_{k}"] = pd.to_numeric(d[f"C2108{s}"], errors="coerce")
    out.columns = ["code", "pref", "muni"] + [f"{c}_{year_tag}" for c in out.columns[3:]]
    return out


a = load("SSDSE-A-2021.csv", "16")
b = load("SSDSE-A-2026.csv", "21")
m = a.merge(b.drop(columns=["pref", "muni"]), on="code", how="inner")
print("matched", len(m), "of", len(a), len(b))

mw = pd.read_csv(RAW / "minimum_wage_2002_2026.csv")
pref_names = m["pref"].unique()


def norm(p):
    return p if p.endswith(("都", "道", "府", "県")) else p


mw["pref_s"] = mw["pref"]
m["pref_s"] = m["pref"].str.replace(r"(都|府|県)$", "", regex=True)
m.loc[m.pref == "北海道", "pref_s"] = "北海道"
m = m.merge(mw[["pref_s", "2015", "2020"]].rename(columns={"2015": "mw15", "2020": "mw20"}), on="pref_s", how="left")
assert m.mw15.notna().all(), m[m.mw15.isna()].pref.unique()
m["dlog_mw"] = np.log(m.mw20) - np.log(m.mw15)
for k in IND:
    m[f"dlog_{k}"] = np.log(m[f"emp_{k}_21"]) - np.log(m[f"emp_{k}_16"])
    m[f"dlog_est_{k}"] = np.log(m[f"est_{k}_21"]) - np.log(m[f"est_{k}_16"])
m = m.replace([np.inf, -np.inf], np.nan)
m.to_csv(DATA / "muni.csv", index=False)
print(m[["dlog_mw", "dlog_food", "dlog_retail", "dlog_manuf", "dlog_total"]].describe().round(3).to_string())
