"""data/raw から月次の表を作る：ドル円（月中平均・月末）、日米の2年・10年の国債金利（日次の月平均）。
期間は1990年1月〜2026年10月。列は見出しの文字で選ぶ。"""
import json, pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
END = "2026-10"

# 日銀：ドル円
j = json.load(open(RAW / "boj_usdjpy_monthly.json", encoding="utf-8"))
fx = {}
for r in j["RESULTSET"]:
    name = r["NAME_OF_TIME_SERIES_J"]
    key = "usdjpy_avg" if "17時時点/月中平均" in name else ("usdjpy_end" if "中心相場/月末" in name else None)
    if key is None:
        continue
    s = pd.Series(r["VALUES"]["VALUES"], index=[f"{str(x)[:4]}-{str(x)[4:6]}" for x in r["VALUES"]["SURVEY_DATES"]], dtype="float64")
    fx[key] = s
fx = pd.DataFrame(fx)

# 財務省：和暦の日付を西暦に
ERA = {"S": 1925, "H": 1988, "R": 2018}
jg = pd.read_csv(RAW / "mof_jgbcm_all.csv", encoding="cp932", skiprows=1, dtype=str)
jg.columns = [c.strip() for c in jg.columns]
def wareki(s):
    m = re.match(r"([SHR])(\d+)\.(\d+)\.(\d+)", s.strip())
    return pd.Timestamp(ERA[m.group(1)] + int(m.group(2)), int(m.group(3)), int(m.group(4)))
jg["date"] = jg["基準日"].map(wareki)
for c in ["2年", "10年"]:
    jg[c] = pd.to_numeric(jg[c], errors="coerce")
jg["ym"] = jg.date.dt.strftime("%Y-%m")
jp = jg.groupby("ym")[["2年", "10年"]].mean().rename(columns={"2年": "jp2", "10年": "jp10"})

# 米国財務省
us = []
for y in range(1990, 2027):
    u = pd.read_csv(RAW / f"ust_par_yield_{y}.csv")
    u.columns = [c.strip() for c in u.columns]
    us.append(pd.DataFrame({"date": pd.to_datetime(u["Date"], format="%m/%d/%Y"),
                            "us2": pd.to_numeric(u["2 Yr"], errors="coerce"), "us10": pd.to_numeric(u["10 Yr"], errors="coerce")}))
us = pd.concat(us)
us["ym"] = us.date.dt.strftime("%Y-%m")
usm = us.groupby("ym")[["us2", "us10"]].mean()

m = fx.join(jp, how="inner").join(usm, how="inner")
m = m[(m.index >= "1990-01") & (m.index <= END)].sort_index()
m["spread2"] = m.us2 - m.jp2
m["spread10"] = m.us10 - m.jp10
m.index.name = "ym"
m.to_csv(ROOT / "data" / "monthly.csv", float_format="%.6f", lineterminator="\n")
print(m.shape, m.index.min(), m.index.max(), m.isna().sum().to_dict())
