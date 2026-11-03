"""社人研2013年推計（市区町村、2010年基準）を JSON から読み、F45 で整形済みの2018・2023年推計と
2025年国勢調査とあわせて、2025年の市区町村の単位・19の年齢区分（90歳以上）にそろえる。

出力（data/）
  pop_units.csv  : code, src, year, sex, a0..a18
       src = act（実績：2010・2015・2020は各推計の基準人口、2025は国勢調査の不詳補完値）、
             ipss13 / ipss18 / ipss23（社人研の推計値）
  surv_units.csv : code, vintage, period, sex, r0..r17（社人研の生残率）
  units.csv      : code, pref, muni, kind
"""
import gzip
import json
import numpy as np
import pandas as pd
from common import RAW, DATA, F45, NA

# 2010年10月以降の市制施行・編入（2025年の単位へ）。岩舟町は2014年に栃木市へ編入したので栃木市ごと除く
CODE_MAP = {3305: 3216, 4423: 4216, 40305: 40231, 17344: 17212, 23304: 23238, 11445: 11246,
            12402: 12239, 43201: 43100, 11226: 11203}
DROP = {9203, 9367}
# 政令市（市全体のコード）
DC = {1100, 4100, 11100, 12100, 14100, 14130, 14150, 15100, 22100, 22130, 23100, 26100, 27100, 27140,
      28100, 33100, 34100, 40100, 40130, 43100}


def to_unit(code):
    code = CODE_MAP.get(code, code)
    if code // 1000 == 7 or code in DROP:      # 福島県は2013・2018年推計に市町村の値がない
        return None
    if code // 1000 != 13 and 101 <= code % 1000 <= 199 and code not in DC:   # 政令市の区は市全体で扱う
        return None
    if code // 1000 == 13 and code % 1000 == 100:
        return None
    return code


def c19(a):
    a = np.asarray(a, float)
    return a if len(a) == 19 else np.concatenate([a[:18], [a[18] + a[19]]])


def c19_rate(rate, pop):
    rate = np.asarray(rate, float)
    if len(rate) == 18:
        return rate
    w = np.array([pop[17], pop[18] + pop[19]], float)
    last = (rate[17] * w[0] + rate[18] * w[1]) / w.sum() if w.sum() > 0 else rate[17]
    return np.concatenate([rate[:17], [last]])


pop_rows, surv_rows, unit_info = [], [], {}

# ---------------------------------------------------------------- 2013年推計（市区町村シート）
J = json.load(gzip.open(RAW / "f160_ipss13_muni.json.gz", "rt", encoding="utf-8"))
for sn, rows in J["kekka"].items():
    code = int(sn.split()[0]); name = sn.split(maxsplit=1)[1]
    u = to_unit(code)
    if u is None:
        continue
    for sex, lab in (("M", "男"), ("F", "女")):
        r0 = [i for i, r in enumerate(rows) if r and r[0] == lab][0]
        years = [int(str(v)[:4]) for v in rows[r0][1:8]]
        block = np.array([[float(x) for x in rows[r0 + 2 + i][1:8]] for i in range(NA)])
        for j, y in enumerate(years):
            if y > 2025:
                continue
            pop_rows.append(dict(code=u, src="act" if y == 2010 else "ipss13", year=y, sex=sex,
                                 **{f"a{i}": block[i, j] for i in range(NA)}))
    e = J["shihyo"][sn]
    for sex, lab in (("M", "男"), ("F", "女")):
        rs = [i for i, r in enumerate(e) if r and r[0] == f"生残率・{lab}"][0]
        periods = [str(v).replace("年", "").replace("\n", "") for v in e[rs + 1][1:4]]
        sv = np.array([[float(x) for x in e[rs + 2 + i][1:4]] for i in range(NA - 1)])
        for j, p in enumerate(periods):
            surv_rows.append(dict(code=u, vintage="ipss13", period=p, sex=sex, **{f"r{i}": sv[i, j] for i in range(NA - 1)}))
    unit_info.setdefault(u, dict(pref=None, muni=name, kind=None))

