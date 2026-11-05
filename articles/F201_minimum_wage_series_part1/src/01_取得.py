"""F201 データの取得メモ（新しく取得したのは全国の影響率・未満率の表だけ）。

- data/raw/f01_panel.csv          : F01 のパネル（47都道府県×2008〜2025年、就業率・失業率・最低賃金）
- data/raw/minimum_wage_2002_2026.csv : 地域別最低賃金（F01 と同じ）
- data/raw/f156_panel_wage.csv    : F156 の短時間労働者の時給パネル（賃金構造基本統計調査、2009〜2025年）
- data/raw/f156_pref_bite.csv     : F156 の基準期間（2009〜11年）の bite
- data/raw/pref_border_pairs_from_F15.csv : F15 の県境の市区町村ペアから作った「隣り合う都道府県」の組（89組）
- data/raw/national_impact_rate.csv : 厚生労働省「最低賃金に関する基礎調査」による全国の未満率・影響率（2005〜2024年）。
    中央最低賃金審議会 目安に関する小委員会の配布資料（平成27年7月15日 第2回 p5、
    「地域別最低賃金の推移等に関する資料 No.22-1（H26〜R5）」、令和7年第1回 p17）から手で転記。
    平成17〜26年度の表は区分名がテキストから読めなかったため、H26 の値（未満率2.0%・影響率7.3%）が
    No.22-1 の全国計と一致する段を全国計として採用した。
- data/raw/national_impact_rate_special_tab.csv : 賃金構造基本統計調査特別集計（5人以上）の未満率・影響率（2022〜2024年）

このスクリプトは、ファイルがそろっているかを確かめるだけです。
"""
from common import RAW

need = ["f01_panel.csv", "minimum_wage_2002_2026.csv", "f156_panel_wage.csv", "f156_pref_bite.csv",
        "pref_border_pairs_from_F15.csv", "national_impact_rate.csv", "national_impact_rate_special_tab.csv"]
miss = [f for f in need if not (RAW / f).exists()]
print("missing:", miss if miss else "なし")
