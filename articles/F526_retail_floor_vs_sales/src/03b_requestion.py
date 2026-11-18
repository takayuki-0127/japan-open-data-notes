"""問い直し（結果を見てから足した）：全体の1㎡あたり販売額の低下（1991→2007年）は、
各業態の中で下がった分（業態内の効果）と、1㎡あたり販売額の低い業態に売場が移った分（構成の効果）に、どう分けられるか。
売場面積の構成比を重みにする対称な分け方。1991年にない業態（ドラッグストア）は、1991年の値を2007年の値と同じとみなす。"""
import json
import pandas as pd
from common import DATA, RES, GYOTAI_JA

gy = pd.read_csv(DATA / "gyotai_pref.csv")
gn = gy[gy.pref == "全国"].pivot_table(index="year", columns="gyotai", values=["sales_mil_yen", "floor_m2"], aggfunc="first")
S, F = gn["sales_mil_yen"].copy(), gn["floor_m2"].copy()
parts = ["dept", "gms", "sm_cloth", "sm_food", "sm_home", "cvs", "drug", "other_super", "specialty", "center", "other_store"]


def decomp(y0, y1):
    f0 = F.loc[y0, parts].fillna(0); f1 = F.loc[y1, parts].fillna(0)
    e0 = S.loc[y0, parts] * 100 / F.loc[y0, parts]; e1 = S.loc[y1, parts] * 100 / F.loc[y1, parts]
    e0 = e0.fillna(e1); e1 = e1.fillna(e0)
    w0, w1 = f0 / f0.sum(), f1 / f1.sum()
    within = ((e1 - e0) * (w0 + w1) / 2)
    mix = ((w1 - w0) * (e0 + e1) / 2)
    tot0, tot1 = float((w0 * e0).sum()), float((w1 * e1).sum())
    rows = pd.DataFrame({"gyotai": parts, "name": [GYOTAI_JA[g] for g in parts], "share_floor_y0_pct": (w0 * 100).round(2).values,
                         "share_floor_y1_pct": (w1 * 100).round(2).values, "eff_y0": e0.round(2).values, "eff_y1": e1.round(2).values,
                         "within": within.round(3).values, "mix": mix.round(3).values})
    return rows, {"eff_y0": round(tot0, 2), "eff_y1": round(tot1, 2), "diff": round(tot1 - tot0, 2), "within": round(float(within.sum()), 2),
                  "mix": round(float(mix.sum()), 2), "mix_share_pct": round(float(mix.sum()) / (tot1 - tot0) * 100, 1)}


r, q = decomp(1991, 2007)
r.to_csv(RES / "requestion_decomposition.csv", index=False)
q2 = decomp(1997, 2007)[1]
out = {"note": "1㎡あたり販売額（万円/㎡）の変化＝業態内の効果＋構成の効果。業態の和で作る全体の値は、合計の行の比と同じ。",
       "1991_2007": q, "1997_2007": q2,
       "top_within": {g: float(r.set_index("gyotai").loc[g, "within"]) for g in ["dept", "gms", "sm_food", "sm_home", "cvs", "specialty", "center"]},
       "top_mix": {g: float(r.set_index("gyotai").loc[g, "mix"]) for g in ["sm_home", "sm_food", "sm_cloth", "gms", "drug", "center", "specialty"]}}
json.dump(out, open(RES / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=0)); print(r.to_string())
