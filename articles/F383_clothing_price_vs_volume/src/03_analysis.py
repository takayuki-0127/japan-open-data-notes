"""03 分析（オフライン）：被服及び履物の名目支出を、消費者物価指数で価格の分と実質（量）の分に分ける。
費目別・世帯主の年齢別・長い期間。結果：results/main.json と CSV"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
nom = pd.read_csv(DATA / "nominal_items_2000_2025.csv").set_index("year")
old = pd.read_csv(DATA / "nominal_items_1963_2007.csv").set_index("year")
cpi = pd.read_csv(DATA / "cpi_clothing.csv").set_index("year")
age = pd.read_csv(DATA / "age_items.csv")
org = pd.read_csv(DATA / "official_real_growth.csv").set_index("year")
MAP = {"被服及び履物": "被服及び履物", "和服": "和服", "洋服": "洋服", "シャツ・セーター類": "シャツ・セーター類", "下着類": "下着類",
       "生地・糸類": "衣料", "他の被服": "他の被服", "履物類": "履物類", "被服関連サービス": "被服関連サービス"}
MID = [k for k in MAP if k != "被服及び履物"]
R = lambda v, k=1: round(float(v), k)


def decomp(n0, n1, p0, p1):
    ln_n, ln_p = np.log(n1 / n0), np.log(p1 / p0)
    return {"nominal_pct": (n1 / n0 - 1) * 100, "price_pct": (p1 / p0 - 1) * 100, "real_pct": (np.exp(ln_n - ln_p) - 1) * 100,
            "price_share_pct": ln_p / ln_n * 100 if ln_n != 0 else np.nan}


# A 全国・費目別（2000→2025年）
real = pd.DataFrame({k: nom[k] / (cpi.loc[nom.index, MAP[k]] / 100) for k in MAP})
real.round(1).to_csv(RES / "real_items_2000_2025.csv")
items = []
for k in MAP:
    d = decomp(nom.loc[2000, k], nom.loc[2025, k], cpi.loc[2000, MAP[k]], cpi.loc[2025, MAP[k]])
    items.append(dict(item=k, cpi_series=MAP[k], nominal_2000=nom.loc[2000, k], nominal_2025=nom.loc[2025, k],
                      cpi_2000=cpi.loc[2000, MAP[k]], cpi_2025=cpi.loc[2025, MAP[k]], **d))
items = pd.DataFrame(items)
items.round(2).to_csv(RES / "items_decomposition.csv", index=False)
T = items.set_index("item")
tot = T.loc["被服及び履物"]
# 名目の減少への費目ごとの寄与（円）
contrib = {k: R(nom.loc[2025, k] - nom.loc[2000, k], 0) for k in MID}
# 消費支出に占める割合
share = (nom["被服及び履物"] / nom["消費支出"] * 100)
# 価格の推移の節目
c = cpi["被服及び履物"]
cpi_min_year = int(c.loc[2000:].idxmin())

# 年ごとの表（図1）
yr = pd.DataFrame({"nominal": nom["被服及び履物"], "cpi": cpi.loc[nom.index, "被服及び履物"], "cpi_all": cpi.loc[nom.index, "総合"],
                   "real_2025yen": real["被服及び履物"], "share_of_consumption_pct": share})
yr["nominal_idx2000"] = yr.nominal / yr.nominal.iloc[0] * 100
yr["cpi_idx2000"] = yr.cpi / yr.cpi.iloc[0] * 100
yr["real_idx2000"] = yr.real_2025yen / yr.real_2025yen.iloc[0] * 100
yr.round(2).to_csv(RES / "annual_national.csv")

# B 長い期間（1970〜2025年）：20-3-a（非農林漁家）を2000〜2007年の重なりの比でつなぐ
ov = range(2000, 2008)
link = float((nom.loc[ov, "被服及び履物"] / old.loc[ov, "被服及び履物"]).mean())
link_sd = float((nom.loc[ov, "被服及び履物"] / old.loc[ov, "被服及び履物"]).std(ddof=0))
lng = pd.concat([old.loc[1970:1999, "被服及び履物"] * link, nom["被服及び履物"]])
lng_unl = pd.concat([old.loc[1970:1999, "被服及び履物"], nom["被服及び履物"]])
L = pd.DataFrame({"nominal_linked": lng, "nominal_unlinked": lng_unl, "cpi": cpi.loc[1970:2025, "被服及び履物"], "cpi_all": cpi.loc[1970:2025, "総合"]})
L["real_2025yen"] = L.nominal_linked / (L.cpi / 100)
L["hh_size"] = pd.concat([old.loc[1970:1999, "世帯人員"], nom["世帯人員"]])
L.index.name = "year"
L.round(2).to_csv(RES / "long_1970_2025.csv")
nom_peak = int(L.nominal_linked.idxmax()); real_peak = int(L.real_2025yen.idxmax()); cpi_peak = int(L.cpi.idxmax())
long_dec = {"1970_2025": decomp(L.nominal_linked[1970], L.nominal_linked[2025], L.cpi[1970], L.cpi[2025]),
            f"{nom_peak}_2025": decomp(L.nominal_linked[nom_peak], L.nominal_linked[2025], L.cpi[nom_peak], L.cpi[2025]),
            "1970_1991": decomp(L.nominal_linked[1970], L.nominal_linked[1991], L.cpi[1970], L.cpi[1991])}

# C 年齢別（2002→2025年）
a = age[age.code == "5"].pivot(index="year", columns="group", values="amount")
w = age[age.code == "hh_weight"].pivot(index="year", columns="group", values="amount")
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
ar = a[AG].div(cpi.loc[a.index, "被服及び履物"] / 100, axis=0)
age_tab = []
for g in AG:
    d = decomp(a.loc[2002, g], a.loc[2025, g], cpi.loc[2002, "被服及び履物"], cpi.loc[2025, "被服及び履物"])
    age_tab.append(dict(age=g, nominal_2002=a.loc[2002, g], nominal_2025=a.loc[2025, g], weight_2002=w.loc[2002, g], weight_2025=w.loc[2025, g], **d))
age_tab = pd.DataFrame(age_tab)
age_tab.round(2).to_csv(RES / "age_decomposition.csv", index=False)
ar.round(1).to_csv(RES / "age_real_annual.csv")


def shift_share(y0, y1, x=ar):
    w0, w1 = w.loc[y0, AG] / w.loc[y0, AG].sum(), w.loc[y1, AG] / w.loc[y1, AG].sum()
    m0, m1 = (w0 * x.loc[y0, AG]).sum(), (w1 * x.loc[y1, AG]).sum()
    comp = ((w1 - w0) * x.loc[y0, AG]).sum()
    within = (w1 * (x.loc[y1, AG] - x.loc[y0, AG])).sum()
    return {"mean0": m0, "mean1": m1, "total": m1 - m0, "composition": comp, "within": within,
            "composition_share_pct": comp / (m1 - m0) * 100}


ss = shift_share(2002, 2025)
age70_share = {y: float(w.loc[y, "70歳以上"] / w.loc[y, AG].sum() * 100) for y in (2002, 2025)}

# D 頑健性
rob = []
def add(label, n0, n1, p0, p1, note=""):
    d = decomp(n0, n1, p0, p1)
    rob.append(dict(確かめ=label, 名目の変化=R(d["nominal_pct"]), 価格の変化=R(d["price_pct"]), 実質の変化=R(d["real_pct"]),
                    価格の分の割合=R(d["price_share_pct"]), 備考=note))
N, C = nom["被服及び履物"], cpi["被服及び履物"]
add("0 主：2000→2025年", N[2000], N[2025], C[2000], C[2025])
add("1a 始まりを2005年に", N[2005], N[2025], C[2005], C[2025])
add("1b 始まりを2010年に", N[2010], N[2025], C[2010], C[2025])
add("1c 終わりを2019年に（感染症の前）", N[2000], N[2019], C[2000], C[2019])
pc = N / nom["世帯人員"]
add("2 1人あたり（世帯人員で割る）", pc[2000], pc[2025], C[2000], C[2025], f"世帯人員 {nom.loc[2000, '世帯人員']}→{nom.loc[2025, '世帯人員']}")
rsum = sum(real[k] for k in MID)   # 費目ごとに割ってから足す
p_impl = N / rsum                   # 暗黙の価格
add("3 費目ごとに物価指数で割ってから足す", N[2000], N[2025], p_impl[2000], p_impl[2025])
off = np.prod([1 + org.loc[y, "被服及び履物_実質増減率"] / 100 for y in range(2001, 2026)])
mine = real.loc[2025, "被服及び履物"] / real.loc[2000, "被服及び履物"]
rob.append(dict(確かめ="4 公表の実質増減率をつないだもの（照合）", 名目の変化=R(tot.nominal_pct), 価格の変化=np.nan, 実質の変化=R((off - 1) * 100),
                価格の分の割合=np.nan, 備考=f"自分で割った実質 {R((mine - 1) * 100)}%"))
d70 = long_dec["1970_2025"]
rob.append(dict(確かめ="5 長い期間 1970→2025年（つないだ系列）", 名目の変化=R(d70["nominal_pct"]), 価格の変化=R(d70["price_pct"]), 実質の変化=R(d70["real_pct"]),
                価格の分の割合=np.nan, 備考=f"つなぎの比 {link:.4f}（2000〜07年の平均、標準偏差 {link_sd:.4f}）"))
rb = pd.DataFrame(rob)
rb.to_csv(RES / "robustness.csv", index=False)

# 問い直し：男性用・女性用・子供用の洋服（洋服の物価指数で割る）
G = ["男性用洋服", "女性用洋服", "子供用洋服"]
req = []
for g in G:
    d = decomp(nom.loc[2000, g], nom.loc[2025, g], cpi.loc[2000, "洋服"], cpi.loc[2025, "洋服"])
    d19 = decomp(nom.loc[2019, g], nom.loc[2025, g], cpi.loc[2019, "洋服"], cpi.loc[2025, "洋服"])
    req.append(dict(item=g, nominal_2000=nom.loc[2000, g], nominal_2019=nom.loc[2019, g], nominal_2025=nom.loc[2025, g],
                    real_pct_2000_2025=d["real_pct"], nominal_pct_2000_2025=d["nominal_pct"], nominal_pct_2019_2025=d19["nominal_pct"],
                    real_pct_2019_2025=d19["real_pct"]))
req = pd.DataFrame(req)
req.round(2).to_csv(RES / "requestion_mens_womens.csv", index=False)
# 男性用÷女性用の比
mw = (nom["男性用洋服"] / nom["女性用洋服"])

H1 = tot.price_pct >= 0
H2 = tot.price_share_pct < 50 if tot.nominal_pct < 0 else False
H3 = T.loc["洋服", "real_pct"] < T.loc["下着類", "real_pct"]
H4a = bool((age_tab.real_pct < 0).all())
H4b = abs(ss["within"]) > abs(ss["composition"])
main = {
    "national_2000_2025": {k: R(v) for k, v in tot[["nominal_2000", "nominal_2025", "cpi_2000", "cpi_2025", "nominal_pct", "price_pct", "real_pct", "price_share_pct"]].items()},
    "cpi_all_2000_2025_pct": R((cpi.loc[2025, "総合"] / cpi.loc[2000, "総合"] - 1) * 100),
    "cpi_clothing_min_year_2000_2025": cpi_min_year, "cpi_clothing_min_value": R(c[cpi_min_year]),
    "cpi_clothing_2000_to_min_pct": R((c[cpi_min_year] / c[2000] - 1) * 100), "cpi_clothing_min_to_2025_pct": R((c[2025] / c[cpi_min_year] - 1) * 100),
    "share_of_consumption_pct": {"2000": R(share[2000], 2), "2025": R(share[2025], 2)},
    "items": {k: {kk: R(T.loc[k, kk]) for kk in ["nominal_2000", "nominal_2025", "nominal_pct", "price_pct", "real_pct"]} for k in MAP},
    "item_contrib_yen": contrib,
    "covid": {"nominal_2019": R(N[2019], 0), "nominal_2020": R(N[2020], 0), "drop_2019_2020_pct": R((N[2020] / N[2019] - 1) * 100),
              "nominal_2025_vs_2019_pct": R((N[2025] / N[2019] - 1) * 100), "real_2025_vs_2019_pct": R((real.loc[2025, "被服及び履物"] / real.loc[2019, "被服及び履物"] - 1) * 100)},
    "long": {"link_ratio": round(link, 4), "nominal_peak_year": nom_peak, "nominal_peak_yen": R(L.nominal_linked[nom_peak], 0),
             "real_peak_year": real_peak, "cpi_peak_year": cpi_peak,
             "decomp": {k: {kk: R(vv) for kk, vv in v.items()} for k, v in long_dec.items()},
             "nominal_1970": R(L.nominal_linked[1970], 0)},
    "age": {r.age: {"nominal_2002": R(r.nominal_2002, 0), "nominal_2025": R(r.nominal_2025, 0), "nominal_pct": R(r.nominal_pct), "real_pct": R(r.real_pct)} for r in age_tab.itertuples()},
    "age_shift_share_real_2025yen": {k: R(v) for k, v in ss.items()},
    "age70_weight_share_pct": {str(k): R(v) for k, v in age70_share.items()},
    "requestion": {r.item: {"real_pct_2000_2025": R(r.real_pct_2000_2025), "nominal_pct_2000_2025": R(r.nominal_pct_2000_2025),
                            "nominal_pct_2019_2025": R(r.nominal_pct_2019_2025), "real_pct_2019_2025": R(r.real_pct_2019_2025),
                            "nominal_2000": R(r.nominal_2000, 0), "nominal_2025": R(r.nominal_2025, 0)} for r in req.itertuples()},
    "mens_to_womens_ratio": {"2000": R(mw[2000], 3), "2019": R(mw[2019], 3), "2025": R(mw[2025], 3)},
    "robustness": {r["確かめ"]: {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items() if k != "確かめ"} for r in rob},
    "hypotheses": {"H1": "支持" if H1 else "外れ", "H2": "支持" if H2 else "外れ", "H3": "支持" if H3 else "外れ",
                   "H4": "支持" if (H4a and H4b) else ("一部支持" if (H4a or H4b) else "外れ")},
}
(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(main, ensure_ascii=False, indent=1))
