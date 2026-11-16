"""03_analysis.py : 年休の取得率の上がり方を、規模・産業別、前後の期間別に比べる（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "paid_leave.csv")
SIZES = ["1000人以上", "300〜999人", "100〜299人", "30〜99人"]


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


rate = d.pivot_table(index="year", columns="group", values="rate")
taken = d.pivot_table(index="year", columns="group", values="taken")
gr = d.pivot_table(index="year", columns="group", values="granted")
rate.round(2).to_csv(RES / "rate_by_group_year.csv")
main = {"total_rate": {int(y): r(v, 1) for y, v in rate["調査産業計"].items()}}
t = rate["調査産業計"]
pre = (t.loc[2019] - t.loc[2015]) / 4
post = (t.loc[2025] - t.loc[2019]) / 6
main["H1"] = {"pre_per_year_2015_2019": r(pre, 3), "post_per_year_2019_2025": r(post, 3), "ratio": r(post / pre, 2),
              "v2015": r(t.loc[2015], 1), "v2019": r(t.loc[2019], 1), "v2025": r(t.loc[2025], 1)}
# 規模別
sz = {s: {"2015": r(rate.loc[2015, s], 1), "2019": r(rate.loc[2019, s], 1), "2025": r(rate.loc[2025, s], 1),
          "chg_2019_2025": r(rate.loc[2025, s] - rate.loc[2019, s], 1), "chg_2015_2019": r(rate.loc[2019, s] - rate.loc[2015, s], 1)} for s in SIZES}
main["size"] = sz
gap = rate["1000人以上"] - rate["30〜99人"]
main["gap_1000_vs_30_99"] = {int(y): r(v, 1) for y, v in gap.items()}
main["H2"] = {"large_chg": sz["1000人以上"]["chg_2019_2025"], "small_chg": sz["30〜99人"]["chg_2019_2025"]}
# 産業別
inds = [c for c in d[d.kind == "industry"].group.unique()]
ind = pd.DataFrame({"r2015": rate.loc[2015, inds], "r2019": rate.loc[2019, inds], "r2020": rate.loc[2020, inds], "r2025": rate.loc[2025, inds],
                    "taken2019": taken.loc[2019, inds], "taken2025": taken.loc[2025, inds],
                    "granted2019": gr.loc[2019, inds], "granted2025": gr.loc[2025, inds]})
ind["chg_2019_2025"] = ind.r2025 - ind.r2019
ind["chg_2020_2025"] = ind.r2025 - ind.r2020
ind = ind.dropna(subset=["r2019", "r2025"])
order = ["鉱業", "建設業", "製造業", "電気・ガス", "情報通信業", "運輸業", "卸売・小売業", "金融・保険業", "不動産業", "学術研究・専門技術",
         "宿泊・飲食", "生活関連・娯楽", "教育・学習支援", "医療・福祉", "複合サービス", "サービス業（他に分類されないもの）"]
ind = ind.loc[[g for g in order if g in ind.index]]
ind.round(2).to_csv(RES / "industry_change.csv")
c = np.corrcoef(ind.r2019, ind.chg_2019_2025)[0, 1]
sp = stats.spearmanr(ind.r2019, ind.chg_2019_2025).statistic
sub = ind.drop(index=[g for g in ["鉱業", "複合サービス"] if g in ind.index])
c2 = np.corrcoef(sub.r2019, sub.chg_2019_2025)[0, 1]
c3 = np.corrcoef(ind.r2020, ind.chg_2020_2025)[0, 1]
b = np.polyfit(ind.r2019, ind.chg_2019_2025, 1)
main["H3"] = {"n": int(len(ind)), "corr": r(c, 3), "spearman": r(sp, 3), "corr_excl_small": r(c2, 3), "corr_from_2020": r(c3, 3),
              "slope": r(b[0], 3), "sd_2019": r(ind.r2019.std(ddof=0), 2), "sd_2025": r(ind.r2025.std(ddof=0), 2),
              "min_2019": [ind.r2019.idxmin(), r(ind.r2019.min(), 1)], "max_2019": [ind.r2019.idxmax(), r(ind.r2019.max(), 1)],
              "min_2025": [ind.r2025.idxmin(), r(ind.r2025.min(), 1)], "max_2025": [ind.r2025.idxmax(), r(ind.r2025.max(), 1)]}
main["industry"] = {g: {"2019": r(ind.loc[g, "r2019"], 1), "2025": r(ind.loc[g, "r2025"], 1), "chg": r(ind.loc[g, "chg_2019_2025"], 1),
                        "taken2025": r(ind.loc[g, "taken2025"], 1)} for g in ind.index}
# H4 分解
dl_rate = np.log(t.loc[2025] / t.loc[2019])
dl_taken = np.log(taken.loc[2025, "調査産業計"] / taken.loc[2019, "調査産業計"])
dl_gr = np.log(gr.loc[2025, "調査産業計"] / gr.loc[2019, "調査産業計"])
main["H4"] = {"taken_2019": r(taken.loc[2019, "調査産業計"], 1), "taken_2025": r(taken.loc[2025, "調査産業計"], 1),
              "granted_2019": r(gr.loc[2019, "調査産業計"], 1), "granted_2025": r(gr.loc[2025, "調査産業計"], 1),
              "dlog_rate": r(dl_rate, 4), "dlog_taken": r(dl_taken, 4), "dlog_granted": r(dl_gr, 4),
              "share_taken": r(dl_taken / (dl_taken - dl_gr), 3)}
dec = []
for g in ["調査産業計"] + SIZES:
    a = np.log(taken.loc[2025, g] / taken.loc[2019, g])
    bb = np.log(gr.loc[2025, g] / gr.loc[2019, g])
    dec.append({"group": g, "taken2019": taken.loc[2019, g], "taken2025": taken.loc[2025, g], "granted2019": gr.loc[2019, g],
                "granted2025": gr.loc[2025, g], "dlog_taken": a, "dlog_granted": bb, "share_taken": a / (a - bb)})
pd.DataFrame(dec).round(4).to_csv(RES / "decomposition_2019_2025.csv", index=False)
main["decomposition_size"] = {row["group"]: {"share_taken": r(row["share_taken"], 3), "taken2019": r(row["taken2019"], 1), "taken2025": r(row["taken2025"], 1),
                                             "granted2019": r(row["granted2019"], 1), "granted2025": r(row["granted2025"], 1)} for row in dec}
# 頑健性
rb = [
    {"check": "主：H1 前2015→2019・後2019→2025（1年あたり）", "pre": r(pre, 3), "post": r(post, 3), "ratio": r(post / pre, 2)},
    {"check": "1 前を2009→2019年調査に", "pre": r((t.loc[2019] - t.loc[2009]) / 10, 3), "post": r(post, 3), "ratio": r(post / ((t.loc[2019] - t.loc[2009]) / 10), 2)},
    {"check": "2 後の起点を2020年調査に（2020→2025）", "pre": r(pre, 3), "post": r((t.loc[2025] - t.loc[2020]) / 5, 3), "ratio": r(((t.loc[2025] - t.loc[2020]) / 5) / pre, 2)},
    {"check": "3 H3 を順位の相関で", "pre": None, "post": None, "ratio": r(sp, 3)},
    {"check": "4 H3 を小さな2産業（鉱業・複合サービス）を除いて", "pre": None, "post": None, "ratio": r(c2, 3)},
    {"check": "5 H3 の起点を2020年調査に", "pre": None, "post": None, "ratio": r(c3, 3)},
]
pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rb
# 問い直し：取得日数（2025年調査）の産業別、5日との差
q = ind[["taken2019", "taken2025"]].copy()
q["over5_2025"] = q.taken2025 - 5
q.round(2).to_csv(RES / "requestion_taken_days.csv")
main["requestion"] = {"min_taken_2025": [q.taken2025.idxmin(), r(q.taken2025.min(), 1)], "max_taken_2025": [q.taken2025.idxmax(), r(q.taken2025.max(), 1)],
                      "min_taken_2019": [q.taken2019.idxmin(), r(q.taken2019.min(), 1)],
                      "n_below_8_2019": int((q.taken2019 < 8).sum()), "n_below_8_2025": int((q.taken2025 < 8).sum()),
                      "size_taken": {s: [r(taken.loc[2019, s], 1), r(taken.loc[2025, s], 1)] for s in SIZES}}
main["judgement"] = {"H1": "支持" if post >= 2 * pre else "外れ", "H2": "支持" if main["H2"]["small_chg"] > main["H2"]["large_chg"] else "外れ",
                     "H3": "支持" if c < -0.3 else "外れ", "H4": "支持" if main["H4"]["share_taken"] >= 0.8 else "外れ"}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "judgement", "size", "robustness", "requestion", "decomposition_size"]}, ensure_ascii=False, indent=1))
print(ind.round(1).to_string())
