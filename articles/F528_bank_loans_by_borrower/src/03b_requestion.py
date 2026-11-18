"""問い直し：不動産業向けの増加は、中小企業・中堅企業・大企業のどこに向かったのか（オフライン）。"""
import json, pathlib, importlib.util
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_analysis.py"); a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
LAB = {"sme": "中小企業", "mid": "中堅企業", "large": "大企業"}

def main():
    long = pd.read_csv(ROOT / "data" / "loans_long.csv")
    last = a.wide(long, "bank").index[-1]
    allw = a.wide(long, "bank")
    rows = []
    for k in ("sme", "mid", "large"):
        w = a.wide(long, "bank", k)
        for sec in ("不動産業", "不動産流動化等を目的とするSPC", "個人による貸家業"):
            if sec not in w: continue
            for q in ("2009Q2", "2013Q1", "2019Q4", last):
                rows.append({"size": k, "label": LAB[k], "sector": sec, "quarter": q, "oku_yen": float(w.loc[q, sec])})
    t = pd.DataFrame(rows); t.to_csv(ROOT / "results" / "requestion_realestate_by_size.csv", index=False)
    re = t[t.sector == "不動産業"].pivot(index="quarter", columns="size", values="oku_yen")
    re["sum3"] = re[["sme", "mid", "large"]].sum(axis=1)
    re["all"] = allw.loc[re.index, "不動産業"]
    inc = re.loc[last] - re.loc["2013Q1"]
    out = {"re_level_tn": {q: {c: round(float(re.loc[q, c]) / 1e4, 2) for c in re.columns} for q in re.index},
           "re_increase_share_2013": {c: round(float(inc[c] / inc["sum3"]) * 100, 1) for c in ("sme", "mid", "large")},
           "re_increase_tn_2013": round(float(inc["sum3"]) / 1e4, 2),
           "sum3_vs_all_gap_pct_last": round(float((re.loc[last, "sum3"] - re.loc[last, "all"]) / re.loc[last, "all"]) * 100, 3)}
    sme = t[t["size"] == "sme"].pivot(index="quarter", columns="sector", values="oku_yen")
    d = sme.loc[last] - sme.loc["2013Q1"]
    out["sme_re_increase_tn_2013"] = {"SPC": round(float(d["不動産流動化等を目的とするSPC"]) / 1e4, 2), "個人による貸家業": round(float(d["個人による貸家業"]) / 1e4, 2),
                                      "その他": round(float(d["不動産業"] - d["不動産流動化等を目的とするSPC"] - d["個人による貸家業"]) / 1e4, 2)}
    out["large_re_increase_tn_2013"] = round(float(inc["large"]) / 1e4, 2)
    out["mid_re_increase_tn_2013"] = round(float(inc["mid"]) / 1e4, 2)
    hr = t[(t.sector == "個人による貸家業")].groupby(["size", "quarter"]).oku_yen.sum().unstack()
    out["hr_by_size_last_tn"] = {k: round(float(hr.loc[k, last]) / 1e4, 2) for k in hr.index}
    m = json.loads((ROOT / "results" / "main.json").read_text(encoding="utf-8"))
    m["requestion"] = out
    (ROOT / "results" / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))

if __name__ == "__main__":
    main()
