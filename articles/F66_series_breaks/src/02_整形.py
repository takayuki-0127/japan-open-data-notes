"""労働力調査と毎月勤労統計を月次の表にそろえる"""
import re
import warnings
import pandas as pd
from common import RAW, DATA

warnings.filterwarnings("ignore")

# ---- 労働力調査（原数値、沖縄を含む 1972年7月〜）----
d = pd.read_excel(RAW / "lfs.xlsx", "原数値", header=None)
cols = {4: "lf", 7: "emp", 10: "ee", 13: "unemp", 16: "nilf", 19: "urate",
        8: "emp_m", 9: "emp_f", 5: "lf_m", 6: "lf_f", 17: "nilf_m", 18: "nilf_f"}
rows, year = [], None
for i in range(10, len(d)):
    m = re.match(r"(\d+)月", str(d.iat[i, 1]))
    if not m:
        continue
    mon = int(m.group(1))
    c0 = str(d.iat[i, 0])
    if mon == 1:
        nxt = str(d.iat[i + 1, 0]) if i + 1 < len(d) else ""
        year = int(float(nxt)) if re.fullmatch(r"\d{4}(\.0)?", nxt) else (year + 1 if year else None)
    elif re.fullmatch(r"\d{4}(\.0)?", c0):
        year = int(float(c0))
    rec = {"date": pd.Timestamp(year, mon, 1)}
    for j, k in cols.items():
        v = pd.to_numeric(str(d.iat[i, j]).strip("<>() "), errors="coerce")
        rec[k] = v
    rows.append(rec)
lfs = pd.DataFrame(rows).dropna(subset=["lf"]).set_index("date").sort_index()
lfs = lfs[lfs.index >= "1972-07-01"]
lfs["pop15"] = lfs["lf"] + lfs["nilf"]
lfs.to_csv(DATA / "lfs_monthly.csv")
print("労働力調査", lfs.index.min().date(), "〜", lfs.index.max().date(), len(lfs), "か月")

# ---- 毎月勤労統計 ----
w = pd.read_csv(RAW / "wage.csv", dtype={"月": str})
w = w[w["月"] != "CY"].copy()
w["date"] = pd.to_datetime(w["年"].astype(str) + "-" + w["月"] + "-01")
items = {"現金給与総額": "cash_total", "きまって支給する給与": "scheduled", "所定内給与": "scheduled_base"}
ix = w[w["種別"] == "指数"].set_index("date")[list(items)].rename(columns=items)
gr = w[w["種別"] != "指数"].set_index("date")[list(items)].rename(columns=items)
mk = ix.add_prefix("idx_").join(gr.add_prefix("pub_"))
for k in items.values():
    mk[f"idxyoy_{k}"] = (mk[f"idx_{k}"] / mk[f"idx_{k}"].shift(12) - 1) * 100
ky = pd.read_csv(RAW / "maikin_kyotsu_yoy.csv")
ky["date"] = pd.to_datetime(ky["month"] + "-01")
mk = mk.join(ky.set_index("date").drop(columns="month").add_prefix("kyo_"))
mk.to_csv(DATA / "maikin_monthly.csv")
print("毎月勤労統計", mk.index.min().date(), "〜", mk.index.max().date(), len(mk), "か月")
