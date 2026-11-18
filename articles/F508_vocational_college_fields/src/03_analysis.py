"""分野別の人数・割合・指数・18歳人口あたり、仮説の判定、頑健性。"""
import json
import pandas as pd
from common import DATA, RES, YEARS, SHOWN, NAME

RES.mkdir(exist_ok=True)
fb = pd.read_csv(DATA / "fields_by_year.csv")
en = pd.read_csv(DATA / "entry_rate.csv").set_index("year")


def tab(course):
    t = fb[fb.course == course].pivot(index="year", columns="field", values="students")
    t["six"] = t[SHOWN].sum(axis=1)
    t["other2"] = t["total"] - t["six"]
    return t


S, A = tab("senmon"), tab("all")
coh = en.cohort18.reindex(YEARS)
rows = []
for y in YEARS:
    for f in SHOWN + ["six", "other2", "total"]:
        rows.append({"year": y, "field": f, "students": int(S.loc[y, f]), "share_of_total_pct": round(S.loc[y, f] / S.loc[y, "total"] * 100, 2),
                     "index_1985": round(S.loc[y, f] / S.loc[1985, f] * 100, 1), "per_1000_cohort18": round(S.loc[y, f] / coh[y] * 1000, 2)})
by = pd.DataFrame(rows)
by.to_csv(RES / "by_year.csv", index=False)

pct = lambda a, b: round((b / a - 1) * 100, 1)
m = {"note": "専修学校の専門課程の生徒数（各年度5月1日）。six は取り上げる6分野の和、other2 は取り上げない2分野（合計との差）。",
     "names": {f: NAME[f] for f in SHOWN}}
m["students"] = {f: {y: int(S.loc[y, f]) for y in YEARS} for f in SHOWN + ["six", "other2", "total"]}
m["change_1985_2025_pct"] = {f: pct(S.loc[1985, f], S.loc[2025, f]) for f in SHOWN + ["six", "other2", "total"]}
m["change_1995_2025_pct"] = {f: pct(S.loc[1995, f], S.loc[2025, f]) for f in SHOWN + ["six", "total"]}
m["change_2010_2025_pct"] = {f: pct(S.loc[2010, f], S.loc[2025, f]) for f in SHOWN + ["six", "total"]}
m["peak"] = {f: {"year": int(S[f].idxmax()), "students": int(S[f].max()), "2025_vs_peak_pct": pct(S[f].max(), S.loc[2025, f])} for f in SHOWN + ["six", "total"]}
m["share_pct"] = {f: {y: round(S.loc[y, f] / S.loc[y, "total"] * 100, 1) for y in YEARS} for f in SHOWN + ["six", "other2"]}
m["share_of_six_pct"] = {f: {y: round(S.loc[y, f] / S.loc[y, "six"] * 100, 1) for y in YEARS} for f in SHOWN}
m["per_1000_cohort18"] = {f: {y: round(S.loc[y, f] / coh[y] * 1000, 1) for y in YEARS} for f in SHOWN + ["six", "total"]}
m["cohort18"] = {y: int(coh[y]) for y in YEARS}
m["cohort18_change_1995_2025_pct"] = pct(coh[1995], coh[2025])
m["senmon_entry_rate"] = {int(y): float(en.loc[y, "senmon_rate"]) for y in en.index if y >= 1985}
m["univ_entry_rate"] = {int(y): float(en.loc[y, "univ_rate"]) for y in en.index if y >= 1985}
m["entry_rate_peak"] = {"year": int(en.loc[en.index >= 1976, "senmon_rate"].idxmax()), "rate": float(en.senmon_rate.max())}
m["entrants"] = {int(y): int(en.loc[y, "senmon_entrants"]) for y in (1985, 1995, 2025)}
largest_2025 = max(SHOWN, key=lambda f: S.loc[2025, f])
fastest = max(SHOWN, key=lambda f: S.loc[2025, f] / S.loc[1985, f])
fastest_wo_nogyo = max([f for f in SHOWN if f != "nogyo"], key=lambda f: S.loc[2025, f] / S.loc[1985, f])
steepest_fall = min(SHOWN, key=lambda f: S.loc[2025, f] / S.loc[1985, f])
m["largest_of_six_2025"] = largest_2025
m["largest_of_six_by_year"] = {y: max(SHOWN, key=lambda f: S.loc[y, f]) for y in YEARS}
m["fastest_growth_1985_2025"] = fastest
m["fastest_growth_excl_nogyo"] = fastest_wo_nogyo
m["steepest_fall_1985_2025"] = steepest_fall

c = m["change_1985_2025_pct"]
H = {"H1": {"text": "6分野のうち減少率が最大は服飾・家政で、半分以下に減った", "value": {"kasei": c["kasei"], "steepest": steepest_fall},
            "verdict": "支持" if steepest_fall == "kasei" and c["kasei"] <= -50 else "外れ"},
     "H2": {"text": "6分野のうち増加率が最大は文化・教養で、2025年度に6分野で最も多い",
            "value": {"fastest": fastest, "fastest_rate": c[fastest], "bunka": c["bunka"], "largest_2025": largest_2025},
            "verdict": "支持" if fastest == "bunka" and largest_2025 == "bunka" else ("外れ" if fastest != "bunka" and largest_2025 != "bunka" else "一部外れ")},
     "H3": {"text": "工業の山は1990年代で、2025年度は山より30%以上少ない", "value": m["peak"]["kogyo"],
            "verdict": "支持" if 1990 <= m["peak"]["kogyo"]["year"] <= 1999 and m["peak"]["kogyo"]["2025_vs_peak_pct"] <= -30 else "外れ"},
     "H4": {"text": "専門課程への進学率は2025年が1995年より高い", "value": {1995: m["senmon_entry_rate"][1995], 2025: m["senmon_entry_rate"][2025]},
            "verdict": "支持" if m["senmon_entry_rate"][2025] > m["senmon_entry_rate"][1995] else "外れ"}}
m["hypotheses"] = H

# ---- 頑健性 ----
rob = []
for f in SHOWN:
    rob.append({"field": f, "name": NAME[f], "senmon_1985_2025": c[f], "senmon_1995_2025": m["change_1995_2025_pct"][f],
                "senmon_2010_2025": m["change_2010_2025_pct"][f], "all_courses_1985_2025": pct(A.loc[1985, f], A.loc[2025, f]),
                "per_1000_cohort_1985_2025": pct(S.loc[1985, f] / coh[1985], S.loc[2025, f] / coh[2025])})
rb = pd.DataFrame(rob)
rb.to_csv(RES / "robustness.csv", index=False)
m["robustness"] = rob
m["robust_sign_same"] = {r["field"]: len({x > 0 for x in (r["senmon_1985_2025"], r["all_courses_1985_2025"], r["per_1000_cohort_1985_2025"])}) == 1 for r in rob}
m["all_courses_largest_2025"] = max(SHOWN, key=lambda f: A.loc[2025, f])
m["all_courses_steepest_fall"] = min(SHOWN, key=lambda f: A.loc[2025, f] / A.loc[1985, f])
json.dump(m, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: m[k] for k in ["students", "change_1985_2025_pct", "peak", "share_pct", "per_1000_cohort18", "senmon_entry_rate", "hypotheses", "largest_of_six_by_year", "robust_sign_same", "cohort18"]}, ensure_ascii=False))
print(rb.to_string())
