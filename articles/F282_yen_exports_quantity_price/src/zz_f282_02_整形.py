"""02 整形：貿易指数（年・年度・月、地域別）と日銀の物価・為替を、それぞれ1つの表にする。"""
import csv, json, re, pathlib
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
MON = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
rows = []
for f in sorted(RAW.glob("idx_*.csv")):
    vint = int(f.stem.split("_")[1])
    for r in csv.reader(open(f, encoding="shift_jis", errors="ignore")):
        if len(r) < 8 or not re.match(r"^\d{4}", r[0]):
            continue
        p = r[0].strip(); kind = None; key = None
        if re.fullmatch(r"\d{4}", p):
            kind, key = "CY", p
        elif re.fullmatch(r"\d{4} \(FY\)", p):
            kind, key = "FY", p[:4]
        else:
            m = re.fullmatch(r"(\d{4}) ([A-Z][a-z]{2})\.", p)
            if m:
                kind, key = "M", f"{m.group(1)}-{MON[m.group(2)]:02d}"
        if kind is None:
            continue
        rows.append(dict(kind=kind, period=key, area=r[1].strip(), vintage=vint,
                         V=float(r[2]), Q=float(r[3]), UV=float(r[4])))
t = pd.DataFrame(rows)
# 同じ期間・地域が複数の年の表にあるときは、いちばん新しい表（改定後）を使う
t = t.sort_values("vintage").groupby(["kind", "period", "area"], as_index=False).last()
t.to_csv(OUT / "trade_index.csv", index=False)
print("trade_index:", t.groupby("kind").size().to_dict(), "areas:", sorted(t.area.unique()))
print("monthly range:", t[t.kind == "M"].period.min(), t[t.kind == "M"].period.max())

def boj(fn):
    d = json.load(open(RAW / fn, encoding="utf-8"))
    out = {}
    for s in d["RESULTSET"]:
        v = s["VALUES"]
        out[s["SERIES_CODE"]] = pd.Series(
            [float(x) if x not in (None, "") else float("nan") for x in v["VALUES"]],
            index=[f"{str(x)[:4]}-{str(x)[4:6]}" for x in v["SURVEY_DATES"]])
    return pd.DataFrame(out)
b = pd.concat([boj("boj_export_prices.json"), boj("boj_usdjpy.json"), boj("boj_eer.json")], axis=1)
b.index.name = "month"
b.to_csv(OUT / "boj_monthly.csv")
print("boj:", b.shape, b.index.min(), b.index.max(), "NaN:", int(b.isna().sum().sum()))

cs = []
for r in csv.reader(open(RAW / "currency_share_export.csv", encoding="shift_jis", errors="ignore")):
    if len(r) < 14 or not re.match(r"^\d{4}", r[0]):
        continue
    d = dict(half=r[0].strip(), area=r[1].strip())
    for k in range(6):
        cur, sh = r[2 + 2 * k].strip(), r[3 + 2 * k].strip()
        if cur and sh:
            d[cur] = float(sh)
    cs.append(d)
cs = pd.DataFrame(cs).fillna(0.0)
cs.to_csv(OUT / "currency_share.csv", index=False)
print("currency share rows:", len(cs), cs.half.iloc[0], "...", cs.half.iloc[-1])
