"""問い直し（結果を見てから足した）：2015→2020年に情報通信業の就業者が大きく増えたとき、増えた分はどこに住む人だったのか。
地方別・東京都・東京圏の、増加への寄与の割合（原数値と不詳補完値）。地方中枢の県（北海道・宮城・愛知・大阪・広島・福岡）の立地係数も見る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
c = pd.read_csv(ROOT / "data" / "census.csv")
REGION = {"北海道": [1], "東北": list(range(2, 8)), "関東（東京圏を除く）": [8, 9, 10], "東京圏": [11, 12, 13, 14], "中部": list(range(15, 24)),
          "近畿": list(range(24, 31)), "中国": list(range(31, 36)), "四国": list(range(36, 40)), "九州・沖縄": list(range(40, 48))}
HUB = {1: "北海道", 4: "宮城県", 23: "愛知県", 27: "大阪府", 34: "広島県", 40: "福岡県"}


def r(x, k=1):
    return round(float(x), k)


g = c[(c.sex == "総数") & (c.ind == "G")].set_index("pref_code")
t = c[(c.sex == "総数") & (c.ind == "total")].set_index("pref_code")
rows = []
for a, b in [("y2005", "y2015"), ("y2015", "y2020"), ("y2015c", "y2020c")]:
    inc = g[b] - g[a]
    tot = inc.sum()
    for k, ps in list(REGION.items()) + [("うち東京都", [13])]:
        rows.append({"period": f"{a[1:]}→{b[1:]}", "region": k, "increase": int(inc[ps].sum()), "share_of_increase_pct": r(100 * inc[ps].sum() / tot)})
inc = pd.DataFrame(rows)
inc.to_csv(R / "increase_by_region.csv", index=False)

hub = []
for p, name in HUB.items():
    for y in ["y2005", "y2010", "y2015", "y2020"]:
        lq = (g.loc[p, y] / g[y].sum()) / (t.loc[p, y] / t[y].sum())
        hub.append({"pref": name, "year": int(y[1:]), "lq": r(lq, 3), "n": int(g.loc[p, y])})
hb = pd.DataFrame(hub)
hb.to_csv(R / "hub_lq.csv", index=False)


def pick(period, region):
    q = inc[(inc.period == period) & (inc.region == region)].iloc[0]
    return {"increase": int(q.increase), "share_pct": float(q.share_of_increase_pct)}


res = {
    "national_increase": {p: int(inc[inc.period == p].increase.iloc[:len(REGION)].sum()) for p in inc.period.unique()},
    "tokyo": {p: pick(p, "うち東京都") for p in inc.period.unique()},
    "tokyo_area": {p: pick(p, "東京圏") for p in inc.period.unique()},
    "hub_lq_2005": {n: float(hb[(hb.pref == n) & (hb.year == 2005)].lq.iloc[0]) for n in HUB.values()},
    "hub_lq_2020": {n: float(hb[(hb.pref == n) & (hb.year == 2020)].lq.iloc[0]) for n in HUB.values()},
}
(R / "requestion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
