"""割合・増減の分解・1戸あたり・輸入・頑健性。数字はすべて results に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
S = pd.read_csv(D / "shiitake_national.csv").set_index("year")
P = pd.read_csv(D / "producers_national.csv").set_index("year")
K = pd.read_csv(D / "kinoko_national.csv").set_index("year")
B = pd.read_csv(D / "balance_shiitake.csv")
L = pd.read_csv(D / "logs_beds.csv").set_index("year")


def r(v, n=1):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), n)


# ---- 年ごとの表 ----
A = pd.DataFrame(index=S.index)
A["fresh_total"] = S.fresh_total; A["fresh_log"] = S.fresh_log; A["fresh_bed"] = S.fresh_bed
A["log_share_fresh_pct"] = S.fresh_log / S.fresh_total * 100
A["dry_total"] = S.dry_total; A["dry_log"] = S.dry_log; A["dry_bed"] = S.dry_bed
A["dry_log_share_pct"] = S.dry_log / S.dry_total * 100
A["kinoko_total"] = K["きのこ類総計"]
A["shiitake_fresh_equiv"] = K["生しいたけ"] + K["乾しいたけ_生換算"]
A["shiitake_share_pct"] = A.shiitake_fresh_equiv / A.kinoko_total * 100
for it in ["えのきたけ", "ぶなしめじ", "まいたけ", "エリンギ", "なめこ", "ひらたけ"]:
    A[f"share_{it}_pct"] = K[it] / A.kinoko_total * 100
A["dry_to_fresh_ratio"] = K["乾しいたけ_生換算"] / K["乾しいたけ"]
A["prod_log_total"] = P.log_total; A["prod_log_dry"] = P.log_dry; A["prod_log_fresh"] = P.log_fresh
A["prod_bed"] = P.bed_total; A["prod_total"] = P.total
A["t_per_log_fresh_producer"] = S.fresh_log / P.log_fresh
A["t_per_bed_producer"] = S.fresh_bed / P.bed_total
A["t_per_log_dry_producer"] = S.dry_log / P.log_dry
for it in ("生しいたけ", "乾しいたけ"):
    b = B[B.item == it].set_index("year")
    k = "fresh" if it == "生しいたけ" else "dry"
    A[f"{k}_imports"] = b.imports
    A[f"{k}_domestic_share_pct"] = b.production / b.consumption * 100
    A[f"{k}_balance_production"] = b.production
A["logs_total_thousand"] = L.logs_total_thousand.reindex(A.index)
A["logs_fresh_thousand"] = L.logs_fresh_thousand.reindex(A.index)
A["beds_thousand"] = L.beds_thousand.reindex(A.index)
A = A.reset_index()
A.round(3).to_csv(R / "annual_national.csv", index=False)
a = A.set_index("year")

# ---- 品目別（2005年と2025年） ----
items = ["生しいたけ", "乾しいたけ_生換算", "えのきたけ", "ぶなしめじ", "まいたけ", "エリンギ", "なめこ", "ひらたけ"]
it_rows = []
for it in items:
    v05, v25 = K.loc[2005, it], K.loc[2025, it]
    it_rows.append({"item": it, "t_2005": v05, "t_2025": v25, "change_t": v25 - v05, "change_pct": (v25 / v05 - 1) * 100,
                    "share_2005_pct": v05 / K.loc[2005, "きのこ類総計"] * 100, "share_2025_pct": v25 / K.loc[2025, "きのこ類総計"] * 100,
                    "peak_year": int(K[it].idxmax()), "peak_t": K[it].max()})
IT = pd.DataFrame(it_rows); IT.round(2).to_csv(R / "items_2005_2025.csv", index=False)

# ---- 生しいたけの増減を原木・菌床に分ける ----
dec = []
for a0, a1 in [(2005, 2025), (2005, 2010), (2010, 2021), (2021, 2025)]:
    dec.append({"from": a0, "to": a1, "fresh_change": S.loc[a1, "fresh_total"] - S.loc[a0, "fresh_total"],
                "log_change": S.loc[a1, "fresh_log"] - S.loc[a0, "fresh_log"], "bed_change": S.loc[a1, "fresh_bed"] - S.loc[a0, "fresh_bed"]})
DEC = pd.DataFrame(dec); DEC.round(1).to_csv(R / "fresh_decomposition.csv", index=False)

# ---- 照合：生しいたけの生産量（3つの表） ----
chk = pd.DataFrame({"shiitake_table": S.fresh_total, "kinoko_table": K["生しいたけ"],
                    "balance_table": B[B.item == "生しいたけ"].set_index("year").production})
chk["max_abs_diff"] = chk.max(axis=1) - chk.min(axis=1)
chk.reset_index().round(1).to_csv(R / "check_fresh_three_tables.csv", index=False)
chkd = pd.DataFrame({"shiitake_table": S.dry_total, "kinoko_table": K["乾しいたけ"],
                     "balance_table": B[B.item == "乾しいたけ"].set_index("year").production})
dry_diff = float((chkd.max(axis=1) - chkd.min(axis=1)).max())

# ---- 仮説 ----
ls05, ls25 = a.loc[2005, "log_share_fresh_pct"], a.loc[2025, "log_share_fresh_pct"]
pl13, pl23 = P.loc[2013, "log_total"], P.loc[2023, "log_total"]
sh05, sh25 = a.loc[2005, "shiitake_share_pct"], a.loc[2025, "shiitake_share_pct"]
bed_peak_y = int(S.fresh_bed.idxmax()); bed_peak = S.fresh_bed.max(); bed25 = S.loc[2025, "fresh_bed"]
H = {
    "H1": {"rule": "生しいたけに占める原木の割合が2005→2025年に20ポイント以上下がれば支持",
           "share_2005": r(ls05, 1), "share_2025": r(ls25, 1), "drop_pt": r(ls05 - ls25, 1),
           "judge": "支持" if ls05 - ls25 >= 20 else "外れ"},
    "H2": {"rule": "原木しいたけ生産者（乾・生の計）が2013→2023年に45%以上減れば支持",
           "n_2013": int(pl13), "n_2023": int(pl23), "change_pct": r((pl23 / pl13 - 1) * 100, 1),
           "judge": "支持" if pl23 / pl13 - 1 <= -0.45 else "外れ"},
    "H3": {"rule": "きのこ類総計に占めるしいたけ（生＋乾の生換算）が2005→2025年に3ポイント以上下がれば支持",
           "share_2005": r(sh05, 1), "share_2025": r(sh25, 1), "drop_pt": r(sh05 - sh25, 1),
           "judge": "支持" if sh05 - sh25 >= 3 else "外れ"},
    "H4": {"rule": "菌床の生しいたけが2025>2005、山が2025年より前、山から2025年に5%以上減なら支持",
           "bed_2005": r(S.loc[2005, "fresh_bed"]), "bed_2025": r(bed25), "peak_year": bed_peak_y, "peak": r(bed_peak),
           "from_peak_pct": r((bed25 / bed_peak - 1) * 100, 1),
           "judge": "支持" if (bed25 > S.loc[2005, "fresh_bed"] and bed_peak_y < 2025 and bed25 / bed_peak - 1 <= -0.05) else "外れ"},
}

# ---- 頑健性 ----
def avg(col, ys, src=a):
    return float(src.loc[list(ys), col].mean())
rob = []
rob.append(("H1 端を3年平均（2005〜07→2023〜25）", "原木の割合 %",
            f"{avg('log_share_fresh_pct', range(2005, 2008)):.1f} → {avg('log_share_fresh_pct', range(2023, 2026)):.1f}"))
rob.append(("H3 端を3年平均", "しいたけの割合 %",
            f"{avg('shiitake_share_pct', range(2005, 2008)):.1f} → {avg('shiitake_share_pct', range(2023, 2026)):.1f}"))
rob.append(("H3 乾を生に換算せず、生しいたけだけで見る", "生しいたけ÷きのこ類総計 %",
            f"{K.loc[2005, '生しいたけ'] / K.loc[2005, 'きのこ類総計'] * 100:.1f} → {K.loc[2025, '生しいたけ'] / K.loc[2025, 'きのこ類総計'] * 100:.1f}"))
rob.append(("生しいたけ：3つの表の差（2005〜2025年の最大）", "トン", f"{chk.max_abs_diff.max():.1f}"))
rob.append(("乾しいたけ：3つの表の差（2005〜2025年の最大）", "トン", f"{dry_diff:.1f}"))
step = (P.loc[2010, "log_total"] / P.loc[2009, "log_total"] - 1) * 100
rob.append(("生産者数の段差 2009→2010年（数え方の注が付いた年）", "原木の戸数 %", f"{step:.1f}"))
y5 = (P.loc[2015, "log_total"] / P.loc[2010, "log_total"] - 1) * 100
rob.append(("比べ：2010→2015年の5年の変化", "原木の戸数 %", f"{y5:.1f}"))
rob.append(("H2 期間を2015→2025年にする", "原木の戸数 %", f"{(P.loc[2025, 'log_total'] / P.loc[2015, 'log_total'] - 1) * 100:.1f}"))
rob.append(("H2 期間を2010→2020年にする", "原木の戸数 %", f"{(P.loc[2020, 'log_total'] / P.loc[2010, 'log_total'] - 1) * 100:.1f}"))
# レビューで追加：2020→2021年にも注の変更なしで大きな1年の段差がある。その1年を除いた2013→2023年の変化
step21 = (P.loc[2021, "log_total"] / P.loc[2020, "log_total"] - 1) * 100
rob.append(("生産者数の段差 2020→2021年（表に注の変更なし）", "原木の戸数 %", f"{step21:.1f}"))
ex21 = (P.loc[2020, "log_total"] / P.loc[2013, "log_total"] * P.loc[2023, "log_total"] / P.loc[2021, "log_total"] - 1) * 100
rob.append(("H2 2013→2023年から2020→2021年の1年を除く", "原木の戸数 %", f"{ex21:.1f}"))
rob.append(("H4 菌床の山を3年平均で見る", "山の3年（中心）",
            str(int(S.fresh_bed.rolling(3, center=True).mean().idxmax()))))
ROB = pd.DataFrame(rob, columns=["check", "unit", "value"]); ROB.to_csv(R / "robustness.csv", index=False)

main = {
    "hypotheses": H,
    "fresh": {y: {"total": r(S.loc[y, "fresh_total"]), "log": r(S.loc[y, "fresh_log"]), "bed": r(S.loc[y, "fresh_bed"]),
                  "log_share_pct": r(a.loc[y, "log_share_fresh_pct"], 1)} for y in (2005, 2010, 2015, 2020, 2021, 2025)},
    "fresh_peak": {"year": int(S.fresh_total.idxmax()), "t": r(S.fresh_total.max())},
    "fresh_log_change_2005_2025_pct": r((S.loc[2025, "fresh_log"] / S.loc[2005, "fresh_log"] - 1) * 100, 1),
    "fresh_decomposition": DEC.round(1).to_dict(orient="records"),
    "dry": {y: {"total": r(S.loc[y, "dry_total"]), "log_share_pct": r(a.loc[y, "dry_log_share_pct"], 1)} for y in (2005, 2010, 2015, 2020, 2025)},
    "dry_change_2005_2025_pct": r((S.loc[2025, "dry_total"] / S.loc[2005, "dry_total"] - 1) * 100, 1),
    "imports": {y: {"fresh_imports": r(a.loc[y, "fresh_imports"], 0), "fresh_domestic_share_pct": r(a.loc[y, "fresh_domestic_share_pct"], 1),
                    "dry_imports": r(a.loc[y, "dry_imports"], 0), "dry_domestic_share_pct": r(a.loc[y, "dry_domestic_share_pct"], 1)}
                for y in (2005, 2010, 2015, 2020, 2025)},
    "kinoko_total": {y: r(K.loc[y, "きのこ類総計"]) for y in (2005, 2010, 2011, 2015, 2020, 2025)},
    "kinoko_peak": {"year": int(K["きのこ類総計"].idxmax()), "t": r(K["きのこ類総計"].max())},
    "shiitake_share_pct": {y: r(a.loc[y, "shiitake_share_pct"], 1) for y in (2005, 2010, 2015, 2020, 2025)},
    "items": IT.round(1).to_dict(orient="records"),
    "producers": {y: {k: int(P.loc[y, k]) for k in P.columns} for y in (2005, 2009, 2010, 2013, 2015, 2020, 2023, 2025)},
    "per_producer_t": {y: {"log_fresh": r(a.loc[y, "t_per_log_fresh_producer"], 2), "bed": r(a.loc[y, "t_per_bed_producer"], 2),
                           "log_dry": r(a.loc[y, "t_per_log_dry_producer"], 3)} for y in (2010, 2015, 2020, 2025)},
    "logs": {y: r(L.loc[y, "logs_total_thousand"], 0) for y in (1970, 1985, 2005, 2010, 2015, 2020, 2025)},
    "logs_peak": {"year": int(L.logs_total_thousand.idxmax()), "thousand": r(L.logs_total_thousand.max(), 0)},
    "beds": {y: r(L.loc[y, "beds_thousand"], 0) for y in (1993, 2005, 2010, 2015, 2020, 2022)},
    "dry_to_fresh_ratio": {"min": r(A.dry_to_fresh_ratio.min(), 2), "max": r(A.dry_to_fresh_ratio.max(), 2)},
    "producers_change_pct": {f"{c}_{a0}_{a1}": r((P.loc[a1, c] / P.loc[a0, c] - 1) * 100, 1)
                             for c in ("log_total", "log_dry", "log_fresh", "bed_total", "total") for a0, a1 in ((2013, 2023), (2010, 2025))},
    "robustness": {x.check: x.value for x in ROB.itertuples()},
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(H, ensure_ascii=False, indent=1)); print(ROB.to_string()); print(IT.round(1).to_string()); print(DEC)
print(A[["year", "log_share_fresh_pct", "shiitake_share_pct", "t_per_log_fresh_producer", "t_per_bed_producer", "fresh_domestic_share_pct", "dry_domestic_share_pct"]].round(1).to_string())
