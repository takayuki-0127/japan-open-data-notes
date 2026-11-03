"""元データの取得。このリポジトリの過去の記事（F55・F86・F92）が作った推定結果・データを使い回す。
- F55：ベイズ構造時系列で出生数を予測したときのシミュレーション（年の出生数、2026〜2030年、4,000本の道筋）と、
        2010〜19年で学習して2020〜25年を予測したシミュレーション（月、72か月×4,000本）
        元データは厚生労働省「人口動態統計」2025年確定数 上巻 出生 第4.2表
- F86：日本版死亡データベース（国立社会保障・人口問題研究所）から整えた年齢別の死亡数・曝露人口
        （Lee–Carter の予測をここで同じ手順・同じ乱数の種でやり直す）
- F92：東京エリアの翌日ピーク需要の予測と実績（東京電力パワーグリッド「エリア需給実績」、気象庁の気温から F92 で作成）

F55 のシミュレーション（.npy の2つ）は F55 のリポジトリのフォルダに置いていないため、F55 の src/01_analysis.py が
書き出したものをこのフォルダの data/raw/ にそのまま置いている（f55_bsts_future_annual.npy・f55_bsts_2020_2025_monthly.npy）。
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "f55_annual_forecast.csv": "F55_births_bsts/results/A_annual_forecast.csv",
    "f55_monthly.csv": "F55_births_bsts/data/monthly.csv",
    "f86_mx_long.csv": "F86_lee_carter_e0/data/mx_long.csv",
    "f86_forecast_e0.csv": "F86_lee_carter_e0/results/forecast_e0.csv",
    "f92_pred_tokyo.csv": "F92_power_quantile_forecast/results/pred_tokyo.csv",
}
for name, path in FILES.items():
    out = RAW / name
    if not out.exists():
        urllib.request.urlretrieve(BASE + path, out)
    print(name, out.stat().st_size)
