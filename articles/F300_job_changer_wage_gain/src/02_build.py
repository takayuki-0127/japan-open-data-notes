"""data/raw の Excel から分析用の表を作る（オフライン）。
出力：data/wage_change_by_age.csv（年×年齢×区分の割合）、data/job_change_rate_by_age5.csv、
      data/employed_by_age5.csv、data/jobs_ratio_annual.csv、data/age_weights.csv
"""
import pathlib, re, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
YEARS = list(range(1991, 2026))
CLEAN = lambda s: re.sub(r"[\s　]|[0-9]\)$", "", str(s)) if isinstance(s, str) else s

# 第11表
v = pd.read_excel(RAW / "koyo_hyo11_wage_change_by_age.xls", header=None)
assert str(v.iloc[3, 7]).replace("\n", "").startswith("平成") and str(v.iloc[3, 41]).strip() == "7"
cat_map = {"１割以上増加": "up10", "１割未満増減": "within10", "１割以上減少": "down10"}
age_map = {"計": "all", "19歳以下": "u19", "20～29歳": "20_29", "30～44歳": "30_44", "45～59歳": "45_59", "60歳以上": "60p"}
rows, age = [], None
for i in range(4, 22):
    a = CLEAN(v.iloc[i, 0])
    if isinstance(a, str) and a:
        age = age_map[a]
    c = cat_map[CLEAN(v.iloc[i, 5])]
    for j, y in enumerate(YEARS):
        rows.append((y, age, c, float(v.iloc[i, 7 + j])))
wc = pd.DataFrame(rows, columns=["year", "age", "cat", "pct"]).pivot_table(index=["year", "age"], columns="cat", values="pct").reset_index()
wc = wc[["year", "age", "up10", "within10", "down10"]].sort_values(["year", "age"]).reset_index(drop=True)
wc.to_csv(DATA / "wage_change_by_age.csv", index=False)

# 第4-2表（男女計の行だけ）
v = pd.read_excel(RAW / "koyo_hyo04_2_job_change_rate_by_age.xls", header=None)
assert str(v.iloc[3, 5]).replace("\n", "").startswith("平成") and str(v.iloc[3, 39]).strip() == "7"
rows = []
for i in range(4, 16):
    lab = CLEAN(v.iloc[i, 3]).replace("6)", "")
    lab = re.sub(r"\d\)$", "", lab)
    for j, y in enumerate(YEARS):
        val = v.iloc[i, 5 + j]
        rows.append((y, lab, float(val) if pd.notna(val) else np.nan))
jr = pd.DataFrame(rows, columns=["year", "age5", "job_change_rate"])
jr.to_csv(DATA / "job_change_rate_by_age5.csv", index=False)

# 労働力調査 表3-3（総数、就業者数、万人）
v = pd.read_excel(RAW / "lfs_t3_3_employed_by_age5.xlsx", sheet_name="総数", header=None)
labs = ["15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65歳以上"]
rows = []
for i in range(9, len(v)):
    y = v.iloc[i, 1]
    if isinstance(y, (int, float)) and not pd.isna(y) and 1968 <= int(y) <= 2025:
        for k, lab in enumerate(labs):
            rows.append((int(y), lab, float(v.iloc[i, 3 + k])))
em = pd.DataFrame(rows, columns=["year", "age5", "employed_10k"])
em.to_csv(DATA / "employed_by_age5.csv", index=False)

# 有効求人倍率（年平均、実数）
v = pd.read_excel(RAW / "hw_t1_labor_market.xlsx", header=None)
rows = []
for i in range(len(v)):
    m = re.fullmatch(r"(\d{4})年", str(v.iloc[i, 0]).strip())
    if m:
        rows.append((int(m.group(1)), float(v.iloc[i, 4])))
hr = pd.DataFrame(rows, columns=["year", "jobs_ratio"]).drop_duplicates("year").sort_values("year")
hr.to_csv(DATA / "jobs_ratio_annual.csv", index=False)

# 年齢の重み：転職入職者数の近似 ∝ 転職入職率 × 就業者数（5歳階級）を第11表の5区分にまとめる
g5 = {"19歳以下": "u19", "20～24歳": "20_29", "25～29歳": "20_29", "30～34歳": "30_44", "35～39歳": "30_44", "40～44歳": "30_44",
      "45～49歳": "45_59", "50～54歳": "45_59", "55～59歳": "45_59", "60～64歳": "60p", "65歳以上": "60p"}
em2 = em.replace({"age5": {"15～19歳": "19歳以下"}})
w = jr.merge(em2, on=["year", "age5"])
w = w[w.year >= 1993].copy()  # 1992年までは35〜44歳などの区分
w["movers"] = w.job_change_rate / 100 * w.employed_10k
w["employed"] = w.employed_10k
w["age"] = w.age5.map(g5)
wa = w.groupby(["year", "age"], sort=True)[["movers", "employed"]].sum().reset_index()
wa["w_movers"] = wa.movers / wa.groupby("year").movers.transform("sum")
wa["w_employed"] = wa.employed / wa.groupby("year").employed.transform("sum")
wa.to_csv(DATA / "age_weights.csv", index=False, float_format="%.6f")
print(len(wc), len(jr), len(em), len(hr), len(wa))
