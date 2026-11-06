"""元データ（このフォルダでは新しく取得しない）
この記事は、同じリポジトリのほかの記事フォルダのデータをそのまま使う。リポジトリ全体を取得して articles/ に並べておくこと。
- articles/F207_landprice_series_part1/data/price_hist_1996_2026.csv.gz・chg_2007_2026.csv.gz
    地価公示（国土数値情報 L01-26）の各地点の1996〜2026年の価格と、前年と同じ地点が続いたかの印（F207 の 01_取得.py で抽出）
- articles/F207_landprice_series_part1/results/A_change_2006_2026.csv.gz：20年の変化（地点）
- articles/F182_condo_depreciation_curve/data/condo_clean.csv.gz
    国土交通省「不動産取引価格情報」（不動産情報ライブラリ）の中古マンション等の取引、2015〜2025年、全国（F182 で整形）
- articles/F158_land_price_update/data/panel.csv：地価公示の2017〜2026年の地点×年の価格（F158 で整形）
- articles/F03_land_price_ml/data/features.csv：地点の特徴量（F03）
実行：python src/02_分析.py . ..  →  python src/03_図.py .
"""
print(__doc__)
