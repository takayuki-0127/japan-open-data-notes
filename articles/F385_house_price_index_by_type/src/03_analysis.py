"""03 分析：種類別・地域別の伸び、底の月、実質、取引件数、頑健性、問い直し → results/（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
AREAS = ["全国", "北海道地方", "東北地方", "関東地方", "北陸地方", "中部地方", "近畿地方", "中国地方", "四国地方",
         "九州・沖縄地方", "南関東圏", "名古屋圏", "京阪神圏", "東京都", "愛知県", "大阪府"]
TYPES = ["住宅総合", "住宅地", "戸建住宅", "マンション"]

idx = pd.read_csv(DATA / "rppi_monthly.csv")
idx = idx[idx.month >= "2008-04"].copy()
idx["year"] = idx.month.str[:4].astype(int)
cpi = pd.read_csv(DATA / "cpi_monthly.csv").set_index("month")["cpi"]
cpi2010 = cpi[[m for m in cpi.index if m.startswith("2010")]].mean()
idx["real"] = idx["index"] / idx.month.map(cpi).values * cpi2010
tx = pd.read_csv(DATA / "transactions_monthly.csv")
tx["year"] = tx.month.str[:4].astype(int)


def annual(series="sa", col="index"):
    d = idx[idx.series == series]
    return d.groupby(["area", "type", "year"], sort=False)[col].mean()


def growth(a, y0, y1):
    """a: annual Series (area,type,year) → DataFrame area x type の伸び（%）。"""
    out = {}
    for ar in AREAS:
        out[ar] = {t: 100 * (a[(ar, t, y1)] / a[(ar, t, y0)] - 1) for t in TYPES}
    return pd.DataFrame(out).T.loc[AREAS, TYPES]


def trough_month(series="sa"):
    d = idx[idx.series == series]
    out = {}
    for ar in AREAS:
        out[ar] = {}
        for t in ["戸建住宅", "マンション", "住宅地"]:
            s = d[(d.area == ar) & (d.type == t)].set_index("month")["index"].sort_index()
            ma = s.rolling(12, center=True).mean()
            ma = ma[ma.index >= "2009-01"].dropna()
            out[ar][t] = ma.idxmin()
    return pd.DataFrame(out).T.loc[AREAS]


def trough_year(series="sa"):
    a = annual(series)
    out = {}
    for ar in AREAS:
        out[ar] = {t: int(a.loc[(ar, t)].loc[2009:2025].idxmin()) for t in ["戸建住宅", "マンション", "住宅地"]}
    return pd.DataFrame(out).T.loc[AREAS]


def years_between(m1, m2):
    y1, mo1 = map(int, m1.split("-")); y2, mo2 = map(int, m2.split("-"))
    return ((y2 - y1) * 12 + (mo2 - mo1)) / 12


def judge(g, tr, label):
    det = g["戸建住宅"]
    h1 = g.loc["全国", "マンション"] / g.loc["全国", "戸建住宅"]
    h2 = int((det >= 10).sum())
    h3 = int((g["マンション"] > g["戸建住宅"]).sum())
    if isinstance(tr.iloc[0, 0], str):
        lead = [years_between(tr.loc[a, "マンション"], tr.loc[a, "戸建住宅"]) for a in AREAS]
    else:
        lead = [float(tr.loc[a, "戸建住宅"] - tr.loc[a, "マンション"]) for a in AREAS]
    h4 = int(sum(1 for x in lead if x >= 3))
    return {"設定": label, "全国_マンション伸び": round(g.loc["全国", "マンション"], 1),
            "全国_戸建伸び": round(g.loc["全国", "戸建住宅"], 1), "H1_倍率": round(h1, 2),
            "H2_戸建+10%以上の地域数": h2, "H3_マンション>戸建の地域数": h3, "H4_3年以上早い地域数": h4,
            "戸建の伸び_最小": round(det.min(), 1), "戸建の伸び_最大": round(det.max(), 1)}


main = {}
a_sa = annual("sa")
g = growth(a_sa, 2013, 2025)
tr = trough_month("sa")
g_real = growth(annual("sa", "real"), 2013, 2025)
out = g.round(2).add_suffix("_名目").join(g_real.round(2).add_suffix("_実質")).join(tr.add_prefix("底の月_"))
lead = pd.Series({a: round(years_between(tr.loc[a, "マンション"], tr.loc[a, "戸建住宅"]), 2) for a in AREAS})
out["マンションの底が早い年数"] = lead
out.index.name = "area"
out.to_csv(RES / "growth_by_area.csv")

# 年平均の表（図1・図2用）
yr = a_sa.unstack("year").loc[:, 2009:2025].round(3)
yr = yr.reset_index()
yr["area"] = pd.Categorical(yr["area"], AREAS, ordered=True)
yr = yr.sort_values(["area", "type"])
yr.to_csv(RES / "annual_index_sa.csv", index=False)

J = judge(g, tr, "主（季節調整・2013→2025年・名目）")
main["main"] = J
main["national"] = {t: {"2013": round(a_sa[("全国", t, 2013)], 2), "2025": round(a_sa[("全国", t, 2025)], 2),
                        "伸び%": round(g.loc["全国", t], 1), "実質伸び%": round(g_real.loc["全国", t], 1)} for t in TYPES}
main["cpi_2013_2025_%"] = round(100 * (cpi[[m for m in cpi.index if m.startswith("2025")]].mean() /
                                       cpi[[m for m in cpi.index if m.startswith("2013")]].mean() - 1), 2)
main["detached_growth_range"] = [round(g["戸建住宅"].min(), 1), round(g["戸建住宅"].max(), 1)]
main["condo_growth_range"] = [round(g["マンション"].min(), 1), round(g["マンション"].max(), 1)]
main["detached_ge10_areas"] = [a for a in AREAS if g.loc[a, "戸建住宅"] >= 10]
main["detached_lt10_areas"] = [a for a in AREAS if g.loc[a, "戸建住宅"] < 10]
main["real_detached_ge0"] = int((g_real["戸建住宅"] >= 0).sum())
main["real_detached_ge10"] = int((g_real["戸建住宅"] >= 10).sum())
main["real_detached_range"] = [round(g_real["戸建住宅"].min(), 1), round(g_real["戸建住宅"].max(), 1)]
main["trough"] = {a: {"マンション": tr.loc[a, "マンション"], "戸建住宅": tr.loc[a, "戸建住宅"], "差の年数": float(lead[a])} for a in AREAS}
main["lead_median_years"] = round(float(lead.median()), 2)

# 2019→2025（コロナ以降）の伸び
g19 = growth(a_sa, 2019, 2025)
main["since2019"] = {a: {"戸建住宅": round(g19.loc[a, "戸建住宅"], 1), "マンション": round(g19.loc[a, "マンション"], 1)} for a in AREAS}
main["share_of_detached_growth_after2019_national"] = round(
    100 * (a_sa[("全国", "戸建住宅", 2025)] - a_sa[("全国", "戸建住宅", 2019)]) /
    (a_sa[("全国", "戸建住宅", 2025)] - a_sa[("全国", "戸建住宅", 2013)]), 1)

# 取引件数（年計）
txa = tx[(tx.year >= 2009) & (tx.year <= 2025)].groupby(["area", "type", "year"], sort=False)["count"].sum()
txg = pd.DataFrame({a: {t: round(100 * (txa[(a, t, 2025)] / txa[(a, t, 2013)] - 1), 2) for t in ["戸建住宅", "マンション"]}
                    for a in AREAS}).T.loc[AREAS]
txg.index.name = "area"
txg.columns = ["件数の伸び_戸建住宅", "件数の伸び_マンション"]
txg.to_csv(RES / "transactions_growth.csv")
txy = txa.unstack("year").reset_index()
txy["area"] = pd.Categorical(txy["area"], AREAS, ordered=True)
txy.sort_values(["area", "type"]).to_csv(RES / "transactions_annual.csv", index=False)
main["tx_national"] = {t: {"2013": int(txa[("全国", t, 2013)]), "2025": int(txa[("全国", t, 2025)]),
                           "伸び%": float(txg.loc["全国", f"件数の伸び_{t}"])} for t in ["戸建住宅", "マンション"]}
# 地域ごとの「価格の伸び」と「件数の伸び」の順位相関（全国を除く15地域、種類ごと）
from scipy.stats import spearmanr
sub = [a for a in AREAS if a != "全国"]
main["tx_price_spearman"] = {t: round(float(spearmanr(g.loc[sub, t], txg.loc[sub, f"件数の伸び_{t}"]).statistic), 3)
                             for t in ["戸建住宅", "マンション"]}

# 頑健性
rob = [J]
rob.append(judge(growth(a_sa, 2010, 2025), tr, "期間 2010→2025年"))
rob.append(judge(growth(a_sa, 2019, 2025), tr, "期間 2019→2025年"))
rob.append(judge(g_real, tr, "実質（消費者物価で割り引く）"))
a_or = annual("orig")
rob.append(judge(growth(a_or, 2013, 2025), trough_month("orig"), "原系列の年平均"))
d = idx[idx.series == "sa"]
med = d.groupby(["area", "type", "year"], sort=False)["index"].median()
rob.append(judge(growth(med, 2013, 2025), tr, "年の中央値で比べる"))
rob.append(judge(g, trough_year("sa"), "底を年平均の最小の年で決める"))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rob.to_dict(orient="records")

# 問い直し：東京都・愛知県・大阪府の戸建住宅は、1984年からの長い系列で見ると、バブル期の山にどこまで戻ったか
full = pd.read_csv(DATA / "rppi_monthly.csv")
full = full[(full.series == "sa") & (full.type.isin(["戸建住宅", "住宅地"])) & (full.area.isin(["東京都", "愛知県", "大阪府"]))].copy()
full["year"] = full.month.str[:4].astype(int)
fa = full[(full.year >= 1985) & (full.year <= 2025)].groupby(["area", "type", "year"], sort=False)["index"].mean()
req = {}
rows = []
for ar in ["東京都", "愛知県", "大阪府"]:
    for t in ["戸建住宅", "住宅地"]:
        s = fa.loc[(ar, t)]
        py = int(s.idxmax())
        req[f"{ar}_{t}"] = {"山の年": py, "山の値": round(float(s.max()), 1), "2025": round(float(s[2025]), 1),
                           "2025は山の%": round(100 * float(s[2025] / s.max()), 1),
                           "底の年(1992以降)": int(s.loc[1992:].idxmin()), "底の値": round(float(s.loc[1992:].min()), 1)}
        for y, v in s.items():
            rows.append((ar, t, y, round(float(v), 3)))
pd.DataFrame(rows, columns=["area", "type", "year", "index_sa"]).to_csv(RES / "requestion_long_series.csv", index=False)
cond = {ar: round(float(a_sa[(ar, "マンション", 2025)]), 1) for ar in ["東京都", "愛知県", "大阪府"]}
main["requestion"] = req
main["requestion_condo2025"] = cond

json.dump(main, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: main[k] for k in ["main", "national", "cpi_2013_2025_%", "detached_growth_range", "detached_lt10_areas",
                                       "real_detached_ge0", "real_detached_range", "lead_median_years", "tx_national",
                                       "tx_price_spearman", "share_of_detached_growth_after2019_national"]}, ensure_ascii=False, indent=0))
print(out[["戸建住宅_名目", "マンション_名目", "戸建住宅_実質", "底の月_マンション", "底の月_戸建住宅", "マンションの底が早い年数"]])
print(rob.to_string())
print(json.dumps(req, ensure_ascii=False))
print(txg)
