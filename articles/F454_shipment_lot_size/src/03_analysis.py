"""流動ロットの推移、輸送機関の構成と輸送機関の中のロットへの分解、ロット階層別の割合。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
m = pd.read_csv(ROOT / "data" / "modes.csv")
m["lot"] = m.ton / m["count"]
TON = m.pivot(index="year", columns="mode", values="ton"); CNT = m.pivot(index="year", columns="mode", values="count")
LOT = TON / CNT
LOT.to_csv(R / "lot_by_mode.csv", float_format="%.5f")
parts = [c for c in TON.columns if c != "合計"]
assert (abs(TON[parts].sum(axis=1) - TON["合計"]) / TON["合計"] < 0.001).all()


def shift(y0, y1, cols):
    """合計のロット = Σ 件数の割合 × 輸送機関のロット。構成の分と輸送機関の中の分に分ける（中点の重み）。"""
    s0 = CNT.loc[y0, cols] / CNT.loc[y0, cols].sum(); s1 = CNT.loc[y1, cols] / CNT.loc[y1, cols].sum()
    l0 = LOT.loc[y0, cols]; l1 = LOT.loc[y1, cols]
    mix = ((s1 - s0) * (l0 + l1) / 2); within = ((l1 - l0) * (s0 + s1) / 2)
    tot0 = TON.loc[y0, cols].sum() / CNT.loc[y0, cols].sum(); tot1 = TON.loc[y1, cols].sum() / CNT.loc[y1, cols].sum()
    return dict(lot0=tot0, lot1=tot1, change=tot1 - tot0, mix=float(mix.sum()), within=float(within.sum()),
                mix_by=mix.to_dict(), within_by=within.to_dict())


d = shift(2005, 2021, parts)
pd.DataFrame({"mix": d["mix_by"], "within": d["within_by"]}).to_csv(R / "shift_share_2005_2021.csv", float_format="%.5f")
tot = LOT["合計"]
main = {"lot": {int(y): round(float(v), 3) for y, v in tot.items()},
        "lot_pct_2000_2021": round(float((tot[2021] / tot[2000] - 1) * 100), 1),
        "count_pct_2000_2021": round(float((CNT.loc[2021, "合計"] / CNT.loc[2000, "合計"] - 1) * 100), 1),
        "ton_pct_2000_2021": round(float((TON.loc[2021, "合計"] / TON.loc[2000, "合計"] - 1) * 100), 1),
        "count_million": {int(y): round(float(v) / 1e6, 2) for y, v in CNT["合計"].items()},
        "ton_million": {int(y): round(float(v) / 1e6, 2) for y, v in TON["合計"].items()},
        "shift_2005_2021": {k: round(v, 4) for k, v in d.items() if not isinstance(v, dict)},
        "lot_mode_2000": {k: round(float(v), 3) for k, v in LOT.loc[2000].items()},
        "lot_mode_2021": {k: round(float(v), 3) for k, v in LOT.loc[2021].items()},
        "count_share_parcel": {int(y): round(float(CNT.loc[y, "宅配便等混載"] / CNT.loc[y, "合計"] * 100), 1) for y in CNT.index}}
main["shift_2005_2021"]["within_share_pct"] = round(d["within"] / d["change"] * 100, 1)
# ロット階層
L = pd.read_csv(ROOT / "data" / "lot_classes.csv")
L["count_share"] = L["count"] / L.groupby("year")["count"].transform("sum") * 100
L["ton_share"] = L.ton / L.groupby("year").ton.transform("sum") * 100
L.to_csv(R / "lot_classes_share.csv", index=False, float_format="%.4f")
def small(y, cls):
    x = L[(L.year == y) & (L.lot_class.isin(cls))]
    return round(float(x.count_share.sum()), 1), round(float(x.ton_share.sum()), 2)
U01 = ["<0.01", "0.01-0.05", "0.05-0.1"]
for y in [2015, 2021]:
    main[f"under0.1_{y}"] = dict(zip(["count_share", "ton_share"], small(y, U01)))
    main[f"under0.05_{y}"] = dict(zip(["count_share", "ton_share"], small(y, U01[:2])))
    main[f"under0.5_{y}"] = dict(zip(["count_share", "ton_share"], small(y, U01 + ["0.1-0.5"])))
    main[f"over10_{y}"] = dict(zip(["count_share", "ton_share"], small(y, ["10-15", "15-20", "20-30", "30-50", "50-100", "100-500", "500-1000", ">=1000"])))
c21, t21 = main["under0.1_2021"]["count_share"], main["under0.1_2021"]["ton_share"]
main["hypotheses"] = {
    "H1": "支持" if main["lot_pct_2000_2021"] <= -40 else "外れ",
    "H2": "支持" if main["count_pct_2000_2021"] > 0 and main["ton_pct_2000_2021"] < 0 else "外れ",
    "H3": "支持" if abs(d["within"]) > abs(d["mix"]) and d["within"] < 0 else "外れ",
    "H4": "支持" if c21 >= 80 and t21 < 2 else "外れ",
}
# 頑健性
rb = []
for a, b in [(2005, 2021), (2015, 2021), (2000, 2015)]:
    rb.append(dict(check=f"合計のロットの変化 {a}→{b}", value=round(float((tot[b] / tot[a] - 1) * 100), 1), unit="%"))
ex = [c for c in parts if c != "宅配便等混載"]
l_ex = TON[ex].sum(axis=1) / CNT[ex].sum(axis=1)
rb.append(dict(check="宅配便等混載を除く合計のロット 2000→2021", value=round(float((l_ex[2021] / l_ex[2000] - 1) * 100), 1), unit="%"))
ex2 = [c for c in parts if c != "その他"]
l_ex2 = TON[ex2].sum(axis=1) / CNT[ex2].sum(axis=1)
rb.append(dict(check="「その他」の輸送機関を除く合計のロット 2000→2021（2021年に件数が急に増えた区分）", value=round(float((l_ex2[2021] / l_ex2[2000] - 1) * 100), 1), unit="%"))
d2 = shift(2005, 2021, ex2)
rb.append(dict(check="「その他」を除いたときの、輸送機関の中の分の割合（2005→2021）", value=round(d2["within"] / d2["change"] * 100, 1), unit="%"))
d3 = shift(2000, 2021, parts)
rb.append(dict(check="分解の期間を2000→2021にしたときの、輸送機関の中の分の割合", value=round(d3["within"] / d3["change"] * 100, 1), unit="%"))
ov = pd.read_csv(ROOT / "data" / "overlap_check.csv")
rb.append(dict(check="2つの公表年の表の重なる年の重量・件数の最大の差", value=float(max((ov.ton_2021table - ov.ton_2015table).abs().max(), (ov.count_2021table - ov.count_2015table).abs().max())), unit="トン・件"))
rb.append(dict(check="0.05トン未満の件数の割合（2021）", value=main["under0.05_2021"]["count_share"], unit="%"))
rb.append(dict(check="0.5トン未満の件数の割合（2021）", value=main["under0.5_2021"]["count_share"], unit="%"))
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {r.check: r.value for r in rbd.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rbd.to_string())
