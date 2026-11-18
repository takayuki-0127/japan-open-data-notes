"""問い直し：利下げのときは、利上げのときより速く・大きく動くのか（オフライン）。"""
import json, pathlib, importlib.util
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_analysis.py"); a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)

def main():
    df = a.load()
    # 預金金利の自由化（1994年10月に完了）の前後の動きを除くため、1995年から
    cut, evs = a.event_table(df, sign=-1, start="199501", end="200912")
    cut.to_csv(ROOT / "results" / "events_cuts.csv", index=False)
    hike = pd.read_csv(ROOT / "results" / "events_hikes.csv", dtype={"event": str})
    rows = []
    for kind, t in (("利上げ", hike), ("利下げ", cut)):
        for c in a.DEP:
            s = t[t.series == c]
            if len(s) == 0: continue
            rows.append({"kind": kind, "series": c, "label": a.LABEL[c], "n_events": int(s.ratio_h3.notna().sum()), "n_h1": int(s.ratio_h1.notna().sum()),
                         "ratio_h1_mean": round(float(s.ratio_h1.mean()), 3), "ratio_h3_mean": round(float(s.ratio_h3.mean()), 3),
                         "lag_median": float(s.lag_months.median()) if s.lag_months.notna().any() else None})
    comp = pd.DataFrame(rows); comp.to_csv(ROOT / "results" / "requestion_hike_vs_cut.csv", index=False)
    # 利下げの出来事のうち、預金金利の出発点が0.1%以上だったもの（下限に当たりにくいもの）だけ
    hi = cut[cut.base >= 0.1]
    hi_comp = hi.groupby("series").ratio_h3.mean().round(3).to_dict()
    # レビューで追加：利下げ（週次の月内平均）と測り方がそろう、2022年3月までの利上げだけ
    hw = hike[hike.event < "202204"]
    hike_weekly = {c: {"h1": round(float(hw[hw.series == c].ratio_h1.mean()), 3), "h3": round(float(hw[hw.series == c].ratio_h3.mean()), 3),
                       "n": int(hw[hw.series == c].ratio_h3.notna().sum())} for c in a.DEP}
    out = {"hike_weekly_only": hike_weekly, "cut_events": [{"start": e["start"], "size": round(e["size"], 3)} for e in evs],
           "hike_vs_cut": {f"{r.kind}|{r.series}": {"h1": r.ratio_h1_mean, "h3": r.ratio_h3_mean, "lag_median": r.lag_median, "n": r.n_events} for r in comp.itertuples()},
           "cut_h3_base_ge_0.1": hi_comp}
    m = json.loads((ROOT / "results" / "main.json").read_text(encoding="utf-8"))
    m["requestion"] = out
    (ROOT / "results" / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(comp.to_string()); print(out["cut_events"]); print(hi_comp)

if __name__ == "__main__":
    main()
