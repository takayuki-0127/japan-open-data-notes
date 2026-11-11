"""02 整形：JSON を都道府県×年度（付帯率）、都道府県×年（世帯加入率）、都道府県×月（新契約・保有）の表にし、
概況の第12表（2010〜2024年度）と照合する。"""
import json, pathlib, sys
import openpyxl, pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from zz_f276_common import PREF
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, PRO = ROOT / "data" / "raw", ROOT / "data" / "processed"
PRO.mkdir(parents=True, exist_ok=True)
ex = json.loads((RAW / "graph_data_eq_ex.json").read_text(encoding="utf-8-sig"))
mo = json.loads((RAW / "graph_data_eq.json").read_text(encoding="utf-8-sig"))
f = lambda v: None if v in (None, "", "-") else float(v)
rows = []
for y, d in ex.items():
    for k, v in d.items():
        if not v:
            continue
        code = 0 if k == "total" else int(k)
        rows.append(dict(year=int(y), code=code, futai=f(v.get("accessibility")), kanyu=f(v.get("subscriptionRate"))))
an = pd.DataFrame(rows).sort_values(["code", "year"])
an["pref"] = an["code"].map(lambda c: "全国" if c == 0 else PREF[c - 1])
an.to_csv(PRO / "annual_pref.csv", index=False, encoding="utf-8")
rows = []
for ym, d in mo.items():
    if "/" not in ym:
        continue
    y, m = map(int, ym.split("/"))
    for k, v in d.items():
        if not v:
            continue
        code = 0 if k == "total" else int(k)
        rows.append(dict(ym=ym, year=y, month=m, code=code, new=f(v.get("newContract")), inforce=f(v.get("inforceContracts"))))
mon = pd.DataFrame(rows).sort_values(["code", "ym"])
mon.to_csv(PRO / "monthly_pref.csv", index=False, encoding="utf-8")
# 照合：第12表
chk = []
for fn in ["k_2015.xlsx", "k_2020.xlsx", "k_2025.xlsx"]:
    ws = openpyxl.load_workbook(RAW / fn, read_only=True, data_only=True)["第12表"]
    rs = [[c for c in r if c is not None] for r in ws.iter_rows(values_only=True)]
    hdr = next(r for r in rs if len(r) == 6 and all(isinstance(x, (int, str)) for x in r) and str(r[0]).replace("平成", "").isdigit())
    yrs = [int(x) if isinstance(x, int) else 1988 + int(str(x).replace("平成", "")) for x in hdr[:5]]
    for r in rs:
        if r and isinstance(r[0], str):
            name = r[0].replace("　", "").replace(" ", "")
            name = "全国" if name == "合計" else name.rstrip("都府県") if name not in ("北海道", "京都府") else name.replace("府", "")
            if name in PREF or name == "全国":
                vals = [x for x in r[1:] if isinstance(x, (int, float))]
                for yy, vv in zip(yrs, vals[:5]):
                    chk.append(dict(file=fn, pref=name, year=yy, table12=float(vv)))
chk = pd.DataFrame(chk)
m = chk.merge(an[["pref", "year", "futai"]], on=["pref", "year"], how="left")
m["diff"] = (m["table12"] - m["futai"]).round(3)
m.to_csv(PRO / "check_table12.csv", index=False, encoding="utf-8")
print("annual", an.shape, "years", an.year.min(), an.year.max(), "futai from", an.dropna(subset=["futai"]).year.min())
print("monthly", mon.shape, mon.ym.min(), mon.ym.max())
print("table12 rows", len(m), "prefs", m.pref.nunique(), "max |diff|", m["diff"].abs().max(), "missing", m["futai"].isna().sum())
