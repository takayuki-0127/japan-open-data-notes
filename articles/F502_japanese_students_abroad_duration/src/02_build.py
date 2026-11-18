"""読み取り済みの CSV（data/extract_*.csv）と学校基本調査の Excel から、分析用の表を作る。照合もここで行う。"""
import json
import pandas as pd
from common import ROOT, read_nenji, col

D = ROOT / "data"
P = ["m_lt1", "m1_3", "m3_6", "m6_12", "y1plus", "unknown"]
REG = ["アジア", "中東", "アフリカ", "大洋州", "北米", "中南米", "欧州", "その他・無記入"]

ex = pd.read_csv(D / "extract_region_period.csv")
ex[P] = ex[P].fillna(0).astype(int)
ex["region"] = ex.region.replace({"その他": "その他・無記入", "無記入": "その他・無記入"})
chk = {}
chk["row_periods_sum_eq_total"] = bool((ex[P].sum(axis=1) == ex.total).all())
body = ex[ex.region != "計"].groupby(["year", "kind"])[P + ["total"]].sum()
tot = ex[ex.region == "計"].set_index(["year", "kind"])[P + ["total"]]
chk["regions_sum_eq_total_row"] = bool((body.sort_index() == tot.sort_index()).all().all())

# 協定あり＋協定なし ＝ 合計（2009〜2024年度）。2014年度以降は「合計」の表と一致するか確かめる
an = ex[ex.kind.isin(["ari", "nashi"])].groupby(["year", "region"])[P + ["total"]].sum()
tt = ex[ex.kind == "total"].groupby(["year", "region"])[P + ["total"]].sum()
common_idx = tt.index.intersection(an.index)
chk["ari_plus_nashi_eq_total_table_2014plus"] = bool((an.loc[common_idx] == tt.loc[common_idx]).all().all()) and len(common_idx) == len(tt)

# 2024年度版の推移の表との照合
ser = pd.read_csv(D / "extract_series_2024.csv").set_index("year")
k = ex[ex.region == "計"].pivot(index="year", columns="kind", values="total")
chk["ari_eq_series"] = bool((k.ari == ser.ari.loc[k.index]).all())
chk["nashi_eq_series"] = bool((k.nashi == ser.nashi.loc[k.index]).all())
chk["sum_eq_series_total"] = bool(((k.ari + k.nashi) == ser.total.loc[k.index]).all())

# 翌年度の表の（前年度の値）と、その年度の表の値の差（後から直された分）
pv = ex.dropna(subset=["prev_total"]).groupby(["year", "kind", "region"]).prev_total.sum()
cur = ex.groupby(["year", "kind", "region"]).total.sum().to_dict()
diff = []
for (y, kd, rg), v in pv.items():
    key = (y - 1, kd, rg)
    if key in cur:
        diff.append({"year": int(y - 1), "kind": kd, "region": rg, "own_table": int(cur[key]),
                     "next_table_prev": int(v), "diff": int(v - cur[key])})
diff = pd.DataFrame(diff)
diff.to_csv(D / "prev_value_check.csv", index=False)
chk["prev_value_rows"] = int(len(diff))
chk["prev_value_mismatch_rows"] = int((diff["diff"] != 0).sum())
chk["prev_value_mismatch_total_rows_abs_sum"] = int(diff[diff.region == "計"]["diff"].abs().sum())

# 年度×地域×期間（合計＝協定あり＋なし）
panel = an.reset_index()
panel["region"] = pd.Categorical(panel.region, REG + ["計"], ordered=True)
panel = panel.sort_values(["year", "region"])
panel.to_csv(D / "panel_region_period.csv", index=False)
ari = ex[ex.kind == "ari"].copy()
ari["region"] = pd.Categorical(ari.region, REG + ["計"], ordered=True)
ari.sort_values(["year", "region"])[["year", "region"] + P + ["total"]].to_csv(D / "panel_ari.csv", index=False)

# 在学者（学校基本調査 年次統計 在学者数）：大学＋短期大学
en = read_nenji("nenji_02_enrollment.xlsx")
stu = (col(en, "大学") + col(en, "短期大学")).loc[2009:2024].astype(int).rename("students_univ_jc")
stu.to_csv(D / "students.csv")

long = pd.read_csv(D / "extract_long_mext.csv")
chk["long_prev_chain_ok"] = bool(all(long.n_prev.iloc[i + 1] == long.n.iloc[i] for i in range(len(long) - 1)))
json.dump(chk, open(D / "build_checks.json", "w"), ensure_ascii=False, indent=1)
print(chk)
assert all(v for kk, v in chk.items() if isinstance(v, bool)), chk
