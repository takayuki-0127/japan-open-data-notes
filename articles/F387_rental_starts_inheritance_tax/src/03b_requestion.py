"""03b 問い直し（結果を見てから足した）：2014〜17年に増えた貸家は、どんな建物だったのか。
2005〜08年（前の山）・2010〜12年（谷）・2014〜17年（見直しの後の山）・2023〜25年の4つの時期で、全国の貸家の着工戸数を
構造（木造・鉄骨造・鉄筋コンクリート系・その他）×建て方（一戸建・長屋建・共同住宅）に分ける。
出力：results/rental_mix.csv, results/requestion.json"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
PER = {"2005-08": [2005, 2006, 2007, 2008], "2010-12": [2010, 2011, 2012], "2014-17": [2014, 2015, 2016, 2017], "2023-25": [2023, 2024, 2025]}
SG = {"木造": "木造", "鉄骨造": "鉄骨造", "鉄骨鉄筋コンクリート造": "鉄筋コンクリート系", "鉄筋コンクリート造": "鉄筋コンクリート系",
      "コンクリートブロック造": "その他", "その他": "その他"}


def main():
    d = pd.read_csv(DATA / "starts_pref.csv")
    r = d[(d.area == "全国") & (d.tenure == "貸家") & (d.struct != "計") & (d.type != "計")].copy()
    r["sg"] = r.struct.map(SG)
    rows = []
    for name, ys in PER.items():
        x = r[r.year.isin(ys)].groupby(["sg", "type"]).units.sum() / len(ys)
        for (sg, ty), v in x.items():
            rows.append({"period": name, "struct": sg, "type": ty, "units": round(v, 1)})
    mix = pd.DataFrame(rows)
    mix.to_csv(RES / "rental_mix.csv", index=False)
    out = {}
    for dim in ["struct", "type"]:
        p = mix.pivot_table(index=dim, columns="period", values="units", aggfunc="sum")
        share = (100 * p / p.sum()).round(1)
        inc = p["2014-17"] - p["2010-12"]
        out[dim] = {k: {"units": {c: round(float(p.loc[k, c])) for c in PER}, "share_pct": {c: float(share.loc[k, c]) for c in PER},
                        "increase_2010_12_to_2014_17": round(float(inc[k])), "share_of_increase_pct": round(float(100 * inc[k] / inc.sum()), 1)}
                    for k in p.index}
    # 木造・鉄骨造の共同住宅＋長屋建（低層のアパートが多い区分、推測）
    low = mix[mix.struct.isin(["木造", "鉄骨造"]) & mix.type.isin(["共同住宅", "長屋建"])].groupby("period").units.sum()
    tot = mix.groupby("period").units.sum()
    out["wood_steel_multi"] = {c: {"units": round(float(low[c])), "share_pct": round(float(100 * low[c] / tot[c]), 1)} for c in PER}
    out["wood_steel_multi"]["share_of_increase_pct"] = round(float(100 * (low["2014-17"] - low["2010-12"]) / (tot["2014-17"] - tot["2010-12"])), 1)
    out["total"] = {c: round(float(tot[c])) for c in PER}
    w = d[(d.area == "全国") & (d.tenure == "貸家") & (d.type == "計") & (d.struct == "木造")].set_index("year").units
    out["wood_rental_peak"] = {"year": int(w.idxmax()), "units": int(w.max()), "first_year": int(w.index.min()),
                               "max_before_2013": int(w.loc[:2012].max()), "max_before_2013_year": int(w.loc[:2012].idxmax()),
                               "units_2017": int(w.loc[2017]), "last_year_above_2017_before": int(w.loc[:2016][w.loc[:2016] > w.loc[2017]].index.max()),
                               "max_2000_2012": int(w.loc[2000:2012].max()), "max_2000_2012_year": int(w.loc[2000:2012].idxmax())}
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
