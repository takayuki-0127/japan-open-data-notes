"""主な分析：1992年を100とした指数、入学者の変化の分解、大学＋短大の合計、設置者別、仮説の判定、頑健性。"""
import json
import pandas as pd
from common import ROOT

R = ROOT / "results"; R.mkdir(exist_ok=True)
p = pd.read_csv(ROOT / "data" / "panel.csv", index_col="year")
B, E = 1992, 2025


def decompose(ent, pop, y0, y1):
    """入学者 = 人口 × 率。変化 = 人口の効果 + 率の効果（2つの年の平均を重みにする対称な形）。"""
    r0, r1 = ent[y0] / pop[y0], ent[y1] / pop[y1]
    pe = (pop[y1] - pop[y0]) * (r0 + r1) / 2
    re_ = (r1 - r0) * (pop[y0] + pop[y1]) / 2
    return {"y0": y0, "y1": y1, "ent0": int(ent[y0]), "ent1": int(ent[y1]), "change": int(ent[y1] - ent[y0]),
            "pop0": int(pop[y0]), "pop1": int(pop[y1]), "rate0_pct": round(100 * r0, 2), "rate1_pct": round(100 * r1, 2),
            "pop_effect": round(pe), "rate_effect": round(re_)}


def pct(a, b):
    return round(100 * (b / a - 1), 1)


m = {"base_year": B, "end_year": E}
m["pop18"] = {str(B): int(p.pop18[B]), str(E): int(p.pop18[E]), "change_pct": pct(p.pop18[B], p.pop18[E]),
              "peak_year": int(p.pop18.loc[1980:2025].idxmax())}
m["univ"] = {str(B): int(p.univ_total[B]), str(E): int(p.univ_total[E]), "change_pct": pct(p.univ_total[B], p.univ_total[E]),
             "max_year": int(p.univ_total.loc[1980:2025].idxmax()), "max_n": int(p.univ_total.loc[1980:2025].max())}
m["jc"] = {str(B): int(p.jc_total[B]), str(E): int(p.jc_total[E]), "change_pct": pct(p.jc_total[B], p.jc_total[E]),
           "max_year": int(p.jc_total.loc[1980:2025].idxmax()), "max_n": int(p.jc_total.loc[1980:2025].max())}
both = p.univ_total + p.jc_total
m["univ_plus_jc"] = {str(B): int(both[B]), str(E): int(both[E]), "change_pct": pct(both[B], both[E]),
                     "max_year": int(both.loc[1980:2025].idxmax()), "max_n": int(both.loc[1980:2025].max())}
m["ent_univ"] = {str(B): int(p.ent_univ[B]), str(E): int(p.ent_univ[E]), "change_pct": pct(p.ent_univ[B], p.ent_univ[E]),
                 "max_year": int(p.ent_univ.loc[1980:2025].idxmax()), "max_n": int(p.ent_univ.loc[1980:2025].max())}
m["ent_jc"] = {str(B): int(p.ent_jc[B]), str(E): int(p.ent_jc[E]), "change_pct": pct(p.ent_jc[B], p.ent_jc[E]),
               "max_year": int(p.ent_jc.loc[1980:2025].idxmax())}
entb = p.ent_univ + p.ent_jc
m["ent_both"] = {str(B): int(entb[B]), str(E): int(entb[E]), "change_pct": pct(entb[B], entb[E]),
                 "max_year": int(entb.loc[1980:2025].idxmax()), "max_n": int(entb.loc[1980:2025].max())}
m["rate_univ_tab"] = {str(B): float(p.rate_univ_tab[B]), str(E): float(p.rate_univ_tab[E])}
m["rate_jc_tab"] = {str(B): float(p.rate_jc_tab[B]), str(E): float(p.rate_jc_tab[E])}
m["decomp_univ"] = decompose(p.ent_univ, p.pop18, B, E)
m["decomp_both"] = decompose(entb, p.pop18, B, E)
# 2025年の学校数の前年差
m["univ_2024_2025"] = {"2024": int(p.univ_total[2024]), "2025": int(p.univ_total[2025])}

# 設置者別
setter = []
for s, lab in [("national", "国立"), ("public", "公立"), ("private", "私立")]:
    for kind, pre in [("大学", "univ"), ("短期大学", "jc")]:
        a, b = p[f"{pre}_{s}"][B], p[f"{pre}_{s}"][E]
        sa, sb = p[f"{pre}_students_{s}"][B], p[f"{pre}_students_{s}"][E]
        setter.append({"kind": kind, "setter": lab, f"schools_{B}": int(a), f"schools_{E}": int(b),
                       "schools_ratio": round(b / a, 3) if a else None, "schools_diff": int(b - a),
                       f"students_{B}": int(sa), f"students_{E}": int(sb), "students_change_pct": pct(sa, sb) if sa else None})
setter = pd.DataFrame(setter)
setter.to_csv(R / "by_setter.csv", index=False)
m["setter"] = setter.to_dict(orient="records")
m["univ_increase_by_setter"] = {r["setter"]: r["schools_diff"] for r in m["setter"] if r["kind"] == "大学"}

