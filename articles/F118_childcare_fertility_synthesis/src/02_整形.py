"""02 整形：都道府県×年のパネル（022 の再推定用）を、共通の単位（在所児・0〜5歳100人あたり）で作る"""
from common import *

# SSDSE-B（022 と同じファイル）
h = pd.read_csv(RAW / "SSDSE-B-2026.csv", encoding="cp932", header=None, nrows=2)
d = pd.read_csv(RAW / "SSDSE-B-2026.csv", encoding="cp932", header=None, skiprows=2)
d.columns = list(h.iloc[0])
d = d.rename(columns={d.columns[0]: "year", d.columns[1]: "code", d.columns[2]: "pref"})
d = d[d.code != "R00000"].copy()
d["pc"] = d.code.str[1:3]

# 0〜5歳の割合（国勢調査の年の市区町村データを県で合計、F16 で取得）。2010・2015・2020 の間は直線で補い、2020年より後は2020年の値
c = pd.read_csv(RAW / "pref_age0_5_census.csv", dtype={"pref": str})
c["r"] = c.A1405 / c.A1301
rows = []
for p, g in c.groupby("pref"):
    g = g.set_index("year").r
    for y in range(2012, 2024):
        rows.append({"pc": p, "year": y, "r": float(np.interp(y, g.index.values, g.values))})
r = pd.DataFrame(rows)
d = d.merge(r, on=["pc", "year"], how="left")
assert d.r.notna().all()
nat = c.groupby("year")[["A1405", "A1301"]].sum(); nat_r = (nat.A1405 / nat.A1301)
d["r_const"] = float(nat_r.loc[2015])

d["tfr"] = d.A4103
d["u15"] = d.A1301
d["age05"] = d.u15 * d.r
# 主な処置：在所児（0〜5歳100人あたり）
d["D"] = d.J2506 / d.age05 * 100
# 代わりの換算
d["D_const"] = d.J2506 / (d.u15 * d.r_const) * 100
d = d.sort_values(["pc", "year"])
d["births6"] = d.groupby("pc").A4101.transform(lambda s: s.rolling(6).sum())   # その年までの6年の出生数（0〜5歳の近似、2017年から）
d["D_births"] = d.J2506 / d.births6 * 100
d["D_cap"] = d.J2505 / d.age05 * 100           # 定員（0〜5歳100人あたり）
d["cap_u15"] = d.J2505 / d.u15 * 100           # 022 のもとの単位（15歳未満100人あたりの定員）
d["job"] = d.F3103 / d.F3102
keep = ["year", "pc", "pref", "tfr", "D", "D_const", "D_births", "D_cap", "cap_u15", "job", "r", "J2506", "J2505", "u15", "age05", "A4101", "births6"]
d[keep].to_csv(DATA / "pref_panel.csv", index=False, encoding="utf-8-sig")
print(d[keep].groupby("year")[["tfr", "D", "D_cap", "cap_u15", "r"]].mean().round(3))
print("0〜5歳 / 15歳未満（全国）:", nat_r.round(4).to_dict())
