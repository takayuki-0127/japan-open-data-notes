"""02 整形：時系列表（第3表・第4表）から全国と都道府県の表を作る"""
import csv, io, json, pathlib
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
d = json.loads((R / "data/raw/hlts_timeseries_r5.json").read_text())
YEARS = [1958, 1963, 1968, 1973, 1978, 1983, 1988, 1993, 1998, 2003, 2008, 2013, 2018, 2023]
T3 = list(csv.reader(io.StringIO(d["t3__003"])))
T4 = list(csv.reader(io.StringIO(d["t4__総数"])))


def num(x):
    x = x.strip().replace(",", "")
    return float(x) if x not in ("", "-", "…", "x", "X") else None


# 列の位置（第4表）：総数 14 列、その他 9 列（1983-）、賃貸 9 列（1983-、1983〜1998年は売却用を含む）、売却 5 列（2003-）、二次的 10 列（1978-）
assert T4[12][5] == "1958" and T4[12][19] == "1983" and T4[12][28] == "1983" and T4[12][37] == "2003" and T4[12][42] == "1978"
assert T3[9][5] == "1958" and T3[9][19] == "1958"
Y_OTH = YEARS[5:]; Y_SALE = YEARS[9:]; Y_SEC = YEARS[4:]


def parse_t4(row):
    out = {}
    for i, y in enumerate(YEARS): out[(y, "vacant")] = num(row[5 + i])
    for i, y in enumerate(Y_OTH): out[(y, "vac_other")] = num(row[19 + i]); out[(y, "vac_rent")] = num(row[28 + i])
    for i, y in enumerate(Y_SALE): out[(y, "vac_sale")] = num(row[37 + i])
    for i, y in enumerate(Y_SEC): out[(y, "vac_second")] = num(row[42 + i])
    return out


def parse_t3(row):
    out = {}
    for i, y in enumerate(YEARS): out[(y, "stock")] = num(row[5 + i]); out[(y, "households")] = num(row[19 + i])
    return out


# 全国：本系列（沖縄を含む、1973年〜）と注の系列（沖縄を含まない、1958〜1973年）
nat_t3 = [r for r in T3 if len(r) > 4 and r[1] == "全国"]
nat_t4 = [r for r in T4 if len(r) > 4 and r[2] == "全国"]
assert len(nat_t3) == 2 and len(nat_t4) == 2 and nat_t3[1][4] == "1)" and nat_t4[1][4] == "2)"
rows = []
for basis, a, b in [("incl_okinawa", nat_t3[0], nat_t4[0]), ("excl_okinawa", nat_t3[1], nat_t4[1])]:
    p3, p4 = parse_t3(a), parse_t4(b)
    for y in YEARS:
        rec = {"basis": basis, "year": y}
        for k in ["stock", "households"]: rec[k] = p3[(y, k)]
        for k in ["vacant", "vac_other", "vac_rent", "vac_sale", "vac_second"]: rec[k] = p4.get((y, k))
        if rec["stock"] is not None and rec["vacant"] is not None: rows.append(rec)
nat = pd.DataFrame(rows)
nat.to_csv(R / "data/national_long.csv", index=False)

# 都道府県
pref = []
t3p = {r[1]: r for r in T3 if len(r) > 4 and len(r[1]) == 2 and r[1].isdigit() and r[2]}
t4p = {r[1]: r for r in T4 if len(r) > 4 and len(r[1]) == 2 and r[1].isdigit() and r[2] and r[1] != "00"}
assert len(t3p) == 47 and len(t4p) == 47
for c in sorted(t3p):
    p3, p4 = parse_t3(t3p[c]), parse_t4(t4p[c])
    assert t3p[c][2] == t4p[c][2]
    for y in YEARS:
        rec = {"code": int(c), "pref": t3p[c][2], "year": y, "stock": p3[(y, "stock")], "households": p3[(y, "households")]}
        for k in ["vacant", "vac_other", "vac_rent", "vac_sale", "vac_second"]: rec[k] = p4.get((y, k))
        pref.append(rec)
pref = pd.DataFrame(pref)
pref.to_csv(R / "data/pref_long.csv", index=False)
# 確かめ：都道府県の合計と全国（2023年、2018年）
for y in [2018, 2023]:
    s = pref[pref.year == y][["stock", "vacant"]].sum()
    n = nat[(nat.basis == "incl_okinawa") & (nat.year == y)].iloc[0]
    print(y, "pref sum vs national", s.stock, n.stock, s.vacant, n.vacant)
    assert abs(s.stock - n.stock) / n.stock < 0.001 and abs(s.vacant - n.vacant) / n.vacant < 0.002
print(nat.to_string()); print(len(pref))
