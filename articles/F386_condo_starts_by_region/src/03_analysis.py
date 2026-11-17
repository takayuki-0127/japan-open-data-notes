"""03 分析（オフライン）：分譲マンションの着工戸数を、三大都市圏・地方圏、8地方に分けて比べる。
結果：results/main.json と CSV"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "starts_pref_long.csv")
PREFS = list(dict.fromkeys(d.loc[d.area != "全国", "area"]))  # 北から南の順（表の順）
assert len(PREFS) == 47 and PREFS[0] == "北海道" and PREFS[-1] == "沖縄県"
METRO = {"首都圏": ["埼玉県", "千葉県", "東京都", "神奈川県"], "中部圏": ["岐阜県", "静岡県", "愛知県", "三重県"],
         "近畿圏": ["京都府", "大阪府", "兵庫県", "奈良県"]}
P2M = {p: m for m, ps in METRO.items() for p in ps}
REG8 = {"北海道": PREFS[0:1], "東北": PREFS[1:7], "関東": PREFS[7:14], "中部": PREFS[14:23], "近畿": PREFS[23:30],
        "中国": PREFS[30:35], "四国": PREFS[35:39], "九州・沖縄": PREFS[39:47]}
assert REG8["関東"][-1] == "神奈川県" and REG8["中部"][-1] == "愛知県" and REG8["近畿"][0] == "三重県" and REG8["四国"][-1] == "高知県"
P2R = {p: r for r, ps in REG8.items() for p in ps}
NONWOOD = ["鉄骨鉄筋コンクリート造", "鉄筋コンクリート造", "鉄骨造"]
BASE, RECENT = (2005, 2007), (2023, 2025)
p = d[d.area != "全国"].copy()


def series(mask):
    """都道府県×年の 戸数・床面積"""
    x = p[mask].groupby(["area", "year"])[["units", "floor_m2"]].sum().reset_index()
    full = pd.MultiIndex.from_product([PREFS, sorted(p.year.unique())], names=["area", "year"])
    return x.set_index(["area", "year"]).reindex(full, fill_value=0).reset_index()


bun = p.tenure == "分譲住宅"
DEF = {"mansion": bun & (p.type == "共同住宅") & p.struct.isin(NONWOOD),   # 国交省の「分譲マンション」
       "bunjo_kyodo_all": bun & (p.type == "共同住宅") & (p.struct == "計"),
       "bunjo_detached": bun & (p.type == "一戸建") & (p.struct == "計"),
       "bunjo_all": bun & (p.type == "計") & (p.struct == "計"),
       "all_housing": (p.tenure == "計") & (p.struct == "計") & (p.type == "計")}
S = {k: series(m) for k, m in DEF.items()}
for k in S:
    S[k]["metro"] = S[k].area.map(P2M).fillna("地方圏")
    S[k]["metro3"] = np.where(S[k].area.isin(P2M), "三大都市圏", "地方圏")
    S[k]["region"] = S[k].area.map(P2R)


def avg(x, yrs, by):
    y0, y1 = yrs
    z = x[(x.year >= y0) & (x.year <= y1)].groupby(by)[["units", "floor_m2"]].sum() / (y1 - y0 + 1)
    return z


def compare(x, by, base=BASE, recent=RECENT, order=None):
    a, b = avg(x, base, by), avg(x, recent, by)
    t = pd.DataFrame({"base_units": a.units, "recent_units": b.units, "base_floor_per_unit": a.floor_m2 / a.units,
                      "recent_floor_per_unit": b.floor_m2 / b.units})
    t["change_pct"] = (t.recent_units / t.base_units - 1) * 100
    tot_a, tot_b = a.units.sum(), b.units.sum()
    t["base_share_pct"] = t.base_units / tot_a * 100
    t["recent_share_pct"] = t.recent_units / tot_b * 100
    t["contrib_pct"] = (t.base_units - t.recent_units) / (tot_a - tot_b) * 100
    if order:
        t = t.loc[order]
    return t


M = S["mansion"]
ORD_METRO = ["首都圏", "中部圏", "近畿圏", "地方圏"]
ORD_REG = list(REG8)
t_metro = compare(M, "metro", order=ORD_METRO)
t_m3 = compare(M, "metro3", order=["三大都市圏", "地方圏"])
t_reg = compare(M, "region", order=ORD_REG)
nat_b, nat_r = avg(M, BASE, "year").units.sum() / 1, avg(M, RECENT, "year").units.sum()
natA, natB = avg(M.assign(k=1), BASE, "k"), avg(M.assign(k=1), RECENT, "k")
nat = {"base_units": float(natA.units.iloc[0]), "recent_units": float(natB.units.iloc[0]),
       "change_pct": float((natB.units.iloc[0] / natA.units.iloc[0] - 1) * 100),
       "base_floor_per_unit": float(natA.floor_m2.iloc[0] / natA.units.iloc[0]),
       "recent_floor_per_unit": float(natB.floor_m2.iloc[0] / natB.units.iloc[0])}

# 年ごとの推移（図1）
ann = M.groupby(["year", "metro"])[["units", "floor_m2"]].sum().unstack("metro")
ts = pd.DataFrame({m: ann["units"][m] for m in ORD_METRO})
ts["全国"] = ts.sum(axis=1)
ts.index.name = "year"
ts.astype(int).to_csv(RES / "annual_by_metro.csv")
peak_year = int(ts["全国"].idxmax())
trough_year = int(ts.loc[2008:, "全国"].idxmin())
fpu = M.groupby(["year", "metro3"])[["units", "floor_m2"]].sum()
fpu = (fpu.floor_m2 / fpu.units).unstack("metro3")
fpu["全国"] = M.groupby("year").floor_m2.sum() / M.groupby("year").units.sum()
fpu.round(2).to_csv(RES / "floor_per_unit_annual.csv")

# 都道府県の数（順位は作らない。北から南の表として出す）
tp = compare(M, "area", order=PREFS)
tp["metro3"] = np.where(tp.index.isin(P2M), "三大都市圏", "地方圏")
tp["region"] = tp.index.map(P2R)
tp.round(2).to_csv(RES / "pref_table_north_to_south.csv")
n_dec = {g: int(((tp.metro3 == g) & (tp.recent_units < tp.base_units)).sum()) for g in ["三大都市圏", "地方圏"]}
n_tot = {g: int((tp.metro3 == g).sum()) for g in ["三大都市圏", "地方圏"]}
n_half = {g: int(((tp.metro3 == g) & (tp.change_pct <= -50)).sum()) for g in ["三大都市圏", "地方圏"]}

# 頑健性
def summary(x, base, recent):
    m3 = compare(x, "metro3", base, recent, order=["三大都市圏", "地方圏"])
    mt = compare(x, "metro", base, recent, order=ORD_METRO)
    a, b = avg(x.assign(k=1), base, "k"), avg(x.assign(k=1), recent, "k")
    return {"全国の変化%": (b.units.iloc[0] / a.units.iloc[0] - 1) * 100,
            "三大都市圏の変化%": m3.change_pct["三大都市圏"], "地方圏の変化%": m3.change_pct["地方圏"],
            "首都圏の割合(基準)%": mt.base_share_pct["首都圏"], "首都圏の割合(直近)%": mt.recent_share_pct["首都圏"],
            "全国の1戸あたり床面積(基準)": a.floor_m2.iloc[0] / a.units.iloc[0], "全国の1戸あたり床面積(直近)": b.floor_m2.iloc[0] / b.units.iloc[0],
            "三大都市圏の床面積の変化": m3.recent_floor_per_unit["三大都市圏"] - m3.base_floor_per_unit["三大都市圏"],
            "地方圏の床面積の変化": m3.recent_floor_per_unit["地方圏"] - m3.base_floor_per_unit["地方圏"]}


rob = []
rob.append(("0 主：2005〜07年 → 2023〜25年（分譲マンション）", summary(M, BASE, RECENT)))
rob.append(("1a 基準を1994〜96年に", summary(M, (1994, 1996), RECENT)))
rob.append(("1b 基準を2013〜15年に", summary(M, (2013, 2015), RECENT)))
rob.append(("1c 直近を2025年の1年だけに", summary(M, BASE, (2025, 2025))))
rob.append(("2 定義：分譲の共同住宅すべて（木造なども含む）", summary(S["bunjo_kyodo_all"], BASE, RECENT)))
# 4 東京都を除く
Mx = M[M.area != "東京都"]
ex = summary(Mx, BASE, RECENT)
rob.append(("4 東京都を除く（首都圏は埼玉・千葉・神奈川）", ex))
rb = pd.DataFrame([dict(確かめ=k, **{kk: round(float(vv), 2) for kk, vv in v.items()}) for k, v in rob])
rb.to_csv(RES / "robustness.csv", index=False)

# 問い直し：分譲の一戸建てと比べる（マンションが一戸建てに置き換わったのか）
D = S["bunjo_detached"]
t_det = compare(D, "metro", order=ORD_METRO)
t_det_reg = compare(D, "region", order=ORD_REG)
A = S["bunjo_all"]
ratio = []
for g, x in (("三大都市圏", "三大都市圏"), ("地方圏", "地方圏")):
    for per, yrs in (("base", BASE), ("recent", RECENT)):
        mm = avg(M[M.metro3 == x].assign(k=1), yrs, "k").units.iloc[0]
        dd = avg(D[D.metro3 == x].assign(k=1), yrs, "k").units.iloc[0]
        aa = avg(A[A.metro3 == x].assign(k=1), yrs, "k").units.iloc[0]
        ratio.append(dict(group=g, period=per, mansion=mm, detached=dd, bunjo_all=aa, mansion_share_pct=mm / aa * 100))
ratio = pd.DataFrame(ratio)
req = pd.concat([t_reg[["base_units", "recent_units", "change_pct"]].add_prefix("mansion_"),
                 t_det_reg[["base_units", "recent_units", "change_pct"]].add_prefix("detached_")], axis=1)
# 8地方ごとの分譲に占めるマンションの割合
for per, yrs in (("base", BASE), ("recent", RECENT)):
    req[f"mansion_share_of_bunjo_{per}_pct"] = (avg(M, yrs, "region").units / avg(A, yrs, "region").units * 100).loc[ORD_REG]
req.index.name = "region"
req.round(2).to_csv(RES / "requestion_detached.csv")
ratio.round(2).to_csv(RES / "requestion_share_metro3.csv", index=False)
# 住宅全体の着工の変化（比べる目安）
H = S["all_housing"]
t_all_m3 = compare(H, "metro3", order=["三大都市圏", "地方圏"])

t_metro.round(2).to_csv(RES / "metro_compare.csv")
t_reg.round(2).to_csv(RES / "region8_compare.csv")

R = lambda v, k=1: round(float(v), k)
main = {
    "period": {"base": "2005-2007平均", "recent": "2023-2025平均"},
    "national": {k: R(v, 1) for k, v in nat.items()},
    "national_peak_year_1988_2025": peak_year, "national_peak_units": int(ts["全国"].max()),
    "national_trough_year_after_2008": trough_year, "national_trough_units": int(ts.loc[trough_year, "全国"]),
    "units_2025": int(ts.loc[2025, "全国"]), "units_2006": int(ts.loc[2006, "全国"]),
    "metro": {g: {k: R(t_metro.loc[g, k]) for k in t_metro.columns} for g in ORD_METRO},
    "metro3": {g: {k: R(t_m3.loc[g, k]) for k in t_m3.columns} for g in t_m3.index},
    "region8": {g: {k: R(t_reg.loc[g, k]) for k in t_reg.columns} for g in ORD_REG},
    "pref_count": {"decreased": n_dec, "total": n_tot, "halved_or_more": n_half},
    "all_housing_change_pct": {g: R(t_all_m3.change_pct[g]) for g in t_all_m3.index},
    "requestion": {"detached_metro": {g: {k: R(t_det.loc[g, k]) for k in ["base_units", "recent_units", "change_pct"]} for g in ORD_METRO},
                   "mansion_share_of_bunjo": {f"{r.group}_{r.period}": R(r.mansion_share_pct) for r in ratio.itertuples()}},
    "robustness": {r["確かめ"]: {k: v for k, v in r.items() if k != "確かめ"} for r in rb.to_dict("records")},
}
H1 = nat["change_pct"] <= -50
H2 = t_m3.change_pct["地方圏"] < t_m3.change_pct["三大都市圏"]
H3 = t_metro.recent_share_pct["首都圏"] > t_metro.base_share_pct["首都圏"]
fd = {g: t_m3.recent_floor_per_unit[g] - t_m3.base_floor_per_unit[g] for g in t_m3.index}
H4n = nat["recent_floor_per_unit"] < nat["base_floor_per_unit"]
main["floor_change_m2"] = {"全国": R(nat["recent_floor_per_unit"] - nat["base_floor_per_unit"]), **{g: R(v) for g, v in fd.items()}}
main["hypotheses"] = {"H1": "支持" if H1 else "外れ", "H2": "支持" if H2 else "外れ", "H3": "支持" if H3 else "外れ",
                      "H4": ("支持" if all(v < 0 for v in fd.values()) else "一部支持") if H4n else "外れ"}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1))
