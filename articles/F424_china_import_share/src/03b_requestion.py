"""03b 問い直し：輸入総額に占める中国の割合の変化（2015→2025年）は、品目の中での割合の変化と、
輸入の品目の構成の変化（中国の割合が高い品目の重みが変わる）のどちらで起きたのか（シフト・シェア分解）。
品目は 03 の38品目と「その他」（総額 − 38品目）。
出力：results/requestion.json, results/shift_share.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
import importlib.util

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
spec = importlib.util.spec_from_file_location("a3", ROOT / "src" / "03_analysis.py"); a3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(a3)


def main():
    d = pd.read_csv(D / "imports_long.csv")
    w = d.pivot_table(index=["code", "year"], columns="partner", values="value_thousand_yen", aggfunc="sum")
    rows = []
    for y in (2015, 2025):
        tot = w.loc[(a3.TOTAL, y)]
        leaf = w.loc[[(c, y) for c in a3.LEAF]]
        other = tot - leaf.sum()
        for c in a3.LEAF + ["other"]:
            r = other if c == "other" else w.loc[(c, y)]
            rows.append(dict(code=c, year=y, world=r.world, china=r.china))
    t = pd.DataFrame(rows).pivot(index="code", columns="year")
    wt0 = t[("world", 2015)] / t[("world", 2015)].sum(); wt1 = t[("world", 2025)] / t[("world", 2025)].sum()
    s0 = t[("china", 2015)] / t[("world", 2015)]; s1 = t[("china", 2025)] / t[("world", 2025)]
    within = float(((s1 - s0) * (wt0 + wt1) / 2).sum() * 100)
    between = float(((wt1 - wt0) * (s0 + s1) / 2).sum() * 100)
    total = float(((s1 * wt1).sum() - (s0 * wt0).sum()) * 100)
    out = dict(total_change_pt=total, within_pt=within, composition_pt=between)
    # 燃料の重みの変化
    fuel = [c for c in a3.LEAF if c.startswith("'30") or c.startswith("'3050")]
    out["fuel_weight_2015"] = float(wt0.loc[fuel].sum() * 100); out["fuel_weight_2025"] = float(wt1.loc[fuel].sum() * 100)
    ss = pd.DataFrame({"weight_2015": wt0 * 100, "weight_2025": wt1 * 100, "china_2015": s0 * 100, "china_2025": s1 * 100})
    ss["within_contrib_pt"] = (s1 - s0) * (wt0 + wt1) / 2 * 100
    ss["composition_contrib_pt"] = (wt1 - wt0) * (s0 + s1) / 2 * 100
    ss.round(4).to_csv(R / "shift_share.csv")
    top = ss.within_contrib_pt.sort_values()
    out["largest_negative_within"] = top.index[0]; out["largest_negative_within_pt"] = float(top.iloc[0])
    out["largest_positive_within"] = top.index[-1]; out["largest_positive_within_pt"] = float(top.iloc[-1])
    json.dump({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out); print(ss.sort_values("within_contrib_pt").round(2).head(6)); print(ss.sort_values("within_contrib_pt").round(2).tail(4))


if __name__ == "__main__":
    main()
