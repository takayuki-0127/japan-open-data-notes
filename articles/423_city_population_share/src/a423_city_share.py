"""A423 市部に住む人の割合と、人口集中地区に住む人の割合。国勢調査（人口統計資料集 2026 表9-9・9-10）"""
import csv, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
SRC = "出典：総務省統計局「国勢調査」（国立社会保障・人口問題研究所「人口統計資料集 2026」表9-9・表9-10）をもとに作成者が加工して作成"
num = lambda s: float(str(s).replace(",", "")) if str(s).strip() not in ("-", "…", "") else np.nan
r9 = [r for r in csv.reader(open(DATA / "ipss2026_T09-09_shibu_gunbu.csv", encoding="utf-8")) if r and r[0].strip().isdigit()]
# 列：年, 注, 市部人口, 郡部人口, 市部%, 郡部%, 空, 市町村数, 市, 町村（人口は1,000人）
a = pd.DataFrame([[int(r[0]), num(r[2]), num(r[3]), num(r[4]), num(r[5]), num(r[7]), num(r[8]), num(r[9])] for r in r9],
                 columns=["year", "shi_pop", "gun_pop", "shi_pct_pub", "gun_pct_pub", "n_muni", "n_shi", "n_choson"])
a["shi_pct"] = a.shi_pop / (a.shi_pop + a.gun_pop) * 100
assert (a.shi_pct.round(1) - a.shi_pct_pub).abs().max() <= 0.11
r10 = [r for r in csv.reader(open(DATA / "ipss2026_T09-10_did.csv", encoding="utf-8")) if r and r[0].strip().isdigit()]
b = pd.DataFrame([[int(r[0])] + [num(x) for x in r[1:10]] for r in r10],
                 columns=["year", "did_pop", "did_shi", "did_gun", "did_pct", "did_pct_in_shi", "did_pct_in_gun", "did_area", "did_area_shi", "did_area_gun"])
d = a.merge(b, on="year", how="left"); d["gap"] = d.shi_pct - d.did_pct
d["shi_nondid_pop"] = d.shi_pop - d.did_shi          # 市部に住むが人口集中地区の外（1,000人）
d["shi_nondid_pct"] = d.shi_nondid_pop / (d.shi_pop + d.gun_pop) * 100
d["did_density"] = d.did_pop * 1000 / d.did_area
d.to_csv(RES / "a423_city_and_did.csv", index=False)
R = d.set_index("year"); out = {}
for y in [1920, 1930, 1940, 1945, 1950, 1955, 1960, 1970, 1980, 1990, 2000, 2005, 2010, 2020]:
    out[f"y{y}"] = {k: (None if pd.isna(R.loc[y, k]) else round(float(R.loc[y, k]), 1)) for k in
                    ["shi_pct", "did_pct", "gap", "shi_pop", "gun_pop", "n_shi", "n_choson", "did_pct_in_shi", "shi_nondid_pct", "did_density"]}
out["first_census_above"] = {str(t): int(d[d.shi_pct >= t].year.iloc[0]) for t in [20, 30, 50, 60, 70, 80, 90]}
out["did_first_above"] = {str(t): int(d[d.did_pct >= t].year.iloc[0]) for t in [50, 60, 70]}
# 5年ごとの変化（ポイント）
d["d_shi"] = d.shi_pct.diff(); d["d_did"] = d.did_pct.diff(); d["d_nshi"] = d.n_shi.diff(); d["d_ncho"] = d.n_choson.diff()
ch = d[["year", "d_shi", "d_did", "d_nshi", "d_ncho"]].dropna(subset=["d_shi"]).round(2); ch.to_csv(RES / "a423_change_5y.csv", index=False)
out["change_5y"] = {str(int(r.year)): {"shi": round(r.d_shi, 1), "did": (None if pd.isna(r.d_did) else round(r.d_did, 1)), "n_shi": int(r.d_nshi), "n_choson": int(r.d_ncho)} for r in ch.itertuples()}
# 3つの大きな段差（1950→55、2000→05、2005→10）が上がり幅に占める割合
tot = R.loc[2020, "shi_pct"] - R.loc[1920, "shi_pct"]; jumps = sum(R.loc[y, "shi_pct"] - R.loc[y - 5, "shi_pct"] for y in [1955, 2005, 2010])
out["rise_1920_2020"] = round(tot, 1); out["three_jumps"] = round(jumps, 1); out["three_jumps_share"] = round(jumps / tot * 100, 1)
out["rise_1960_2020"] = {"shi": round(R.loc[2020, "shi_pct"] - R.loc[1960, "shi_pct"], 1), "did": round(R.loc[2020, "did_pct"] - R.loc[1960, "did_pct"], 1)}
out["rise_2000_2010"] = {"shi": round(R.loc[2010, "shi_pct"] - R.loc[2000, "shi_pct"], 1), "did": round(R.loc[2010, "did_pct"] - R.loc[2000, "did_pct"], 1),
                         "n_shi": int(R.loc[2010, "n_shi"] - R.loc[2000, "n_shi"]), "n_choson": int(R.loc[2010, "n_choson"] - R.loc[2000, "n_choson"])}
