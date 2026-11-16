"""外食・調理食品の割合、名目の伸びの物価と量への分解、世帯の形、2020年の落ち込み。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "food_spending.csv")


def table(series, kind="名目"):
    return d[(d.series == series) & (d.kind == kind)].pivot(index="year", columns="item", values="value").sort_index()


def r(x, k=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


L = table("二人以上（農林漁家を除く）1963-2007")
T = table("二人以上 2000-")
G = table("二人以上 2000-", "実質増減率")
S = table("単身 2000-")
A = table("総世帯 2000-")


def shares(t):
    o = pd.DataFrame(index=t.index)
    o["away_pct"] = 100 * t["外食"] / t["食料"]
    o["prepared_pct"] = 100 * t["調理食品"] / t["食料"]
    o["both_pct"] = o["away_pct"] + o["prepared_pct"]
    if "学校給食" in t:
        o["away_ex_school_pct"] = 100 * (t["外食"] - t["学校給食"]) / t["食料"]
    o["food_share_of_consumption_pct"] = 100 * t["食料"] / t["消費支出"]
    return o


sl, st, ss, sa = shares(L), shares(T), shares(S), shares(A)
# つないだ系列：2000年より前は1963-2007、2000年からは2000-
link = pd.concat([sl.loc[:1999], st]).sort_index()
link.to_csv(R / "shares_linked.csv")
pd.concat({"二人以上(1963-2007)": sl, "二人以上(2000-)": st, "単身(2000-)": ss, "総世帯(2000-)": sa}, names=["series"]).to_csv(R / "shares_all.csv")

main = {}
main["both_pct"] = {str(y): r(link.loc[y, "both_pct"]) for y in [1963, 1970, 1980, 1990, 2000, 2010, 2019, 2020, 2024, 2025]}
main["away_pct"] = {str(y): r(link.loc[y, "away_pct"]) for y in [1963, 1975, 1990, 2000, 2019, 2020, 2025]}
main["prepared_pct"] = {str(y): r(link.loc[y, "prepared_pct"]) for y in [1963, 1975, 1990, 2000, 2019, 2025]}
main["food_share_of_consumption_pct"] = {str(y): r(link.loc[y, "food_share_of_consumption_pct"]) for y in [1963, 2000, 2025]}
pk = sl["away_pct"]
main["away_pct_peak_1963_2007"] = {"year": int(pk.idxmax()), "pct": r(pk.max())}
pk2 = sl["both_pct"]
main["both_pct_1963_2007_peak"] = {"year": int(pk2.idxmax()), "pct": r(pk2.max())}
# 重なりの確かめ（2000〜2007年）
ov = pd.DataFrame({"long": sl.loc[2000:2007, "both_pct"], "new": st.loc[2000:2007, "both_pct"]})
ov["diff"] = ov["new"] - ov["long"]
main["overlap_2000_2007_both_pct_diff_max_abs"] = r(ov["diff"].abs().max(), 2)
ov.to_csv(R / "overlap_check.csv")

# 名目の伸びの分解（2000→2025）：実質増減率を積み上げて実質の指数をつくる
def real_index(item):
    g = G[item].copy()
    idx = [100.0]
    for y in range(2001, 2026):
        idx.append(idx[-1] * (1 + g.loc[y] / 100))
    return pd.Series(idx, index=range(2000, 2026))


dec = {}
rows = []
for item in ["食料", "調理食品", "外食", "一般外食", "消費支出"]:
    nom = 100 * T[item] / T.loc[2000, item]
    real = real_index(item)
    price = 100 * nom / real
    for y in range(2000, 2026):
        rows.append({"item": item, "year": y, "nominal_idx": nom.loc[y], "real_idx": real.loc[y], "price_idx": price.loc[y]})
    ln = np.log(nom.loc[2025] / 100); lr = np.log(real.loc[2025] / 100); lp = ln - lr
    dec[item] = {"nominal_change_pct": r(nom.loc[2025] - 100), "real_change_pct": r(real.loc[2025] - 100),
                 "price_change_pct": r(price.loc[2025] - 100), "price_share_of_log_growth_pct": r(100 * lp / ln) if ln != 0 else None}
idxdf = pd.DataFrame(rows)
idxdf.to_csv(R / "nominal_real_price_index.csv", index=False)
main["decomposition_2000_2025"] = dec
# 2019年＝100 の外食の実質
ra = real_index("外食"); rg = real_index("一般外食"); rp = real_index("調理食品")
main["away_real_2019_100"] = {str(y): r(100 * ra.loc[y] / ra.loc[2019]) for y in range(2019, 2026)}
main["prepared_real_2019_100"] = {str(y): r(100 * rp.loc[y] / rp.loc[2019]) for y in [2019, 2020, 2025]}
main["general_away_real_2019_100_2025"] = r(100 * rg.loc[2025] / rg.loc[2019])

# 世帯の形
main["household_type_2025_both_pct"] = {"単身": r(ss.loc[2025, "both_pct"]), "二人以上": r(st.loc[2025, "both_pct"]), "総世帯": r(sa.loc[2025, "both_pct"])}
main["household_type_2000_both_pct"] = {"単身": r(ss.loc[2000, "both_pct"]), "二人以上": r(st.loc[2000, "both_pct"]), "総世帯": r(sa.loc[2000, "both_pct"])}
main["single_2025"] = {"away_pct": r(ss.loc[2025, "away_pct"]), "prepared_pct": r(ss.loc[2025, "prepared_pct"])}
main["single_2019"] = {"away_pct": r(ss.loc[2019, "away_pct"]), "prepared_pct": r(ss.loc[2019, "prepared_pct"]), "both_pct": r(ss.loc[2019, "both_pct"])}

# 頑健性
main["robust"] = {
    "away_ex_school_pct": {str(y): r(link.loc[y, "away_ex_school_pct"]) for y in [1963, 2000, 2025]},
    "total_households_both_pct": {str(y): r(sa.loc[y, "both_pct"]) for y in [2000, 2019, 2025]},
    "per_capita_prepared_nominal_change_2000_2025_pct": r(100 * ((T.loc[2025, "調理食品"] / T.loc[2025, "世帯人員(人)"]) / (T.loc[2000, "調理食品"] / T.loc[2000, "世帯人員(人)"]) - 1)),
    # レビューで追加：世帯人員の変化を除いた1人あたりの量（実質）
    "household_size_2000_2025": [r(T.loc[2000, "世帯人員(人)"], 2), r(T.loc[2025, "世帯人員(人)"], 2)],
    "per_capita_away_real_change_2000_2025_pct": r(100 * ((ra.loc[2025] / T.loc[2025, "世帯人員(人)"]) / (ra.loc[2000] / T.loc[2000, "世帯人員(人)"]) - 1)),
    "per_capita_prepared_real_change_2000_2025_pct": r(100 * ((rp.loc[2025] / T.loc[2025, "世帯人員(人)"]) / (rp.loc[2000] / T.loc[2000, "世帯人員(人)"]) - 1)),
    "prepared_nominal_change_2000_2025_pct": r(100 * (T.loc[2025, "調理食品"] / T.loc[2000, "調理食品"] - 1)),
    "both_pct_2017_2018_2019": [r(st.loc[y, "both_pct"]) for y in (2017, 2018, 2019)],
    "both_pct_change_2017_18_vs_avg_2000_2017": [r(st.loc[2018, "both_pct"] - st.loc[2017, "both_pct"], 2),
                                                 r(st["both_pct"].diff().loc[2001:2017].mean(), 2)],
}

main["hypotheses"] = {
    "H1": {"value": dec["調理食品"]["price_share_of_log_growth_pct"], "verdict": "支持" if dec["調理食品"]["price_share_of_log_growth_pct"] >= 50 else "外れ"},
    "H2": {"value": main["household_type_2025_both_pct"]["単身"], "verdict": "支持" if main["household_type_2025_both_pct"]["単身"] >= 45 else "外れ"},
    "H3": {"value": main["away_real_2019_100"]["2025"], "verdict": "支持" if main["away_real_2019_100"]["2025"] < 100 else "外れ"},
    "H4": {"value": main["away_pct_peak_1963_2007"]["year"], "verdict": "支持" if main["away_pct_peak_1963_2007"]["year"] < 2000 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=0))
