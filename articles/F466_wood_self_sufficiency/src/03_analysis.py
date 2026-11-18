"""自給率の推移、上昇の分解（用途×国内生産・輸入）、仮説の判定、頑健性。乱数は使わない。"""
import json, pathlib, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, RES, W, DCOLS, MCOLS, LAB, ss, run

# 自給率の推移
s_tot = 100 * W[DCOLS].sum(1) / (W[DCOLS].sum(1) + W[MCOLS].sum(1))
s_you = 100 * W[[c for c in DCOLS if c not in ("dom_shiitake", "dom_nenryo")]].sum(1) / (W[["dom_seizai", "dom_gouhan", "dom_pulp", "dom_sonota"]].sum(1) + W[["imp_seizai", "imp_gouhan", "imp_pulp", "imp_sonota"]].sum(1))
ser = pd.DataFrame({"ss_total": s_tot.round(3), "ss_total_pub": W.ss_total_pub, "ss_youzai_pub": W.ss_youzai_pub,
                    "dom_total": W.dom_total, "imp_total": W.imp_total, "total": W.total,
                    "dom_youzai": W.dom_youzai, "dom_nenryo": W.dom_nenryo, "imp_youzai": W.imp_youzai, "imp_nenryo": W.imp_nenryo})
for k in LAB:
    if f"dom_{k}" in W: ser[f"dom_{k}"] = W[f"dom_{k}"]
    if f"imp_{k}" in W: ser[f"imp_{k}"] = W[f"imp_{k}"]
ser.to_csv(RES / "national_series.csv")
post = W.loc[1990:]
y_min = int(post.ss_total_pub.idxmin())
END = int(W.index.max())

main = run(y_min, END)
dec_rows = []
for c in DCOLS + MCOLS:
    side, k = c.split("_")
    dec_rows.append({"side": "国内生産" if side == "dom" else "輸入", "use": LAB[k],
                     "vol_from": W.loc[y_min, c], "vol_to": W.loc[END, c], "contrib_pt": round(main[c], 4)})
dec = pd.DataFrame(dec_rows)
dec.to_csv(RES / f"decomp_{y_min}_{END}.csv", index=False)

# 燃料材の寄与（国内＋輸入）
fuel = main["dom_nenryo"] + main["imp_nenryo"]
you_dom = {k: main[f"dom_{k}"] for k in ["seizai", "gouhan", "pulp", "sonota"]}
imp_k = {k: main[f"imp_{k}"] for k in ["seizai", "gouhan", "pulp", "sonota", "nenryo"]}
hyp = {
    "H1": {"dom": main["dom_contrib"], "imp": main["imp_contrib"], "verdict": "支持" if main["dom_contrib"] > main["imp_contrib"] else "外れ"},
    "H2": {"fuel": fuel, "share": fuel / main["change"], "verdict": "支持" if fuel / main["change"] >= 1 / 3 else "外れ"},
    "H3": {"by_use": you_dom, "top": LAB[max(you_dom, key=you_dom.get)], "verdict": "支持" if max(you_dom, key=you_dom.get) == "gouhan" else "外れ"},
    "H4": {"by_use": imp_k, "top": LAB[max(imp_k, key=imp_k.get)], "verdict": "支持" if max(imp_k, key=imp_k.get) == "seizai" else "外れ"},
}

# 頑健性
rob = []
def add(name, r, note=""):
    fuel_r = r.get("dom_nenryo", 0) + r.get("imp_nenryo", 0)
    rob.append({"check": name, "from": r["from"], "to": r["to"], "ss_from": round(r["ss_from"], 2), "ss_to": round(r["ss_to"], 2),
                "change": round(r["change"], 2), "dom": round(r["dom_contrib"], 2), "imp": round(r["imp_contrib"], 2),
                "fuel": round(fuel_r, 2), "dom_gouhan": round(r["dom_gouhan"], 2), "imp_seizai": round(r["imp_seizai"], 2),
                "imp_pulp": round(r["imp_pulp"], 2), "resid": r["resid"], "note": note})
add("本計算", main)
add("起点2000年", run(2000, END))
add("起点2010年", run(2010, END))
add("燃料材を除く（用材＋しいたけ原木）", run(y_min, END, [c for c in DCOLS if c != "dom_nenryo"], [c for c in MCOLS if c != "imp_nenryo"]))
add("3年平均（前後1年）", run(y_min, END, avg=1), "終点は2023〜2024年の平均")
robdf = pd.DataFrame(rob)
robdf.to_csv(RES / "robustness.csv", index=False)

# 数字（本文用）
def r1(x): return round(float(x), 1)
M = {
    "y_min": y_min, "end": END,
    "ss_min": float(W.loc[y_min, "ss_total_pub"]), "ss_end": float(W.loc[END, "ss_total_pub"]),
    "ss_youzai_min": float(W.loc[y_min, "ss_youzai_pub"]), "ss_youzai_end": float(W.loc[END, "ss_youzai_pub"]),
    "ss_max_after_min": float(W.loc[y_min:, "ss_total_pub"].max()), "ss_max_year": int(W.loc[y_min:, "ss_total_pub"].idxmax()),
    "ss_1955": float(W.loc[1955, "ss_total_pub"]),
    "change_pt": round(main["change"], 3), "dom_contrib_pt": round(main["dom_contrib"], 3), "imp_contrib_pt": round(main["imp_contrib"], 3),
    "resid_pt": main["resid"], "shapley_dom_pt": round(main["shapley_dom"], 3), "shapley_imp_pt": round(main["shapley_imp"], 3),
    "fuel_contrib_pt": round(fuel, 3), "fuel_share": round(fuel / main["change"], 4),
    "vol": {c: {"from": float(W.loc[y_min, c]), "to": float(W.loc[END, c])} for c in DCOLS + MCOLS + ["dom_total", "imp_total", "total", "dom_youzai", "imp_youzai", "imp_maruta", "imp_prod_total"]},
    "contrib": {c: round(main[c], 3) for c in DCOLS + MCOLS},
    "hypotheses": hyp,
    "robustness": rob,
}
json.dump(M, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: M[k] for k in ["y_min", "ss_min", "ss_end", "change_pt", "dom_contrib_pt", "imp_contrib_pt", "resid_pt", "shapley_dom_pt", "fuel_contrib_pt", "fuel_share", "ss_max_year", "ss_max_after_min"]}, ensure_ascii=False))
print(dec)
print(robdf.drop(columns="note"))
print({h: v["verdict"] for h, v in hyp.items()})
