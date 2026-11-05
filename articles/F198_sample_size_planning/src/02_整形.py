"""02 整形：転記した表の確認（合計・単位のチェック）。"""
import pandas as pd

from common import DATA, LFS_POP15

se = pd.read_csv(DATA / "lfs_se_by_size.csv")
# 標準誤差率 = 標準誤差 ÷ 推定値 を、公表の率（四捨五入）と照合
for col, rate in (("monthly_se_10k", "monthly_se_pct"), ("annual_se_10k", "annual_se_pct")):
    calc = se[col] / se["size_10k"] * 100
    tol = 0.05 / se["size_10k"] * 100 + 0.051   # 標準誤差は0.1万人単位、率は0.1%単位で丸められている
    diff = (calc - se[rate]).abs()
    print(col, "率の再計算との最大差", round(diff.max(), 3), "pt（丸めの幅以内:", bool((diff <= tol).all()), "）")
    assert (diff <= tol).all()
main = pd.read_csv(DATA / "lfs_main_items_2025.csv")
print("15歳以上人口（労働力人口＋非労働力人口）", LFS_POP15, "万人")
calc = main.annual_se_10k / main.annual_2025_10k * 100
print("主要項目 率の再計算との最大差", round((calc - main.annual_se_pct).abs().max(), 3))
sv = pd.read_csv(DATA / "survey_designs.csv")
print(sv[["statistic", "psu_count", "households", "persons_or_units"]])