# ---------------------------------------------------------------- 2018・2023年推計、2025年国勢調査（F45 の整形済み CSV）
def keep_units(df):
    df = df[df.kind.astype(str).isin(["1", "2", "3"]) | ((df.kind.astype(str) == "0") & (df.code // 1000 == 13))].copy()
    df["u"] = df.code.map(to_unit_whole)
    return df[df.u.notna()]


def to_unit_whole(code):
    code = CODE_MAP.get(code, code)
    if code // 1000 == 7 or code in DROP or code == 13100:
        return None
    return code


for v, fn, y0 in (("ipss18", "pop_2018.csv", 2015), ("ipss23", "pop_2023.csv", 2020), ("act", "pop_census2025.csv", 2025)):
    p = keep_units(pd.read_csv(F45 / fn))
    A = [c for c in p.columns if c.startswith("a")]
    for r in p.itertuples(index=False):
        if r.year > 2025:
            continue
        arr = c19([getattr(r, a) for a in A])
        src = "act" if (r.year == y0) else v
        pop_rows.append(dict(code=int(r.u), src=src, year=int(r.year), sex=r.sex, **{f"a{i}": arr[i] for i in range(NA)}))
        inf = unit_info.setdefault(int(r.u), dict(pref=None, muni=None, kind=None))
        inf["pref"] = inf["pref"] or r.pref
        inf["muni"] = r.muni if v == "act" else (inf["muni"] or r.muni)
        inf["kind"] = str(r.kind)

pop = pd.DataFrame(pop_rows)
# 2023年推計の基準（2020年）は、20区分→19区分の生残率の加重に使う
P20 = {(r.code, r.sex): np.array([getattr(r, f"a{i}") for i in range(NA)]) for r in pop[(pop.src == "act") & (pop.year == 2020)].itertuples()}
P23raw = {}
p23 = keep_units(pd.read_csv(F45 / "pop_2023.csv"))
for r in p23.itertuples(index=False):
    P23raw[(int(r.u), int(r.year), r.sex)] = np.array([getattr(r, f"a{i}") for i in range(20)], float)

for v, fn in (("ipss18", "surv_2018.csv"), ("ipss23", "surv_2023.csv")):
    s = keep_units(pd.read_csv(F45 / fn))
    R = [c for c in s.columns if c.startswith("r")]
    for r in s.itertuples(index=False):
        rate = np.array([getattr(r, c) for c in R], float)
        rate = rate[~np.isnan(rate)] if len(rate) > 18 else rate
        if v == "ipss23":
            y0 = int(str(r.period)[:4])
            w = P23raw.get((int(r.u), y0, r.sex))
            rate = c19_rate(rate, w if w is not None else np.ones(20))
        surv_rows.append(dict(code=int(r.u), vintage=v, period=str(r.period).replace("年", ""), sex=r.sex,
                              **{f"r{i}": rate[i] for i in range(NA - 1)}))

surv = pd.DataFrame(surv_rows)
info = pd.DataFrame([dict(code=k, **v) for k, v in unit_info.items()])

# すべての資料にそろっている単位だけ残す
need = [("act", 2010), ("act", 2015), ("act", 2020), ("act", 2025), ("ipss13", 2025), ("ipss18", 2025), ("ipss23", 2025)]
have = pop.groupby(["src", "year"]).code.apply(set)
common = set.intersection(*[have[k] for k in need])
needs = [("ipss13", "2010→2015"), ("ipss18", "2015→2020"), ("ipss23", "2020→2025"), ("ipss23", "2045→2050")]
hs = surv.groupby(["vintage", "period"]).code.apply(set)
common &= set.intersection(*[hs[k] for k in needs])
pop = pop[pop.code.isin(common)].sort_values(["code", "src", "year", "sex"])
surv = surv[surv.code.isin(common)].sort_values(["code", "vintage", "period", "sex"])
info = info[info.code.isin(common)].sort_values("code")
pop.to_csv(DATA / "pop_units.csv", index=False, float_format="%.6g")
surv.to_csv(DATA / "surv_units.csv", index=False, float_format="%.6g")
info.to_csv(DATA / "units.csv", index=False)
print("単位数:", len(common), "| pop行:", len(pop), "| surv行:", len(surv))
print(pop.groupby(["src", "year"]).code.nunique().to_string())
# 合計の確認（実績2010・2015・2020・2025）
for y in (2010, 2015, 2020, 2025):
    t = pop[(pop.src == "act") & (pop.year == y)][[f"a{i}" for i in range(NA)]].to_numpy().sum()
    print(y, f"{t:,.0f}")