out["rise_1950_1955"] = {"shi": round(R.loc[1955, "shi_pct"] - R.loc[1950, "shi_pct"], 1), "n_shi": int(R.loc[1955, "n_shi"] - R.loc[1950, "n_shi"]),
                         "n_choson": int(R.loc[1955, "n_choson"] - R.loc[1950, "n_choson"])}
# 頑健性：段差の3回を除いて、ほかの期間の平均ペースで置き換えた「合併がなかった場合」の市部の割合（粗い見積もり）
others = [R.loc[y, "shi_pct"] - R.loc[y - 5, "shi_pct"] for y in range(1965, 2001, 5)]
out["avg_5y_rise_1960_2000"] = round(float(np.mean(others)), 2)
out["did_avg_5y_rise_1960_2000"] = round(float(np.mean([R.loc[y, "did_pct"] - R.loc[y - 5, "did_pct"] for y in range(1965, 2001, 5)])), 2)
out["did_avg_5y_rise_2000_2020"] = round(float(np.mean([R.loc[y, "did_pct"] - R.loc[y - 5, "did_pct"] for y in range(2005, 2021, 5)])), 2)
out["did_area_share_note"] = {"1960_km2": R.loc[1960, "did_area"], "2020_km2": R.loc[2020, "did_area"], "ratio": round(R.loc[2020, "did_area"] / R.loc[1960, "did_area"], 2)}
json.dump(out, open(RES / "a423_main.json", "w"), ensure_ascii=False, indent=1)

fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(d.year, d.shi_pct, color=BLUE, lw=2.2, marker="o", ms=4, label="市部に住む人の割合")
m = d.dropna(subset=["did_pct"]); ax.plot(m.year, m.did_pct, color=ORANGE, lw=2.2, marker="o", ms=4, label="人口集中地区に住む人の割合（1960年〜）")
ax.axhline(50, color="#cccccc", lw=.8)
for y in [1920, 1950, 1955, 2000, 2010, 2020]: ax.annotate(f"{R.loc[y,'shi_pct']:.0f}%", (y, R.loc[y, "shi_pct"]), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8.5, color=BLUE)
for y in [1960, 2000, 2020]: ax.annotate(f"{R.loc[y,'did_pct']:.0f}%", (y, R.loc[y, "did_pct"]), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=8.5, color=ORANGE)
ax.set_ylim(0, 100); ax.set_ylabel("総人口に占める割合（%）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("市部の割合は1955年に5割を超え、2010年に9割。人口集中地区の割合は2020年に7割"); save(fig, "a423_share.png", SRC)
c = d.dropna(subset=["d_shi"]); fig, ax = plt.subplots(figsize=(9, 4.8)); w = 1.9
ax.bar(c.year - w / 2, c.d_shi, width=w, color=BLUE, label="市部の割合"); cc = c.dropna(subset=["d_did"]); ax.bar(cc.year + w / 2, cc.d_did, width=w, color=ORANGE, label="人口集中地区の割合")
ax.axhline(0, color=INK, lw=.8); ax.set_xticks(c.year); ax.set_xticklabels([f"{int(y)-5}→\n{str(int(y))[2:]}" for y in c.year], fontsize=7.5)
ax.legend(frameon=False); ax.set_ylabel("5年間の変化（ポイント）"); ax.set_title("市部の割合が大きく上がったのは、合併の多かった3つの時期だった"); save(fig, "a423_change_5y.png", SRC)
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(d.year, d.n_choson, color=GRAY, lw=2, marker="o", ms=4, label="町村の数（左の目盛り）"); ax.set_ylabel("町村の数")
ax2 = ax.twinx(); ax2.plot(d.year, d.n_shi, color=BLUE, lw=2, marker="o", ms=4, label="市の数（右の目盛り）"); ax2.set_ylabel("市の数"); ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, loc="center right")
ax.set_title("町村は1万2千から926に減り、市は83から793に増えた"); save(fig, "a423_municipalities.png", SRC)
print(json.dumps(out, ensure_ascii=False))
