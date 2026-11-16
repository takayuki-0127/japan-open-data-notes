"""03 分析：地方圏の若い年齢の転出超過の男女差、年齢、率、推移、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49",
        "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", "90+"]
METRO = [8 + 3, 12, 13, 14, 21, 23, 24, 26, 27, 28, 29]  # 東京圏・名古屋圏・大阪圏
CHIHO = [p for p in range(1, 48) if p not in METRO]       # 36道県
NOT_TK = [p for p in range(1, 48) if p not in (11, 12, 13, 14)]
YOUNG = ["15-19", "20-24", "25-29"]
PREF = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
        "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
        "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
        "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
assert len(CHIHO) == 36

m = pd.read_csv(ROOT / "data" / "netmig_pref_sex_age.csv")
P = pd.read_csv(ROOT / "data" / "pop_pref_sex_age.csv")
def r(x, n=1): return float(round(float(x), n))

def out_by(prefs, nat="日本人"):
    """地域の転出超過（＝−転入超過）、年×性×年齢"""
    q = m[(m.pref.isin(prefs)) & (m.nat == nat)]
    g = q.groupby(["year", "sex", "age"], sort=True).net.sum().mul(-1)
    return g.unstack("age")

O = out_by(CHIHO)
F, Mm = O.xs("女", level="sex"), O.xs("男", level="sex")
M = {}
# ---- 表：地方圏 男女×年齢帯
bands = {"15-19": ["15-19"], "20-24": ["20-24"], "25-29": ["25-29"], "30-34": ["30-34"], "35-44": ["35-39", "40-44"],
         "15-29": YOUNG, "全年齢": ["total"]}
tab = pd.DataFrame({f"{s}_{b}": X[v].sum(axis=1) for b, v in bands.items() for s, X in [("女", F), ("男", Mm)]})
for b in bands:
    tab[f"女−男_{b}"] = tab[f"女_{b}"] - tab[f"男_{b}"]
tab["女の割合_15_29_%"] = (tab["女_15-29"] / (tab["女_15-29"] + tab["男_15-29"]) * 100).round(2)
tab.index.name = "year"; tab.to_csv(RES / "chiho_sex_bands.csv")

# ---- H1
d1529 = tab["女−男_15-29"]
M["H1"] = {"女＞男の年数": int((d1529 > 0).sum()), "年数": 16,
           "女_15_29_2025": int(tab.loc[2025, "女_15-29"]), "男_15_29_2025": int(tab.loc[2025, "男_15-29"]),
           "女−男_15_29_2025": int(d1529.loc[2025]), "女の割合_2025": r(tab.loc[2025, "女の割合_15_29_%"]),
           "女の割合_最小": r(tab["女の割合_15_29_%"].min()), "女の割合_最大": r(tab["女の割合_15_29_%"].max()),
           "女_15_29_2010": int(tab.loc[2010, "女_15-29"]), "男_15_29_2010": int(tab.loc[2010, "男_15-29"]),
           "判定": "支持" if (d1529 > 0).sum() >= 9 else "外れ"}
# ---- H2
d2024 = tab["女−男_20-24"]; d1519 = tab["女−男_15-19"]; d2529 = tab["女−男_25-29"]
M["H2"] = {"20_24_女＞男の年数": int((d2024 > 0).sum()), "15_19_女≦男の年数": int((d1519 <= 0).sum()),
           "25_29_女＞男の年数": int((d2529 > 0).sum()),
           "女−男_15_19_2025": int(d1519.loc[2025]), "女−男_20_24_2025": int(d2024.loc[2025]),
           "女−男_25_29_2025": int(d2529.loc[2025]),
           "女−男_20_24_平均_2010_2025": r(d2024.mean(), 0), "女−男_15_19_平均_2010_2025": r(d1519.mean(), 0),
           "女−男_25_29_平均_2010_2025": r(d2529.mean(), 0),
           "判定": "支持" if ((d2024 > 0).all() and (d1519 <= 0).sum() >= 9) else "外れ"}

# ---- H3 率（県別、20〜24歳）
def rates(prefs, years, pop_year, age="20-24"):
    q = m[(m.nat == "日本人") & (m.age == age) & (m.year.isin(years)) & (m.pref.isin(prefs)) & (m.sex.isin(["男", "女"]))]
    o = q.groupby(["pref", "sex"], sort=True).net.mean().mul(-1)
    pp = P[(P.year == pop_year) & (P.age == age)].set_index(["pref", "sex"]).pop_thousand * 1000
    rt = (o / pp.reindex(o.index) * 100).unstack("sex")
    cnt = o.unstack("sex")
    return rt, cnt, pp.unstack("sex").loc[prefs]

rt, cnt, pp = rates(CHIHO, [2024, 2025], 2024)
pr = pd.DataFrame({"県": [PREF[p - 1] for p in rt.index], "女_率_%": rt["女"].round(3), "男_率_%": rt["男"].round(3),
                   "女_人数": cnt["女"].round(1), "男_人数": cnt["男"].round(1)}, index=rt.index)
pr["女−男_率_pt"] = (pr["女_率_%"] - pr["男_率_%"]).round(3)
pr.index.name = "pref_code"; pr.to_csv(RES / "pref_rates_20_24_2024_2025.csv")
w_f = cnt["女"].sum() / pp["女"].sum() * 100; w_m = cnt["男"].sum() / pp["男"].sum() * 100
nF = int((rt["女"] > rt["男"]).sum())
M["H3"] = {"女の率＞男の率の県数": nF, "県数": 36, "地方圏全体_女_率_%": r(w_f, 2), "地方圏全体_男_率_%": r(w_m, 2),
           "県の女の率_中央値_%": r(rt["女"].median(), 2), "県の男の率_中央値_%": r(rt["男"].median(), 2),
           "判定": "支持" if nF >= 19 else "外れ"}

# ---- H4 推移
early = d1529.loc[2010:2012].mean(); late = d1529.loc[2023:2025].mean()
M["H4"] = {"女−男_15_29_2010_2012平均": r(early, 0), "女−男_15_29_2023_2025平均": r(late, 0),
           "女−男_15_29_最大年": int(d1529.idxmax()), "女−男_15_29_最大": int(d1529.max()),
           "判定": "支持" if late > early else "外れ"}
M["推移_女−男_15_29"] = {int(y): int(v) for y, v in d1529.items()}

# ---- 頑健性
rob = []
for lab, cols in [("15〜34歳に広げる", YOUNG + ["30-34"]), ("全年齢", ["total"])]:
    dd = F[cols].sum(axis=1) - Mm[cols].sum(axis=1)
    rob.append(("H1", lab, "女＞男の年数（16年中）", int((dd > 0).sum()), "支持" if (dd > 0).sum() >= 9 else "外れ"))
Oa = out_by(CHIHO, nat="外国人を含む")
Fa, Ma = Oa.xs("女", level="sex"), Oa.xs("男", level="sex")
dda = Fa[YOUNG].sum(axis=1) - Ma[YOUNG].sum(axis=1)
rob.append(("H1", "外国人を含む（2014〜25年）", "女＞男の年数（12年中）", int((dda > 0).sum()), "支持" if (dda > 0).sum() > 6 else "外れ"))
d2a = Fa["20-24"] - Ma["20-24"]; d1a = Fa["15-19"] - Ma["15-19"]
rob.append(("H2", "外国人を含む（2014〜25年）", "20〜24歳 女＞男／15〜19歳 女≦男 の年数（12年中）",
            f"{int((d2a > 0).sum())}／{int((d1a <= 0).sum())}", "支持" if ((d2a > 0).all() and (d1a <= 0).sum() > 6) else "外れ"))
Ot = out_by(NOT_TK)
Ft, Mt = Ot.xs("女", level="sex"), Ot.xs("男", level="sex")
ddt = Ft[YOUNG].sum(axis=1) - Mt[YOUNG].sum(axis=1)
rob.append(("H1", "東京圏以外の43道府県", "女＞男の年数（16年中）", int((ddt > 0).sum()), "支持" if (ddt > 0).sum() >= 9 else "外れ"))
d2t = Ft["20-24"] - Mt["20-24"]; d1t = Ft["15-19"] - Mt["15-19"]
rob.append(("H2", "東京圏以外の43道府県", "20〜24歳 女＞男／15〜19歳 女≦男 の年数（16年中）",
            f"{int((d2t > 0).sum())}／{int((d1t <= 0).sum())}", "支持" if ((d2t > 0).all() and (d1t <= 0).sum() >= 9) else "外れ"))
rt19, cnt19, pp19 = rates(CHIHO, [2018, 2019], 2019)
n19 = int((rt19["女"] > rt19["男"]).sum())
rob.append(("H3", "2018・2019年と2019年人口（コロナ前）", "女の率＞男の率の県数（36中）", n19, "支持" if n19 >= 19 else "外れ"))
rob.append(("H3", "地方圏全体の率で比べる", "女の率／男の率 %", f"{r(w_f,2)}／{r(w_m,2)}", "支持" if w_f > w_m else "外れ"))
rt15, _, _ = rates(CHIHO, [2024, 2025], 2024, age="15-19")
n15 = int((rt15["女"] > rt15["男"]).sum())
rob.append(("H3", "15〜19歳で同じ計算", "女の率＞男の率の県数（36中）", n15, "（参考）"))
e2 = (dda.loc[2014:2016].mean(), dda.loc[2023:2025].mean())
rob.append(("H4", "外国人を含む、2014〜16年と2023〜25年", "女−男の平均", f"{r(e2[0],0)}→{r(e2[1],0)}", "支持" if e2[1] > e2[0] else "外れ"))
early_t, late_t = ddt.loc[2010:2012].mean(), ddt.loc[2023:2025].mean()
rob.append(("H4", "東京圏以外の43道府県", "女−男の平均 2010〜12→2023〜25", f"{r(early_t,0)}→{r(late_t,0)}", ("支持" if late_t > early_t else "外れ") if late_t > 0 else "判定できず（どちらの期間も男性が多い）"))
R = pd.DataFrame(rob, columns=["仮説", "変えたこと", "指標", "値", "判定"])
R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {f"{a}|{b}": {"指標": c, "値": v, "判定": j} for a, b, c, v, j in rob}
M["率_2019_女_地方圏全体_%"] = r(cnt19["女"].sum() / pp19["女"].sum() * 100, 2)
M["率_2019_男_地方圏全体_%"] = r(cnt19["男"].sum() / pp19["男"].sum() * 100, 2)

# ---- 問い直し：30〜44歳で戻ってくる（転入超過）のは男女どちらか
d3034 = tab["女−男_30-34"]; d3544 = tab["女−男_35-44"]
back = pd.DataFrame({"女_30_44": tab["女_30-34"] + tab["女_35-44"], "男_30_44": tab["男_30-34"] + tab["男_35-44"]})
back.index.name = "year"; back.to_csv(RES / "requestion_30_44.csv")
M["問い直し"] = {
    "女_30_44_2019": int(back.loc[2019, "女_30_44"]), "男_30_44_2019": int(back.loc[2019, "男_30_44"]),
    "女_30_44_2025": int(back.loc[2025, "女_30_44"]), "男_30_44_2025": int(back.loc[2025, "男_30_44"]),
    "女_30_44_平均": r(back["女_30_44"].mean(), 0), "男_30_44_平均": r(back["男_30_44"].mean(), 0),
    "男が戻る側（転出超過＜0）の年数": int((back["男_30_44"] < 0).sum()),
    "女が戻る側（転出超過＜0）の年数": int((back["女_30_44"] < 0).sum()),
    "全年齢_女_2025": int(tab.loc[2025, "女_全年齢"]), "全年齢_男_2025": int(tab.loc[2025, "男_全年齢"]),
}
# 15〜44歳を通した差し引き（2010〜2025年の合計）
cum = {s: int(X[YOUNG + ["30-34", "35-39", "40-44"]].sum().sum()) for s, X in [("女", F), ("男", Mm)]}
M["問い直し"]["15_44_16年合計_女"] = cum["女"]; M["問い直し"]["15_44_16年合計_男"] = cum["男"]
M["問い直し"]["15_29_16年合計_女"] = int(F[YOUNG].sum().sum()); M["問い直し"]["15_29_16年合計_男"] = int(Mm[YOUNG].sum().sum())

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps(M, ensure_ascii=False, indent=1))
