"""H1〜H4 と頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "maikin_annual_by_type.csv", dtype={"size": str})
IND16 = list("CDEFGHIJKLMNOPQR")
r3 = lambda x: round(float(x), 3)
NAMES = {"C": "鉱業", "D": "建設業", "E": "製造業", "F": "電気・ガス", "G": "情報通信", "H": "運輸・郵便", "I": "卸売・小売", "J": "金融・保険",
         "K": "不動産・物品賃貸", "L": "学術研究等", "M": "飲食サービス等", "N": "生活関連サービス等", "O": "教育・学習支援", "P": "医療・福祉",
         "Q": "複合サービス", "R": "その他のサービス"}

def get(size="T", pay="sched_pay", hours="sched_hours"):
    x = d[d["size"] == size].copy()
    x["hourly"] = x[pay] / x[hours]
    x["hours_total"] = x.workers * x[hours]
    return x

def growth(x, typ, ind, a, b, col="hourly"):
    s = x[(x.type == typ) & (x.ind == ind)].set_index("year")[col]
    return 100 * (np.log(s[b]) - np.log(s[a]))

def shift_share(x, typ, a, b, fix="start"):
    s = x[(x.type == typ) & x.ind.isin(IND16)].pivot(index="year", columns="ind", values="hourly")
    w = x[(x.type == typ) & x.ind.isin(IND16)].pivot(index="year", columns="ind", values="hours_total")
    w = w.div(w.sum(axis=1), axis=0)
    wa, wb = w.loc[a], w.loc[b]
    agg_a, agg_b = float((wa * s.loc[a]).sum()), float((wb * s.loc[b]).sum())
    wf = wa if fix == "start" else wb
    fixed_b, fixed_a = float((wf * s.loc[b]).sum()), float((wf * s.loc[a]).sum())
    return dict(agg_growth=100 * np.log(agg_b / agg_a), fixed_growth=100 * np.log(fixed_b / fixed_a))

def compare(a=2015, b=2025, size="T", pay="sched_pay", hours="sched_hours", fix="start", label=""):
    x = get(size, pay, hours)
    gp, gg = growth(x, "part", "TL", a, b), growth(x, "general", "TL", a, b)
    sp, sg = shift_share(x, "part", a, b, fix), shift_share(x, "general", a, b, fix)
    gap = gp - gg; gap_fixed = sp["fixed_growth"] - sg["fixed_growth"]; gap_agg16 = sp["agg_growth"] - sg["agg_growth"]
    by = []
    for i in IND16:
        by.append(dict(ind=i, name=NAMES[i], part=r3(growth(x, "part", i, a, b)), general=r3(growth(x, "general", i, a, b))))
    by = pd.DataFrame(by); by["gap"] = by.part - by.general
    return dict(spec=label, period=f"{a}-{b}", size=size, pay=pay, hours=hours, fix=fix,
                part_growth=r3(gp), general_growth=r3(gg), gap=r3(gap),
                part_fixed=r3(sp["fixed_growth"]), general_fixed=r3(sg["fixed_growth"]), gap_fixed=r3(gap_fixed),
                gap_agg16=r3(gap_agg16), share_remaining=r3(gap_fixed / gap_agg16) if gap_agg16 != 0 else None,
                n_ind_part_faster=int((by.gap > 0).sum())), by

out = {}
main, by = compare(label="主")
by.round(3).to_csv(RES / "by_industry_2015_2025.csv", index=False)
out["main"] = main
out["H1_verdict"] = "支持" if main["gap"] >= 3 else "外れ"
out["H2_verdict"] = "支持" if (main["share_remaining"] is not None and main["share_remaining"] >= 0.7) else "外れ"
out["H3_verdict"] = "支持" if main["n_ind_part_faster"] >= 11 else "外れ"
x = get()
lv = x[x.ind == "TL"].pivot(index="year", columns="type", values="hourly")
lv["ratio_part_to_general"] = lv.part / lv.general
lv["yoy_part"] = 100 * np.log(lv.part).diff(); lv["yoy_general"] = 100 * np.log(lv.general).diff(); lv["yoy_gap"] = lv.yoy_part - lv.yoy_general
lv.round(4).to_csv(RES / "tl_hourly_by_year.csv")
out["hourly_2015"] = {k: r3(lv.loc[2015, k]) for k in ["part", "general", "ratio_part_to_general"]}
out["hourly_2025"] = {k: r3(lv.loc[2025, k]) for k in ["part", "general", "ratio_part_to_general"]}
g1, g2 = lv.loc[2015:2019, "yoy_gap"].mean(), lv.loc[2023:2025, "yoy_gap"].mean()
out["yoy_gap_2015_2019"], out["yoy_gap_2023_2025"] = r3(g1), r3(g2)
out["yoy_gap_2020_2022"] = r3(lv.loc[2020:2022, "yoy_gap"].mean())
out["H4_verdict"] = "支持" if g2 > g1 else "外れ"
out["n_years_part_faster_2011_2025"] = int((lv.loc[2011:2025, "yoy_gap"] > 0).sum())
# 時間の比重の変化（パート）
w = x[(x.type == "part") & x.ind.isin(IND16)].pivot(index="year", columns="ind", values="hours_total")
w = w.div(w.sum(axis=1), axis=0)
out["part_hours_share_2015_2025"] = {NAMES[i]: [r3(100 * w.loc[2015, i]), r3(100 * w.loc[2025, i])] for i in IND16}
# 頑健性
rob = [main,
       compare(a=2012, label="R1a 2012→2025")[0], compare(a=2019, label="R1b 2019→2025")[0],
       compare(size="0", label="R2 規模30人以上")[0],
       compare(pay="total_pay", hours="total_hours", label="R3 賞与・残業代を含む（現金給与総額÷総実労働時間）")[0],
       compare(fix="end", label="R4 比重を2025年に固定")[0]]
# R5 月給（所定内給与そのもの）
xm = get(); xm["hourly"] = xm["sched_pay"]
pm, gm = growth(xm, "part", "TL", 2015, 2025), growth(xm, "general", "TL", 2015, 2025)
rob.append(dict(spec="R5 月給（所定内給与）", period="2015-2025", part_growth=r3(pm), general_growth=r3(gm), gap=r3(pm - gm)))
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
out["robustness"] = rob
# 参考：所定内労働時間の変化
hh = x[x.ind == "TL"].pivot(index="year", columns="type", values="sched_hours")
out["sched_hours_2015_2025"] = {t: [r3(hh.loc[2015, t]), r3(hh.loc[2025, t])] for t in ["part", "general"]}
(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("robustness", "part_hours_share_2015_2025")}, ensure_ascii=False, indent=0))
print(pd.DataFrame(rob)[["spec", "part_growth", "general_growth", "gap", "gap_fixed", "share_remaining", "n_ind_part_faster"]].to_string())
print(by.to_string()); print(lv.round(3).to_string())
