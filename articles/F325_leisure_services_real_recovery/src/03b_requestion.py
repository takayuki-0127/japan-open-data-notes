"""03b 問い直し（結果を見てから足した）：
(1) 国内パック旅行費の落ち込みは、コロナ前からの「パック離れ」の続きか。宿泊料＋国内パック旅行費のうちパックの割合（名目）を
    2015〜2019年の直線で2025年まで延ばし、実際と比べる。
(2) 全体の戻りの鈍さのうち、世帯主の年齢の構成（70歳以上の世帯が増えた）で説明できる分はどれだけか。
出力：results/requestion.json、results/pack_share.csv"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
d = pd.read_csv(DATA / "leisure_items.csv")
cpi = pd.read_csv(DATA / "cpi_leisure.csv").set_index("year")
r = lambda x: float(round(x, 4))
Q = {}
a = d[(d.table == "age") & (d.group == "平均")].pivot_table(index="year", columns="item", values="amount")
share = a["国内パック旅行費"] / (a["国内パック旅行費"] + a["宿泊料"])
pre = share.loc[2015:2019]
b, c0 = np.polyfit(pre.index.values.astype(float), pre.values, 1)
trend = pd.Series(c0 + b * share.index.values, index=share.index)
pd.DataFrame({"year": share.index, "pack_share": share.round(4).values, "trend_2015_2019": trend.round(4).values}).to_csv(RES / "pack_share.csv", index=False)
Q["pack_share_2015"] = r(share[2015]); Q["pack_share_2019"] = r(share[2019]); Q["pack_share_2025"] = r(share[2025])
Q["pack_share_trend_2025"] = r(trend[2025]); Q["pack_share_trend_slope_pt_per_year"] = r(b * 100)
# トレンドどおりなら 2025 年の国内パック旅行費（名目）はいくらだったか（宿泊料＋パックの合計は実際の値のまま）
tot25 = a.loc[2025, "国内パック旅行費"] + a.loc[2025, "宿泊料"]
Q["pack_2025_if_trend"] = int(round(trend[2025] * tot25)); Q["pack_2025_actual"] = int(a.loc[2025, "国内パック旅行費"])
Q["pack_2019_actual"] = int(a.loc[2019, "国内パック旅行費"])
Q["pack_2025_actual_minus_trend"] = int(Q["pack_2025_actual"] - Q["pack_2025_if_trend"])
Q["travel2_real_ratio"] = r((tot25 / cpi.loc[2025, "宿泊料"]) / ((a.loc[2019, "国内パック旅行費"] + a.loc[2019, "宿泊料"]) / cpi.loc[2019, "宿泊料"]))
# (2) 年齢構成：2025年の年齢別の額を、2019年の世帯の構成で平均し直す
ITEMS = ["宿泊料", "国内パック旅行費", "外国パック旅行費", "映画・演劇等入場料", "スポーツ観覧料", "スポーツクラブ使用料",
         "他のスポーツ施設使用料", "文化施設入場料", "遊園地入場・乗物代", "他の入場・ゲーム代"]
DEF = {"宿泊料": "宿泊料", "国内パック旅行費": "宿泊料", "外国パック旅行費": "外国パック旅行費", "映画・演劇等入場料": "映画・演劇",
       "スポーツ観覧料": "プロ野球観覧料", "スポーツクラブ使用料": "フィットネスクラブ使用料", "他のスポーツ施設使用料": "入場・観覧・ゲーム代",
       "文化施設入場料": "文化施設入場料", "遊園地入場・乗物代": "テーマパーク入場料", "他の入場・ゲーム代": "入場・観覧・ゲーム代"}
cpi["映画・演劇"] = (cpi["映画観覧料"] + cpi["演劇観覧料"]) / 2
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
x = d[(d.table == "age") & d.item.isin(ITEMS)].copy()
x["real"] = [v / cpi.loc[y, DEF[i]] * 100 for v, y, i in zip(x.amount, x.year, x.item)]
g = x.groupby(["year", "group"]).real.sum()
w = d[(d.table == "age") & (d.code == "hh_weight")].set_index(["year", "group"]).amount
def avg(year, wyear):
    return sum(g[(year, k)] * w[(wyear, k)] for k in AGES) / sum(w[(wyear, k)] for k in AGES)
Q["share_70plus_2019"] = r(w[(2019, "70歳以上")] / 10000); Q["share_70plus_2025"] = r(w[(2025, "70歳以上")] / 10000)
Q["R_real_reweighted_actual"] = r(avg(2025, 2025) / avg(2019, 2019))
Q["R_real_fixed_2019_weights"] = r(avg(2025, 2019) / avg(2019, 2019))
Q["composition_effect_pt"] = r((Q["R_real_fixed_2019_weights"] - Q["R_real_reweighted_actual"]) * 100)
Q["published_average_R_real"] = r(g[(2025, "平均")] / g[(2019, "平均")])
(RES / "requestion.json").write_text(json.dumps(Q, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(Q, ensure_ascii=False, indent=1)); print(pd.read_csv(RES / "pack_share.csv").to_string())
