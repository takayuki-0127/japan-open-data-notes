"""元の表から、使う値だけを抜き出して data/ に CSV で置く。行・列は見出しの文字で選ぶ。"""
import json, re, io
import pandas as pd
from common import RAW, DATA, PREFS, norm, gyotai_of, pref_of, year_of, num, xls_sheets, xlsx_sheet

checks = {}

# ---- 1. 表2（都道府県別、1972〜2004年）：全国の小売業 ----
rows = list(xls_sheets("shogyo_ts_pref_1972_2004.xls").values())[0]
gi = next(i for i, r in enumerate(rows) if "小売業" in [norm(c) for c in r])
start = [norm(c) for c in rows[gi]].index("小売業")
ci = next(i for i in range(gi, gi + 3) if any("売場面積" in norm(c) for c in rows[i]))
c_sales = next(j for j in range(start, len(rows[ci])) if "年間商品販売額" in norm(rows[ci][j]))
c_floor = next(j for j in range(start, len(rows[ci])) if "売場面積" in norm(rows[ci][j]))
c_pref = next(j for j, c in enumerate(rows[gi]) if norm(c) == "都道府県")
c_year = next(j for j, c in enumerate(rows[gi]) if norm(c) == "年次")
recs, pref, prev_year = [], None, None
for r in rows[ci + 1:]:
    p = norm(r[c_pref])
    if p:
        pref = "全国" if p == "全国" else pref_of(p)
    lab = norm(r[c_year])
    y = year_of(lab)
    if y is not None:
        kind = "level"; prev_year = y
    elif lab == "" and prev_year == 1991 and num(r[c_sales]) is not None:
        y, kind = 1991, "level_retab"  # 平成6年調査と対応させて再集計した平成3年の値
    elif "調整済前回比" in lab:
        y, kind = prev_year, "adj_pct"
    else:
        continue
    if pref is None:
        continue
    recs.append({"pref": pref, "year": y, "kind": kind, "sales_mil_yen": num(r[c_sales]), "floor_m2": num(r[c_floor])})
ts = pd.DataFrame(recs)
nat = ts[ts.pref == "全国"].sort_values(["year", "kind"]).reset_index(drop=True)
nat.to_csv(DATA / "national_ts.csv", index=False)
checks["ts_columns"] = {"sales": norm(rows[ci][c_sales]), "floor": norm(rows[ci][c_floor])}
checks["ts_prefs_found"] = int(ts[ts.pref != "全国"].pref.nunique())
lv = ts[ts.kind == "level"]
s = lv[lv.pref != "全国"].groupby("year").sales_mil_yen.sum()
n = lv[lv.pref == "全国"].set_index("year").sales_mil_yen
checks["ts_pref_sum_minus_national_sales"] = {int(y): float(s[y] - n[y]) for y in n.index}

# ---- 2. 表3・表4（業態別、都道府県別）----
def gyotai_table(fname, want):
    out = []
    for sname, rows in xls_sheets(fname).items():
        if want not in norm(sname):
            continue
        yi = next(i for i, r in enumerate(rows) if sum(1 for c in r if year_of(c)) >= 6)
        labs = {}  # 列 → その列から始まる見出し（見出しの行のうち、いちばん下にあるもの）
        for i in range(yi):
            for j, c in enumerate(rows[i]):
                if norm(c) and "単位" not in norm(c):
                    labs[j] = norm(c)
        cols = {}
        for j, c in enumerate(rows[yi]):
            y = year_of(c)
            if y is None:
                continue
            k = max(jj for jj in labs if jj <= j)
            g = gyotai_of(labs[k])
            if g:
                cols[j] = (g, y)
        c_name = next(j for j in range(4) if any(pref_of(r[j]) for r in rows[yi + 1:] if j < len(r)))
        for r in rows[yi + 1:]:
            nm = norm(r[c_name])
            p = "全国" if nm == "全国計" else pref_of(nm)
            if p is None:
                continue
            for j, (g, y) in cols.items():
                out.append({"pref": p, "year": y, "gyotai": g, "value": num(r[j])})
    return pd.DataFrame(out)

g = []
for fname, ws, wf in [("shogyo_gyotai_pref_1991_1997.xls", "販売額", "売場面積"), ("shogyo_gyotai_pref_1999_2004.xls", "販売額", "売場面積")]:
    a = gyotai_table(fname, ws).rename(columns={"value": "sales_mil_yen"})
    b = gyotai_table(fname, wf).rename(columns={"value": "floor_m2"})
    g.append(a.merge(b, on=["pref", "year", "gyotai"], how="outer"))
gy = pd.concat(g)

# ---- 3. 2007年 業態別統計表 第4表 ----
rows = xls_sheets("shogyo_2007_gyotai.xls")["業態４表"]
hi = next(i for i, r in enumerate(rows) if "売場面積" in [norm(c) for c in r] and "都道府県" in [norm(c) for c in r])
hs = next(i for i, r in enumerate(rows) if any("年間商品販売額" == norm(c) for c in r) and i < hi)
c_s = next(j for j, c in enumerate(rows[hs]) if norm(c) == "年間商品販売額")  # 年間商品販売額のかたまりの最初の列＝計
c_f = [norm(c) for c in rows[hi]].index("売場面積")
c_eff = max(j for j, c in enumerate(rows[hi]) if "年間商品販売額" in norm(c))  # 販売効率：売場面積1㎡当たり
c_p = next(j for j, c in enumerate(rows[hi]) if norm(c) == "都道府県")
c_g = next(j for j, c in enumerate(rows[hi]) if "業態分類" in norm(c))
o7, eff7 = [], []
for r in rows[hi + 1:]:
    code = norm(r[c_p])
    m = re.match(r"^(\d\d)(.*)$", code)
    if not m or int(m.group(1)) > 47:
        continue
    p = "全国" if m.group(1) == "00" else pref_of(m.group(2))
    gk = gyotai_of(r[c_g])
    if p is None or gk is None:
        continue
    o7.append({"pref": p, "year": 2007, "gyotai": gk, "sales_mil_yen": num(r[c_s]), "floor_m2": num(r[c_f])})
    if p == "全国":
        eff7.append({"gyotai": gk, "table_eff_10k_yen_per_m2": num(r[c_eff])})
