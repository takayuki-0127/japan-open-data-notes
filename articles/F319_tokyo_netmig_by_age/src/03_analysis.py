"""03 分析：年齢別の寄与、コロナ期の落ち込みの分解、男女、戻り、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
BANDS = {"0-14": AGES[0:3], "15-19": ["15-19"], "20-24": ["20-24"], "25-29": ["25-29"],
         "30-44": AGES[6:9], "45-64": AGES[9:13], "65+": AGES[13:]}
YOUNG = ["15-19", "20-24", "25-29"]

d = pd.read_csv(ROOT / "data" / "netmig_tokyo_age.csv")

def wide(area, nat="日本人", sex="総数"):
    q = d[(d.area == area) & (d.nat == nat) & (d.sex == sex)]
    w = q.pivot(index="year", columns="age", values="net")
    return w[["total"] + AGES].sort_index()

def banded(w):
    b = pd.DataFrame({k: w[v].sum(axis=1) for k, v in BANDS.items()})
    b["total"] = w["total"]
    return b

def r(x, n=1):
    return float(round(float(x), n))

M = {}
# ---- 表：年×年齢帯（東京都・東京圏、日本人、男女計）
tabs = []
for area in ["東京都", "東京圏"]:
    for sex in ["総数", "男", "女"]:
        b = banded(wide(area, sex=sex)).reset_index()
        b.insert(1, "area", area); b.insert(2, "sex", sex)
        tabs.append(b)
T = pd.concat(tabs, ignore_index=True)
T.to_csv(RES / "bands_by_year.csv", index=False)

# ---- H1：若い年齢（15〜29歳）の比率
def young_share(area, young=YOUNG, nat="日本人", years=range(2010, 2026)):
    w = wide(area, nat=nat)
    s = (w[young].sum(axis=1) / w["total"] * 100).loc[[y for y in years if y in w.index]]
    return s

h1 = pd.DataFrame({"東京圏": young_share("東京圏"), "東京都": young_share("東京都")})
h1.index.name = "year"
h1.round(2).to_csv(RES / "young_share.csv")
pre = h1.loc[2010:2019]
M["H1"] = {
    "東京圏_若い比率_2010_2019_最小": r(pre["東京圏"].min()), "東京圏_若い比率_2010_2019_最大": r(pre["東京圏"].max()),
    "東京圏_若い比率_2010_2019_100未満の年数": int((pre["東京圏"] < 100).sum()),
    "東京圏_若い比率_2019": r(h1.loc[2019, "東京圏"]), "東京圏_若い比率_2021": r(h1.loc[2021, "東京圏"]),
    "東京圏_若い比率_2025": r(h1.loc[2025, "東京圏"]),
    "東京圏_若い比率_2020_2025_最小": r(h1.loc[2020:2025, "東京圏"].min()),
    "東京都_若い比率_2010_2019_最小": r(h1.loc[2010:2019, "東京都"].min()),
    "東京都_若い比率_2021": r(h1.loc[2021, "東京都"]),
    "判定": "支持" if (pre["東京圏"] >= 100).all() else "外れ",
}
wk = wide("東京圏")
M["東京圏_2025"] = {"total": int(wk.loc[2025, "total"]), "15-29": int(wk.loc[2025, YOUNG].sum()),
                    "20-24": int(wk.loc[2025, "20-24"]),
                    "その他の年齢": int(wk.loc[2025, "total"] - wk.loc[2025, YOUNG].sum())}
M["東京都_45_64"] = {str(y): int(banded(wide("東京都")).loc[y, "45-64"]) for y in (2019, 2021, 2025)}
M["東京圏_2019"] = {"total": int(wk.loc[2019, "total"]), "15-29": int(wk.loc[2019, YOUNG].sum()),
                    "その他の年齢": int(wk.loc[2019, "total"] - wk.loc[2019, YOUNG].sum())}
# 年齢帯ごとに 2010〜2025 年で正だった年数
bk = banded(wk)
M["東京圏_年齢帯ごとの転入超過の年数(16年中)"] = {k: int((bk[k] > 0).sum()) for k in BANDS}
bt = banded(wide("東京都"))
M["東京都_年齢帯ごとの転入超過の年数(16年中)"] = {k: int((bt[k] > 0).sum()) for k in BANDS}

# ---- H2：コロナ期の落ち込みの分解（2019→2021）
def decomp(area, y1, base, nat="日本人"):
    w = wide(area, nat=nat)
    b0 = w.loc[base].mean() if isinstance(base, list) else w.loc[base]
    dlt = w.loc[y1] - b0
    bb = pd.Series({k: dlt[v].sum() for k, v in BANDS.items()})
    return dlt["total"], bb, bb / dlt["total"] * 100

dt, bb, sh = decomp("東京都", 2021, 2019)
dec = pd.DataFrame({"変化_人": bb.round(1), "寄与_%": sh.round(2)})
dec.index.name = "band"; dec.to_csv(RES / "decomp_tokyo_2019_2021.csv")
c1524 = sh[["15-19", "20-24"]].sum()
M["H2"] = {"東京都_変化_2019_2021": int(dt), "寄与_15_24_%": r(c1524),
           "寄与_0_14_%": r(sh["0-14"]), "寄与_25_29_%": r(sh["25-29"]), "寄与_30_44_%": r(sh["30-44"]),
           "寄与_45_64_%": r(sh["45-64"]), "寄与_65+_%": r(sh["65+"]),
           "判定": "支持" if c1524 < 50 else "外れ"}

# ---- H3：女性の割合（東京圏、15〜29歳）
wf, wm = wide("東京圏", sex="女"), wide("東京圏", sex="男")
fy = wf[YOUNG].sum(axis=1); my = wm[YOUNG].sum(axis=1)
fs = (fy / (fy + my) * 100)
sexdf = pd.DataFrame({"女_15_29": fy, "男_15_29": my, "女の割合_%": fs.round(2),
                      "女_total": wf["total"], "男_total": wm["total"]})
sexdf.index.name = "year"; sexdf.to_csv(RES / "sex_tokyoken.csv")
M["H3"] = {"女の割合_最小": r(fs.min()), "女の割合_最大": r(fs.max()), "50超の年数": int((fs > 50).sum()),
           "年数": int(len(fs)), "女の割合_2019": r(fs.loc[2019]), "女の割合_2025": r(fs.loc[2025]),
           "女の割合_2010": r(fs.loc[2010]),
           "女_全年齢_2025": int(wf.loc[2025, "total"]), "男_全年齢_2025": int(wm.loc[2025, "total"]),
           "判定": "支持" if (fs > 50).sum() > len(fs) / 2 else "外れ"}
# 年齢ごとの女−男（2025・2019、東京圏）
fm = pd.DataFrame({"女−男_2019": wf.loc[2019, AGES] - wm.loc[2019, AGES],
                   "女−男_2025": wf.loc[2025, AGES] - wm.loc[2025, AGES]})
fm.index.name = "age"; fm.to_csv(RES / "female_minus_male_by_age.csv")
M["H3"]["女−男_20_24_2025"] = int(fm.loc["20-24", "女−男_2025"])
M["H3"]["女−男_25_29_2025"] = int(fm.loc["25-29", "女−男_2025"])
M["H3"]["女−男_年齢別合計_2025"] = int(fm["女−男_2025"].sum())
M["H3"]["女−男_30歳以上_2025"] = int(fm.loc[AGES[6:], "女−男_2025"].sum())

# ---- H4：戻り（東京都、2025 / 2019）
w = wide("東京都")
r2024 = w.loc[2025, "20-24"] / w.loc[2019, "20-24"] * 100
fam = lambda y: w.loc[y, AGES[0:3] + AGES[6:9]].sum()
M["H4"] = {"東京都_20_24_2019": int(w.loc[2019, "20-24"]), "東京都_20_24_2025": int(w.loc[2025, "20-24"]),
           "東京都_20_24_戻り_%": r(r2024),
           "東京都_0_14と30_44_2019": int(fam(2019)), "東京都_0_14と30_44_2021": int(fam(2021)),
           "東京都_0_14と30_44_2025": int(fam(2025)),
           "東京都_total_2019": int(w.loc[2019, "total"]), "東京都_total_2021": int(w.loc[2021, "total"]),
           "東京都_total_2025": int(w.loc[2025, "total"]),
           "東京都_total_戻り_%": r(w.loc[2025, "total"] / w.loc[2019, "total"] * 100),
           "判定": "支持" if (r2024 >= 90 and fam(2025) < fam(2019)) else "外れ"}
M["H4"]["東京都_15_19_戻り_%"] = r(w.loc[2025, "15-19"] / w.loc[2019, "15-19"] * 100)
M["H4"]["東京都_25_29_戻り_%"] = r(w.loc[2025, "25-29"] / w.loc[2019, "25-29"] * 100)
# 年齢の形の似かた（2019年との相関、19区分）
cor = {int(y): r(np.corrcoef(w.loc[y, AGES].astype(float), w.loc[2019, AGES].astype(float))[0, 1], 3)
       for y in w.index}
M["年齢の形_2019との相関_東京都"] = cor

# ---- 頑健性
rob = []
# 1 単位を変える
rob.append(("H1", "東京都で数える", "若い比率 2010〜19年の最小", r(h1.loc[2010:2019, "東京都"].min()),
            "支持" if (h1.loc[2010:2019, "東京都"] >= 100).all() else "外れ"))
dt2, bb2, sh2 = decomp("東京圏", 2021, 2019)
rob.append(("H2", "東京圏で数える", "15〜24歳の寄与 %", r(sh2[["15-19", "20-24"]].sum()),
            "支持" if sh2[["15-19", "20-24"]].sum() < 50 else "外れ"))
wk2 = wide("東京圏"); famk = lambda y: wk2.loc[y, AGES[0:3] + AGES[6:9]].sum()
rk = wk2.loc[2025, "20-24"] / wk2.loc[2019, "20-24"] * 100
rob.append(("H4", "東京圏で数える", "20〜24歳の戻り %", r(rk),
            "支持" if (rk >= 90 and famk(2025) < famk(2019)) else "外れ"))
# 2 基準を2017〜2019年の平均
dt3, bb3, sh3 = decomp("東京都", 2021, [2017, 2018, 2019])
rob.append(("H2", "基準を2017〜19年の平均", "15〜24歳の寄与 %", r(sh3[["15-19", "20-24"]].sum()),
            "支持" if sh3[["15-19", "20-24"]].sum() < 50 else "外れ"))
b3 = w.loc[[2017, 2018, 2019]].mean()
r3 = w.loc[2025, "20-24"] / b3["20-24"] * 100
f3 = b3[AGES[0:3] + AGES[6:9]].sum()
rob.append(("H4", "基準を2017〜19年の平均", "20〜24歳の戻り %", r(r3),
            "支持" if (r3 >= 90 and fam(2025) < f3) else "外れ"))
# 3 外国人を含む（2014年以降）
ya = young_share("東京圏", nat="外国人を含む", years=range(2014, 2020))
rob.append(("H1", "外国人を含む（2014〜19年）", "若い比率の最小", r(ya.min()), "支持" if (ya >= 100).all() else "外れ"))
dt4, bb4, sh4 = decomp("東京都", 2021, 2019, nat="外国人を含む")
rob.append(("H2", "外国人を含む", "15〜24歳の寄与 %", r(sh4[["15-19", "20-24"]].sum()),
            "支持" if sh4[["15-19", "20-24"]].sum() < 50 else "外れ"))
wa = wide("東京都", nat="外国人を含む")
ra = wa.loc[2025, "20-24"] / wa.loc[2019, "20-24"] * 100
fa = lambda y: wa.loc[y, AGES[0:3] + AGES[6:9]].sum()
rob.append(("H4", "外国人を含む", "20〜24歳の戻り %", r(ra), "支持" if (ra >= 90 and fa(2025) < fa(2019)) else "外れ"))
# 4 若い年齢の区切り
for lab, yg in [("15〜24歳", ["15-19", "20-24"]), ("20〜29歳", ["20-24", "25-29"])]:
    s = young_share("東京圏", young=yg).loc[2010:2019]
    rob.append(("H1", f"若い年齢を{lab}に", "若い比率の最小", r(s.min()), "支持" if (s >= 100).all() else "外れ"))
    fy2 = wf[yg].sum(axis=1); my2 = wm[yg].sum(axis=1); fs2 = fy2 / (fy2 + my2) * 100
    rob.append(("H3", f"若い年齢を{lab}に", "女の割合50%超の年数（16年中）", int((fs2 > 50).sum()),
                "支持" if (fs2 > 50).sum() > 8 else "外れ"))
# 5 2011年を除く
s5 = h1.loc[[y for y in range(2010, 2020) if y != 2011], "東京圏"]
rob.append(("H1", "2011年を除く", "若い比率の最小", r(s5.min()), "支持" if (s5 >= 100).all() else "外れ"))
fs5 = fs.drop(2011)
rob.append(("H3", "2011年を除く", "女の割合50%超の年数（15年中）", int((fs5 > 50).sum()),
            "支持" if (fs5 > 50).sum() > len(fs5) / 2 else "外れ"))
R = pd.DataFrame(rob, columns=["仮説", "変えたこと", "指標", "値", "判定"])
R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {f"{a}|{b}": {"指標": c, "値": v, "判定": j} for a, b, c, v, j in rob}

# ---- 問い直し：東京都から出た子育て年齢は、東京圏の中（3県）にとどまったのか
k3 = {}
rows = []
for y in range(2010, 2026):
    for band in ["0-14", "30-44"]:
        t = bt.loc[y, band]; k = bk.loc[y, band]
        rows.append((y, band, int(t), int(k - t), int(k)))
Q = pd.DataFrame(rows, columns=["year", "band", "東京都", "3県（東京圏−東京都）", "東京圏"])
Q.to_csv(RES / "requestion_within_tokyoken.csv", index=False)
qq = Q.groupby("year", sort=True)[["東京都", "3県（東京圏−東京都）", "東京圏"]].sum()
M["問い直し"] = {
    "0_14と30_44": {str(y): {"東京都": int(qq.loc[y, "東京都"]), "3県": int(qq.loc[y, "3県（東京圏−東京都）"]),
                             "東京圏": int(qq.loc[y, "東京圏"])} for y in [2010, 2015, 2019, 2020, 2021, 2022, 2025]},
    "東京圏が正の年数(16年中)": int((qq["東京圏"] > 0).sum()),
    "東京都が負の年数(16年中)": int((qq["東京都"] < 0).sum()),
}
# 2019→2021 の東京都の子育て年齢の減少のうち、3県の増加で埋まった割合
dT = qq.loc[2021, "東京都"] - qq.loc[2019, "東京都"]; d3 = qq.loc[2021, "3県（東京圏−東京都）"] - qq.loc[2019, "3県（東京圏−東京都）"]
M["問い直し"]["2019_2021_東京都の変化"] = int(dT)
M["問い直し"]["2019_2021_3県の変化"] = int(d3)
M["問い直し"]["3県で埋まった割合_%"] = r(-d3 / dT * 100)

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1, sort_keys=False)
print(json.dumps(M, ensure_ascii=False, indent=1))
