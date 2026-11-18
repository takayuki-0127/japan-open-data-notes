"""Excel 5本 → data/panel.csv（年×指標）。見出しの文字で列を選び、表どうしの合計を照らし合わせる。"""
import json
import pandas as pd
from common import ROOT, read_nenji, col

t9 = read_nenji("nenji_09_entrants.xlsx")
u = read_nenji("nenji_k10_university.xlsx")
j = read_nenji("nenji_k12_juniorcollege.xlsx")
t1 = read_nenji("nenji_01_schools.xlsx")
t13 = read_nenji("nenji_13_graduates.xlsx")

p = pd.DataFrame(index=range(1954, 2027))
p.index.name = "year"
p["pop18"] = t9["3年前の中学校等卒業者"]
p["ent_univ"] = col(t9, "大学・短期大学への入学者", "大学")
p["ent_jc"] = col(t9, "大学・短期大学への入学者", "短期大学")
p["ent_both_tab"] = col(t9, "大学・短期大学への入学者", "計")
p["rate_univ_tab"] = col(t9, "進学率", "大学・短期大学", "大学")
p["rate_jc_tab"] = col(t9, "進学率", "大学・短期大学", "短期大学")
for s, k in [("total", "計"), ("national", "国立"), ("public", "公立"), ("private", "私立")]:
    p[f"univ_{s}"] = col(u, "学校数", k)
    p[f"jc_{s}"] = col(j, "学校数", k)
    p[f"univ_students_{s}"] = col(u, "在籍者数", k)
    p[f"jc_students_{s}"] = col(j, "在籍者数", k)
p["univ_t1"] = t1["大学"]
p["univ_t1_corr_only"] = t1["大学|通信教育のみを行う学校数（別掲）"]
p["jc_t1"] = t1["短期大学"]
p["jc_t1_corr_only"] = t1["短期大学|通信教育のみを行う学校数（別掲）"]
p["hs_grad"] = t13["高等学校"]

# ---- 照らし合わせ（表の中・表どうし） ----
chk = {}
y = p.loc[1992:2025]
chk["ent_sum_eq_total"] = bool(((y.ent_univ + y.ent_jc) - y.ent_both_tab).abs().max() == 0)
chk["univ_setter_sum_eq_total"] = bool(((y.univ_national + y.univ_public + y.univ_private) - y.univ_total).abs().max() == 0)
chk["jc_setter_sum_eq_total"] = bool(((y.jc_national + y.jc_public + y.jc_private) - y.jc_total).abs().max() == 0)
chk["univ_t1_eq_k10"] = bool((y.univ_t1 - y.univ_total).abs().max() == 0)
chk["jc_t1_eq_k12"] = bool((y.jc_t1 - y.jc_total).abs().max() == 0)
# 表の進学率（小数1位）と、入学者÷18歳人口の計算値のずれ
chk["rate_univ_max_abs_diff_pt"] = round(float((100 * y.ent_univ / y.pop18 - y.rate_univ_tab).abs().max()), 3)
# 特定の年の値（Excel の見出しの文字で読んだ値を、表の行とは別に記録しておく）
chk["values"] = {str(yy): {k: (None if pd.isna(p.at[yy, k]) else int(p.at[yy, k]))
                           for k in ["pop18", "ent_univ", "ent_jc", "univ_total", "univ_public", "jc_total"]}
                 for yy in [1992, 2025]}
for k, v in chk.items():
    if k.endswith("eq_total") or k.endswith("_eq_k10") or k.endswith("_eq_k12"):
        assert v, k
p.to_csv(ROOT / "data" / "panel.csv", float_format="%.1f")
json.dump(chk, open(ROOT / "data" / "build_checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(chk, ensure_ascii=False))