gy = pd.concat([gy, pd.DataFrame(o7)]).sort_values(["pref", "gyotai", "year"]).reset_index(drop=True)
gy.to_csv(DATA / "gyotai_pref.csv", index=False)
checks["header_2007"] = {"sales": norm(rows[hs][c_s]), "floor": norm(rows[hi][c_f]), "eff": norm(rows[hi][c_eff])}

# ---- 4. 2014年（参考）第1表の全国・従業者規模「計」の行 ----
rows = xlsx_sheet("shogyo_2014_gyotai.xlsx", "業態第1表")
hi = next(i for i, r in enumerate(rows) if "売場面積" in [norm(c) for c in r])
c_s = next(j for j, c in enumerate(rows[hi]) if norm(c) == "年間商品販売額")
c_f = [norm(c) for c in rows[hi]].index("売場面積")
o14 = []
for r in rows[hi + 1:]:
    if norm(r[1]) != "00全国" or norm(r[3]) != "計":
        continue
    gk = gyotai_of(r[2])
    if gk:
        o14.append({"pref": "全国", "year": 2014, "gyotai": gk, "sales_mil_yen": num(r[c_s]), "floor_m2": num(r[c_f])})
pd.DataFrame(o14).to_csv(DATA / "gyotai_2014_reference.csv", index=False)
checks["header_2014"] = {"sales": norm(rows[hi][c_s]), "floor": norm(rows[hi][c_f]), "gyotai_found": [d["gyotai"] for d in o14]}

# ---- 5. 消費者物価指数（暦年）----
txt = (RAW / "cpi_2025base_annual_class.csv").read_bytes().decode("cp932")
cp = pd.read_csv(io.StringIO(txt), header=None, dtype=str)
head = [norm(x) for x in cp.iloc[0]]
k_all, k_xr = head.index("総合"), head.index("持家の帰属家賃を除く総合")
cpi = []
for _, r in cp.iterrows():
    t = norm(r[0])
    if re.fullmatch(r"(19|20)\d\d", t):
        cpi.append({"year": int(t), "cpi_all": float(r[k_all]), "cpi_ex_rent": float(r[k_xr])})
pd.DataFrame(cpi).to_csv(DATA / "cpi_annual.csv", index=False)
checks["cpi_columns"] = [head[k_all], head[k_xr]]

# ---- 読み取りの確かめ ----
lv = gy[gy.gyotai == "total"]
sp = lv[lv.pref != "全国"].groupby("year")[["sales_mil_yen", "floor_m2"]].sum()
sn = lv[lv.pref == "全国"].set_index("year")[["sales_mil_yen", "floor_m2"]]
checks["gyotai_pref_sum_minus_national"] = {int(y): {"sales": float(sp.loc[y, "sales_mil_yen"] - sn.loc[y, "sales_mil_yen"]),
                                                     "floor": float(sp.loc[y, "floor_m2"] - sn.loc[y, "floor_m2"])} for y in sn.index}
checks["prefs_per_year"] = {int(y): int(lv[(lv.pref != "全国") & (lv.year == y)].pref.nunique()) for y in sn.index}
# 重なりのない業態の和＝合計（全国）
parts = ["dept", "gms", "spec_super", "cvs", "drug", "other_super", "specialty", "center", "other_store"]
nat_g = gy[gy.pref == "全国"].pivot_table(index="year", columns="gyotai", values=["sales_mil_yen", "floor_m2"], aggfunc="first")
for v in ("sales_mil_yen", "floor_m2"):
    t = nat_g[v]
    ps = t[[c for c in parts if c in t.columns]].sum(axis=1, min_count=1)
    checks[f"gyotai_parts_sum_minus_total_{v}"] = {int(y): float(ps[y] - t.loc[y, "total"]) for y in t.index}
# 表2の全国（そのままの値）と業態表の合計
checks["ts_vs_gyotai_total"] = {int(y): {"ts_sales": float(nat[(nat.year == y) & (nat.kind == "level")].sales_mil_yen.iloc[0]),
                                         "gyotai_sales": float(sn.loc[y, "sales_mil_yen"]),
                                         "ts_floor": float(nat[(nat.year == y) & (nat.kind == "level")].floor_m2.iloc[0]),
                                         "gyotai_floor": float(sn.loc[y, "floor_m2"])} for y in sn.index if y <= 2004}
# 2007年：表の1㎡当たり（万円）と、自分で割った値
e = pd.DataFrame(eff7).set_index("gyotai")
g7 = gy[(gy.pref == "全国") & (gy.year == 2007)].set_index("gyotai")
calc = (g7.sales_mil_yen * 100 / g7.floor_m2).round(0)
checks["eff2007_table_vs_calc"] = {k: {"table": e.loc[k, "table_eff_10k_yen_per_m2"], "calc": float(calc[k])} for k in e.index if k in calc.index}
json.dump(checks, open(DATA / "build_checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(checks, ensure_ascii=False, indent=0)[:6000])
