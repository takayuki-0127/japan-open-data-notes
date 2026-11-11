"""F270 02 整形：Excel・CSV から分析用の表を作る（data/processed）。"""
import os, re, csv, io
import xlrd, pandas as pd, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw"); XLS = os.path.join(RAW, "xls")
OUT = os.path.join(HERE, "..", "data", "processed"); os.makedirs(OUT, exist_ok=True)
YEARS = list(range(2011, 2020)) + [2022, 2023, 2024, 2025]
NAME = {"全体": "全体", "全国籍･地域": "全体", "中国（台湾）": "台湾", "中国 [香港]": "香港"}
# 表の選び方：パッケージツアー参加費の内訳を含む1人1回当たり旅行消費単価（＝公表の「1人当たり旅行支出」）
PKG = {2011: "付表４", 2012: "付表４", 2013: "付表４", 2014: "参考表１", 2015: "参考表１", 2016: "参考表１", 2017: "参考表１"}
EXC = {2011: "第７表", 2012: "第７表", 2013: "第７表", 2014: "第７表", 2015: "第６表", 2016: "第６表", 2017: "第６表"}
NIG = {2011: "付表３", 2012: "付表３", 2013: "付表３", 2014: "第１０表", 2015: "第９表", 2016: "第９表", 2017: "第９表"}

def parse(sheet):
    r0 = c0 = None
    for r in range(12):
        for c in range(4):
            if str(sheet.cell_value(r, c)).strip() == "調査項目":
                r0, c0 = r, c
        if r0 is not None:
            break
    names = {j: str(sheet.cell_value(r0, j)).strip() for j in range(c0 + 1, sheet.ncols) if str(sheet.cell_value(r0, j)).strip()}
    rr = next(r for r in range(r0 + 1, r0 + 6) if str(sheet.cell_value(r, c0)).strip().startswith("全体"))
    out = {}
    for j, n in names.items():
        n = NAME.get(n, n)
        v = sheet.cell_value(rr, j + 1)
        out[n] = (float(sheet.cell_value(rr, j) or 0), float(v) if isinstance(v, float) else np.nan)
    return out

rows = []
for y in YEARS:
    b = xlrd.open_workbook(os.path.join(XLS, f"spend_{y}.xls"), on_demand=True)
    p = parse(b.sheet_by_name(PKG.get(y, "参考1")))
    e = parse(b.sheet_by_name(EXC.get(y, "表3-1")))
    g = parse(b.sheet_by_name(NIG.get(y, "表4-1")))
    for n in p:
        rows.append(dict(year=y, nat=n, n_resp=p[n][0], pc_pkg=p[n][1], pc_exc=e.get(n, (np.nan, np.nan))[1], nights=g.get(n, (np.nan, np.nan))[1]))
pc = pd.DataFrame(rows)
pc.to_csv(os.path.join(OUT, "per_capita_by_nat.csv"), index=False, float_format="%.4f")

# 訪日外客数（JNTO、国籍別・年）
j = pd.read_csv(os.path.join(RAW, "jnto_monthly_2003_2026.csv"))
j = j[(j.year >= 2011) & (j.year <= 2025)]
JN = {"総数": "全体", "豪州": "オーストラリア"}
ann = j.groupby(["year", "market"], as_index=False).visitors.sum()
ann["nat"] = ann.market.map(lambda m: JN.get(m, m))
ann[["year", "nat", "visitors"]].to_csv(os.path.join(OUT, "arrivals_by_nat.csv"), index=False)

# 消費者物価（日本、2020年=100、年平均）
txt = open(os.path.join(RAW, "cpi_2020base_monthly_estat.csv"), encoding="cp932").read()
L = list(csv.reader(io.StringIO(txt)))
head = L[0]
want = {"総合": "cpi_all", "生鮮食品を除く総合": "cpi_core", "外食": "cpi_eatout", "交通": "cpi_transport", "教養娯楽サービス": "cpi_recserv"}
idx = {want[h]: k for k, h in enumerate(head) if h in want}
recs = []
for r in L[3:]:
    if re.fullmatch(r"\d{6}", r[0] or ""):
        d = dict(ym=int(r[0]))
        for k, i in idx.items():
            d[k] = float(r[i]) if r[i].strip() else np.nan
        recs.append(d)
cpi = pd.DataFrame(recs); cpi["year"] = cpi.ym // 100
cpi = cpi.groupby("year").mean(numeric_only=True).drop(columns="ym").reset_index()
cpi = cpi[(cpi.year >= 2010) & (cpi.year <= 2025)]
cpi.to_csv(os.path.join(OUT, "cpi_japan_annual.csv"), index=False, float_format="%.4f")

# FRED：為替（年平均）と米国の消費者物価（年平均）・各国の物価上昇率
def fred(s):
    d = pd.read_csv(os.path.join(RAW, f"fred_{s}.csv")); d.columns = ["date", s]
    d["year"] = pd.to_datetime(d.date).dt.year; d[s] = pd.to_numeric(d[s], errors="coerce")
    return d.groupby("year")[s].mean()
fx = pd.concat([fred(s) for s in ["AEXJPUS", "AEXCHUS", "AEXKOUS", "AEXTAUS", "AEXHKUS", "AEXTHUS", "AEXSIUS", "AEXMAUS", "AEXINUS", "AEXUSUK", "AEXUSEU", "AEXCAUS", "AEXUSAL", "CPIAUCSL"]], axis=1)
infl = pd.concat([fred("FPCPITOTLZG" + c).rename(c) for c in ["KOR", "CHN", "HKG", "THA", "SGP", "USA", "GBR", "AUS", "CAN", "DEU", "FRA", "MYS", "IND"]], axis=1)
fx = fx.join(infl, how="outer")
fx = fx[(fx.index >= 2010) & (fx.index <= 2025)]
fx.reset_index().rename(columns={"index": "year"}).to_csv(os.path.join(OUT, "fx_prices_annual.csv"), index=False, float_format="%.6f")
print(pc[pc.nat == "全体"][["year", "n_resp", "pc_pkg", "pc_exc", "nights"]].to_string(index=False))
print(sorted(set(pc.nat)))
print(sorted(set(ann.nat)))
