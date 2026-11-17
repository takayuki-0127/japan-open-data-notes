"""主な分析：電話機・電算機類の輸入額を台数・円建て単価に分け、円建て単価をドル建て単価・ドル円に分ける。国別の割合。仮説・頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "imports.csv")
fx = pd.read_csv(ROOT / "data" / "usdjpy.csv", index_col=0)


def r(x, k=1):
    return round(float(x), k)


def series(area, item):
    x = d[(d.area == area) & (d.item == item)].set_index("year")
    t = pd.DataFrame({"qty": x.qty, "value_yen": x.value_thousand_yen * 1000})
    t["unit_yen"] = t.value_yen / t.qty
    t["usdjpy"] = fx.usdjpy_avg
    t["unit_usd"] = t.unit_yen / t.usdjpy
    return t


def decompose(t, y0, y1, fxcol="usdjpy_avg"):
    usd = t.unit_yen / fx[fxcol]
    dv = np.log(t.value_yen[y1] / t.value_yen[y0]); dq = np.log(t.qty[y1] / t.qty[y0])
    dp = np.log(t.unit_yen[y1] / t.unit_yen[y0]); dfx = np.log(fx[fxcol][y1] / fx[fxcol][y0]); dusd = np.log(usd[y1] / usd[y0])
    return {"y0": y0, "y1": y1, "value_change_pct": r(100 * (np.exp(dv) - 1)), "qty_change_pct": r(100 * (np.exp(dq) - 1)),
            "unit_yen_change_pct": r(100 * (np.exp(dp) - 1)), "fx_change_pct": r(100 * (np.exp(dfx) - 1)), "unit_usd_change_pct": r(100 * (np.exp(dusd) - 1)),
            "share_unit_in_value_pct": r(100 * dp / dv), "share_fx_in_unit_pct": r(100 * dfx / dp) if dp != 0 else None,
            "share_fx_in_value_pct": r(100 * dfx / dv), "share_qty_in_value_pct": r(100 * dq / dv)}


ph = series("世界", "phones"); pc = series("世界", "computers")
pd.concat({"phones": ph.loc[2017:], "computers": pc}, names=["item", "year"]).round(4).to_csv(R / "world_series.csv")
dec = {"phones_2017_2025": decompose(ph, 2017, 2025), "computers_2017_2025": decompose(pc, 2017, 2025)}

# 国別の割合（電話機）
shares = []
for item in ["phones", "computers"]:
    w = d[(d.area == "世界") & (d.item == item)].set_index("year").value_thousand_yen
    for a in ["中国", "ASEAN", "米国"]:
        x = d[(d.area == a) & (d.item == item)].set_index("year").value_thousand_yen
        for y in [2017, 2021, 2025]:
            shares.append({"item": item, "area": a, "year": y, "share_pct": r(100 * x[y] / w[y], 2)})
sh = pd.DataFrame(shares)
sh.to_csv(R / "country_shares.csv", index=False)


def s(item, a, y):
    return float(sh[(sh.item == item) & (sh.area == a) & (sh.year == y)].share_pct.iloc[0])


p = dec["phones_2017_2025"]; c = dec["computers_2017_2025"]
hyp = {
    "H1": {"share_fx_in_unit_pct": p["share_fx_in_unit_pct"], "verdict": "支持" if p["share_fx_in_unit_pct"] >= 50 else "外れ"},
    "H2": {"unit_usd_change_pct": p["unit_usd_change_pct"], "verdict": "支持" if p["unit_usd_change_pct"] > 0 else "外れ"},
    "H3": {"china_2017": s("phones", "中国", 2017), "china_2025": s("phones", "中国", 2025), "verdict": "支持" if s("phones", "中国", 2025) < s("phones", "中国", 2017) else "外れ"},
    "H4": {"share_unit_in_value_pct": c["share_unit_in_value_pct"], "verdict": "支持" if c["share_unit_in_value_pct"] >= 50 else "外れ"},
}
rob = []
for lab, t, y0, y1, fc in [("電話機 2017→2025（本線）", ph, 2017, 2025, "usdjpy_avg"), ("電話機 2017→2021", ph, 2017, 2021, "usdjpy_avg"),
                           ("電話機 2021→2025", ph, 2021, 2025, "usdjpy_avg"), ("電話機 2017→2025（ドル円は12月の値）", ph, 2017, 2025, "usdjpy_dec"),
                           ("電算機類 2017→2025（本線）", pc, 2017, 2025, "usdjpy_avg"), ("電算機類 2000→2025", pc, 2000, 2025, "usdjpy_avg"),
                           ("電話機 中国から 2017→2025", series("中国", "phones"), 2017, 2025, "usdjpy_avg")]:
    q = decompose(t, y0, y1, fc); q["check"] = lab
    rob.append(q)
rb = pd.DataFrame(rob)[["check", "y0", "y1", "value_change_pct", "qty_change_pct", "unit_yen_change_pct", "fx_change_pct", "unit_usd_change_pct",
                        "share_qty_in_value_pct", "share_unit_in_value_pct", "share_fx_in_unit_pct"]]
rb.to_csv(R / "robustness.csv", index=False)
main = {
    "phones": {str(y): {"qty_million": r(ph.qty[y] / 1e6, 2), "value_trillion": r(ph.value_yen[y] / 1e12, 3), "unit_yen": r(ph.unit_yen[y], 0), "unit_usd": r(ph.unit_usd[y], 0)} for y in [2017, 2021, 2025]},
    "computers": {str(y): {"qty_million": r(pc.qty[y] / 1e6, 2), "value_trillion": r(pc.value_yen[y] / 1e12, 3), "unit_yen": r(pc.unit_yen[y], 0), "unit_usd": r(pc.unit_usd[y], 0)} for y in [2000, 2017, 2021, 2025]},
    "usdjpy": {str(y): r(fx.usdjpy_avg[y], 2) for y in [2000, 2017, 2021, 2025]},
    "decomposition": dec,
    "country_shares": {f"{q.item}_{q.area}_{q.year}": q.share_pct for q in sh.itertuples()},
    "hypotheses": hyp,
    "note": "単価＝金額÷数量（電話機・電算機類（含周辺機器）の中の平均）。ドル円は日銀 東京市場17時の月中平均の年平均。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(hyp, ensure_ascii=False)); print(rb.to_string()); print(sh.to_string()); print(json.dumps(main["phones"], ensure_ascii=False), json.dumps(main["computers"], ensure_ascii=False))
