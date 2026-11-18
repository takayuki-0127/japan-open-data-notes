"""地域鉄道（98社のうち2012〜2023年度がそろう事業者）の輸送密度：まとめた値の推移、帯ごとの事業者の数、変化率の分布、
運輸局別、第三セクターと中小民鉄、頑健性。出力：results/"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
BUREAUS = ["北海道", "東北", "北陸信越", "関東", "中部", "近畿", "中国", "四国", "九州"]
BANDS = [0, 500, 1000, 2000, 4000, 1e9]
BLAB = ["500人未満", "500〜1,000人", "1,000〜2,000人", "2,000〜4,000人", "4,000人以上"]
YEARS = list(range(2012, 2024))

m = pd.read_csv(ROOT / "data" / "chiiki_panel.csv")
days = m["fy"].map(lambda y: 366 if (y + 1) % 4 == 0 else 365)
m["days"] = days
# 表の平均通過数量と人キロから逆算した「営業キロ」が、その事業者のふだんの値（年度の中央値）から25%以上ずれる年度は、
# 表の平均通過数量の誤りか定義の違いとみて、人キロ ÷（ふだんの営業キロ×日数）に置き換える
m["km_implied"] = m["pk_total"] * 1000 / (m["density"] * m["days"])
# ただし、路線が実際に延びた事業者は、延びる前と後を分けて「ふだんの値」をとる（延びたこと自体を表の誤りとみなさない）
# しなの鉄道：2015年3月の北陸新幹線の延伸で北しなの線を引き継ぎ（2015年度から）。三陸鉄道：2019年3月にリアス線（宮古〜釜石）を引き継ぎ（2019年度から）
EXTEND = {"しなの鉄道": 2015, "三陸鉄道": 2019}
m["seg"] = [int(fy >= EXTEND[k]) if k in EXTEND else 0 for k, fy in zip(m["key"], m["fy"])]
med = m.groupby(["key", "seg"])["km_implied"].transform("median")
bad = ((m["km_implied"] / med - 1).abs() > 0.25) | m["density"].isna()
m["density_clean"] = np.where(bad, m["pk_total"] * 1000 / (med * m["days"]), m["density"])
m["replaced"] = bad.astype(int)
nyrs = m.groupby("key")["fy"].nunique()
bal = sorted(nyrs[nyrs == len(YEARS)].index)
b = m[m["key"].isin(bal)].copy()
b.to_csv(R / "panel_balanced.csv", index=False, encoding="utf-8")


def agg_density(df, col="density_clean"):
    """Σ人キロ ÷ Σ(人キロ÷輸送密度)：営業キロ×日数で重みをつけた平均（人／日）"""
    g = df.groupby("fy", sort=True)
    return g["pk_total"].sum() * 1000 / g.apply(lambda t: (t["pk_total"] * 1000 / t[col]).sum(), include_groups=False)


def r(x, n=1):
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


ad = agg_density(b)
ad_raw = agg_density(b, "density")
pk = b.groupby("fy", sort=True)["pk_total"].sum()
nat = pd.DataFrame({"agg_density": ad, "agg_density_table_raw": ad_raw, "pk_total_million": pk / 1e3,
                    "median_density": b.groupby("fy")["density_clean"].median()})
nat["agg_idx_2019"] = nat["agg_density"] / nat.loc[2019, "agg_density"] * 100
nat.round(3).to_csv(R / "aggregate_by_year.csv", encoding="utf-8")

# 帯ごとの事業者の数
b["band"] = pd.cut(b["density_clean"], BANDS, right=False, labels=BLAB)
cnt = b.groupby(["fy", "band"], observed=False).size().unstack()
cnt.to_csv(R / "count_by_band.csv", encoding="utf-8")

# 事業者ごとの変化率
w = b.pivot(index="key", columns="fy", values="density_clean")
chg = pd.DataFrame({"pct_2012_2019": (w[2019] / w[2012] - 1) * 100, "pct_2019_2023": (w[2023] / w[2019] - 1) * 100,
                    "pct_2012_2023": (w[2023] / w[2012] - 1) * 100})
info = b.drop_duplicates("key").set_index("key")[["third_sector", "bureau", "km"]]
chg = chg.join(info)
q = chg[["pct_2012_2019", "pct_2019_2023", "pct_2012_2023"]].quantile([0.25, 0.5, 0.75]).T
q.columns = ["q25", "median", "q75"]
q.round(2).to_csv(R / "change_distribution.csv", encoding="utf-8")

# 運輸局別（北から南）、区分別
rows = []
for g in BUREAUS:
    t = b[b["bureau"] == g]
    if t.empty:
        continue
    a = agg_density(t)
    rows.append({"bureau": g, "n": t["key"].nunique(), "agg_2012": r(a[2012], 0), "agg_2019": r(a[2019], 0), "agg_2023": r(a[2023], 0),
                 "pct_2012_2019": r((a[2019] / a[2012] - 1) * 100), "pct_2019_2023": r((a[2023] / a[2019] - 1) * 100)})
byb = pd.DataFrame(rows)
byb.to_csv(R / "by_bureau.csv", index=False, encoding="utf-8")
rows = []
for ts, lab in [(1, "第三セクター"), (0, "中小民鉄")]:
    t = b[b["third_sector"] == ts]; a = agg_density(t); c = chg[chg["third_sector"] == ts]
    rows.append({"kind": lab, "n": t["key"].nunique(), "agg_2012": r(a[2012], 0), "agg_2019": r(a[2019], 0), "agg_2023": r(a[2023], 0),
                 "median_density_2023": r(t[t.fy == 2023]["density_clean"].median(), 0),
                 "median_pct_2012_2023": r(c["pct_2012_2023"].median()), "median_pct_2012_2019": r(c["pct_2012_2019"].median()),
                 "median_pct_2019_2023": r(c["pct_2019_2023"].median())})
byk = pd.DataFrame(rows)
byk.to_csv(R / "by_kind.csv", index=False, encoding="utf-8")

# 頑健性
rob = []
def add(check, h, val, note=""):
    rob.append({"check": check, "hypothesis": h, "value": r(val, 2), "note": note})
add("基本：まとめた輸送密度 2019/2012（%）", "H1", ad[2019] / ad[2012] * 100)
add("基本：まとめた輸送密度 2023/2019（%）", "H2", ad[2023] / ad[2019] * 100)
add("基本：1,000人未満の事業者数 2023−2012", "H3", (w[2023] < 1000).sum() - (w[2012] < 1000).sum())
k = byk.set_index("kind")
add("基本：変化率の中央値の差（第三セクター−中小民鉄、ポイント）", "H4", k.loc["第三セクター", "median_pct_2012_2023"] - k.loc["中小民鉄", "median_pct_2012_2023"])
med_ = b.groupby("fy")["density_clean"].median()
add("まとめ方：単純な中央値 2019/2012（%）", "H1", med_[2019] / med_[2012] * 100)
add("まとめ方：単純な中央値 2023/2019（%）", "H2", med_[2023] / med_[2019] * 100)
add("基準：2018/2013（%）", "H1", ad[2018] / ad[2013] * 100)
add("基準：2023/2018（%）", "H2", ad[2023] / ad[2018] * 100)
add("表の平均通過数量をそのまま使う：2019/2012（%）", "H1", ad_raw[2019] / ad_raw[2012] * 100)
add("表の平均通過数量をそのまま使う：2023/2019（%）", "H2", ad_raw[2023] / ad_raw[2019] * 100)
wr = b.pivot(index="key", columns="fy", values="density")
add("表の平均通過数量をそのまま使う：1,000人未満の数 2023−2012", "H3", (wr[2023] < 1000).sum() - (wr[2012] < 1000).sum())
jump = (w / w.shift(axis=1)).loc[:, 2013:]
stable = jump[~((jump < 0.5) | (jump > 2.0)).any(axis=1)].index
s = b[b["key"].isin(stable)]; a2 = agg_density(s); c2 = chg.loc[stable]
add(f"大きく動いた事業者を除く（{len(bal) - len(stable)}社）：2019/2012（%）", "H1", a2[2019] / a2[2012] * 100)
add("大きく動いた事業者を除く：2023/2019（%）", "H2", a2[2023] / a2[2019] * 100)
add("大きく動いた事業者を除く：中央値の差（第三セクター−中小民鉄）", "H4",
    c2[c2.third_sector == 1]["pct_2012_2023"].median() - c2[c2.third_sector == 0]["pct_2012_2023"].median())
s3 = b[~b["key"].isin(list(EXTEND))]; a3 = agg_density(s3)
add(f"路線が延びた{len(EXTEND)}社（しなの鉄道・三陸鉄道）を除く：2019/2012（%）", "H1", a3[2019] / a3[2012] * 100)
add("路線が延びた2社を除く：2023/2019（%）", "H2", a3[2023] / a3[2019] * 100)
add("2020年度（コロナの年）/2019（%）", "参考", ad[2020] / ad[2019] * 100)
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False, encoding="utf-8")

# 定期の割合（利用の中身）
sh = b.groupby("fy", sort=True)[["pk_pass", "pk_nonpass", "pk_total"]].sum()
sh["pass_share"] = sh["pk_pass"] / sh["pk_total"] * 100
sh.round(3).to_csv(R / "pass_share.csv", encoding="utf-8")

main = {
    "n_list": int(m["key"].nunique()), "n_balanced": len(bal), "n_cells_replaced": int(b["replaced"].sum()),
    "n_cells_total": int(len(b)),
    "agg_density": {str(y): r(ad[y], 0) for y in (2012, 2016, 2019, 2020, 2021, 2022, 2023)},
    "H1_2019_vs_2012_pct": r(ad[2019] / ad[2012] * 100),
    "H2_2023_vs_2019_pct": r(ad[2023] / ad[2019] * 100),
    "H1_ex_extended_pct": r(a3[2019] / a3[2012] * 100),
    "covid_2020_vs_2019_pct": r(ad[2020] / ad[2019] * 100),
    "pk_total_million": {str(y): r(pk[y] / 1e3, 1) for y in (2012, 2019, 2020, 2023)},
    "median_density": {str(y): r(med_[y], 0) for y in (2012, 2019, 2023)},
    "under1000": {str(y): int((w[y] < 1000).sum()) for y in (2012, 2019, 2020, 2023)},
    "under500": {str(y): int((w[y] < 500).sum()) for y in (2012, 2019, 2023)},
    "over4000": {str(y): int((w[y] >= 4000).sum()) for y in (2012, 2019, 2023)},
    "change_median_pct": {k2: r(v) for k2, v in q["median"].items()},
    "change_q25_pct": {k2: r(v) for k2, v in q["q25"].items()},
    "change_q75_pct": {k2: r(v) for k2, v in q["q75"].items()},
    "n_down_2012_2019": int((chg["pct_2012_2019"] < 0).sum()), "n_down_2012_2023": int((chg["pct_2012_2023"] < 0).sum()),
    "n_below_2019_in_2023": int((chg["pct_2019_2023"] < 0).sum()),
    "by_kind": byk.set_index("kind").to_dict(orient="index"),
    "pass_share_pct": {str(y): r(sh.loc[y, "pass_share"]) for y in (2012, 2019, 2020, 2023)},
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(rob).to_string()); print(byb.to_string()); print(cnt.to_string())
