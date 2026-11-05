"""F202 データの取得（記録用）

このフォルダの data/raw/ にあるファイルの出どころ:

- minimum_wage_2002_2026.csv, national_impact_rate.csv
    F201（articles/F201_minimum_wage_series_part1/data/raw/）からそのままコピー。
    もとは厚生労働省「地域別最低賃金の全国一覧」と中央最低賃金審議会の資料。
- f201_panel_emp.csv, f201_panel_wage.csv, f201_method_comparison.csv, f201_for_F202.json
    F201 の data/ と results/ からコピー（県×年のパネル、4つの推定方法の結果、後編に渡す数字）。
- f82_bunching_main.csv, f82_robustness.csv
    F82（articles/F82_income_wall_bunching/results/）からコピー（年収の壁の手前の集積）。
- shugyo_t8_adjust_pref_2017_2022.csv
    総務省「就業構造基本調査」主要統計表 第8表
    「男女、就業調整の有無、年齢別非正規の職員・従業員数－全国、都道府県」
    （平成29年＝2017年、令和4年＝2022年）。
    e-Stat の Excel をブラウザで読み込み、全国と47都道府県×男女計・男・女の行を CSV にした。
    列：tot_*（総数）、adj_*（就業調整をしている）、noadj_*（就業調整をしていない）、
        年齢は all・15_24・25_34・35_44・45_54・55_64・65p。単位は人。

この作業環境からは e-Stat に直接つながらないため、取得はブラウザで行った。
このスクリプトはファイルがそろっているかを確かめるだけ。
"""
from common import RAW

NEED = [
    "minimum_wage_2002_2026.csv", "national_impact_rate.csv",
    "f201_panel_emp.csv", "f201_panel_wage.csv", "f201_method_comparison.csv",
    "f201_for_F202.json", "f82_bunching_main.csv", "f82_robustness.csv",
    "shugyo_t8_adjust_pref_2017_2022.csv",
]
missing = [f for f in NEED if not (RAW / f).exists()]
if missing:
    raise SystemExit("足りないファイル: " + ", ".join(missing))
print("data/raw はそろっています")