# 年ごとの表（図に使う）
by = pd.DataFrame({"pop18": p.pop18, "univ": p.univ_total, "jc": p.jc_total, "univ_plus_jc": both,
                   "ent_univ": p.ent_univ, "ent_jc": p.ent_jc, "ent_both": entb,
                   "rate_univ_tab": p.rate_univ_tab, "rate_jc_tab": p.rate_jc_tab,
                   "univ_national": p.univ_national, "univ_public": p.univ_public, "univ_private": p.univ_private}).loc[1980:2025]
for c in ["pop18", "univ", "jc", "univ_plus_jc", "ent_univ", "ent_both"]:
    by[f"{c}_idx"] = (100 * by[c] / by.at[B, c]).round(1)
by.to_csv(R / "by_year.csv")

# 仮説
d = m["decomp_univ"]
h = {}
h["H1"] = {"pop18_change_pct": m["pop18"]["change_pct"], "univ_change_pct": m["univ"]["change_pct"],
           "verdict": "支持" if (m["pop18"]["change_pct"] <= -40 and m["univ"]["change_pct"] >= 40) else "外れ"}
h["H2"] = {"ent_change": d["change"], "pop_effect": d["pop_effect"], "rate_effect": d["rate_effect"],
           "verdict": "支持" if (d["change"] > 0 and d["rate_effect"] > -d["pop_effect"]) else "外れ"}
h["H3"] = {"change_pct": m["univ_plus_jc"]["change_pct"],
           "verdict": "支持" if abs(m["univ_plus_jc"]["change_pct"]) < 10 else "外れ"}
rp = setter.set_index(["kind", "setter"])["schools_ratio"]
h["H4"] = {"public_ratio": float(rp[("大学", "公立")]), "private_ratio": float(rp[("大学", "私立")]),
           "verdict": "支持" if rp[("大学", "公立")] > rp[("大学", "私立")] else "外れ"}
m["hypotheses"] = h

# 頑健性
rob = []
rob.append({"check": "本線（18歳人口＝3年前の中学校等卒業者）", "period": f"{B}→{E}", **{k: d[k] for k in ["change", "pop_effect", "rate_effect"]},
            "pop_change_pct": pct(p.pop18[B], p.pop18[E]), "univ_change_pct": pct(p.univ_total[B], p.univ_total[E])})
dd = decompose(p.ent_univ, p.hs_grad, B, E)
rob.append({"check": "18歳人口の目安を高校の卒業者数に替える", "period": f"{B}→{E}", **{k: dd[k] for k in ["change", "pop_effect", "rate_effect"]},
            "pop_change_pct": pct(p.hs_grad[B], p.hs_grad[E]), "univ_change_pct": pct(p.univ_total[B], p.univ_total[E])})
for y0 in [2000, 2010]:
    dd = decompose(p.ent_univ, p.pop18, y0, E)
    rob.append({"check": "期間を変える", "period": f"{y0}→{E}", **{k: dd[k] for k in ["change", "pop_effect", "rate_effect"]},
                "pop_change_pct": pct(p.pop18[y0], p.pop18[E]), "univ_change_pct": pct(p.univ_total[y0], p.univ_total[E])})
nc = p.univ_total - p.univ_t1_corr_only
rob.append({"check": "通信教育のみの大学を除いて数える", "period": f"{B}→{E}", "change": None, "pop_effect": None, "rate_effect": None,
            "pop_change_pct": pct(p.pop18[B], p.pop18[E]), "univ_change_pct": pct(nc[B], nc[E]),
            "note": f"通信教育のみの大学 {int(p.univ_t1_corr_only[B])}→{int(p.univ_t1_corr_only[E])}校"})
dd = m["decomp_both"]
rob.append({"check": "大学＋短大の入学者で分解", "period": f"{B}→{E}", **{k: dd[k] for k in ["change", "pop_effect", "rate_effect"]},
            "pop_change_pct": pct(p.pop18[B], p.pop18[E]), "univ_change_pct": pct(both[B], both[E]), "note": "学校数は大学＋短大"})
rob.append({"check": "学校数を2026年（総括表1）まで延ばす", "period": f"{B}→2026", "change": None, "pop_effect": None, "rate_effect": None,
            "pop_change_pct": None, "univ_change_pct": pct(p.univ_t1[B], p.univ_t1[2026]),
            "note": f"大学 {int(p.univ_t1[2025])}→{int(p.univ_t1[2026])}校、短大 {int(p.jc_t1[2025])}→{int(p.jc_t1[2026])}校（2026年）"})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)
m["robustness"] = rob.where(rob.notna(), None).to_dict(orient="records")
m["univ_2026_t1"] = int(p.univ_t1[2026]); m["jc_2026_t1"] = int(p.jc_t1[2026])
m["corr_only_univ"] = {str(B): int(p.univ_t1_corr_only[B]), str(E): int(p.univ_t1_corr_only[E])}
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(m["hypotheses"], ensure_ascii=False, indent=1))
print(json.dumps({k: m[k] for k in ["pop18", "univ", "jc", "univ_plus_jc", "ent_univ", "ent_jc", "ent_both", "decomp_univ", "decomp_both", "rate_univ_tab", "rate_jc_tab"]}, ensure_ascii=False))
print(setter.to_string()); print(rob.to_string())
