"""第1表から、燃料・業態・区分・車種ごとの 燃料消費量・走行キロ・ℓ/km・km/日 を取り出して data/table1_long.csv にする。
2010年度は、括弧内の参考値（2011年3月の北海道・東北を含む値）を燃料消費量と走行キロに使う。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def n(s):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""


def num(v):
    if isinstance(v, (int, float)) and not pd.isna(v):
        return float(v)
    return None


recs = []
for y in range(2010, 2026):
    f = next(RAW.glob(f"fuel_t1_fy{y}.*"))
    v = list(pd.read_excel(f, header=None, sheet_name=None).values())[0]
    hdr = next(i for i in range(10) if any("燃料消費" in n(c) for c in v.iloc[i]))
    H = [n(c) for c in v.iloc[hdr]]
    c_fuel = next(i for i, h in enumerate(H) if h.startswith("燃料消費"))
    c_km = next(i for i, h in enumerate(H) if h.startswith("走行キロ"))
    c_lkm = next(i for i, h in enumerate(H) if h.startswith("走行1"))
    c_day = next(i for i, h in enumerate(H) if h.startswith("1日1車"))
    if y == 2010:  # 括弧内の参考値は、それぞれの右隣の列
        c_fuel_use, c_km_use = c_fuel + 1, c_km + 1
    else:
        c_fuel_use, c_km_use = c_fuel, c_km
    fuel = biz = grp = None
    for r in range(hdr + 1, len(v)):
        row = v.iloc[r]
        a, b, c, d = n(row[1]), n(row[2]), n(row[3]), n(row[4])
        if a.startswith("(注)") or a.startswith("参考") or a.startswith("及び"):
            break
        if a: fuel = a
        if b: biz = b
        if c: grp = c
        kind = d
        if num(row[c_fuel_use]) is None:
            continue
        recs.append(dict(fy=y, fuel=fuel, biz=biz, grp=grp if not b or c else c, kind=kind,
                         fuel_kl=num(row[c_fuel_use]), km_thousand=num(row[c_km_use]),
                         l_per_km_pub=num(row[c_lkm]), km_per_day=num(row[c_day])))
        if b and not c:  # 「営業用計」などの行のあとは区分を空にする
            grp = None
df = pd.DataFrame(recs)
df.to_csv(ROOT / "data" / "table1_long.csv", index=False)
pc = df[(df.fuel == "ガソリン") & (df.biz == "自家用") & (df.grp == "旅客")]
print(pc.pivot_table(index="fy", columns="kind", values="km_per_day"))
print(df[df.fy == 2025].to_string())
