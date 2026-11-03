"""元データの取得。3つとも、このリポジトリの過去の記事（F02・F22・F68）が公的な出典から取得した表を使い回す。
- 出生数：厚生労働省「人口動態統計」2025年確定数 上巻 出生 第4.2表（F02）
- 電力需要：東京電力パワーグリッド「でんき予報」エリア需給実績＋気象庁の日平均気温（F22 が1時間ごとに整えた表）
- 訪日外客数：日本政府観光局（JNTO）「国籍/月別 訪日外客数（2003年～2026年）」（F68）
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {
    "births_monthly_2000_2025.csv": "F02_births_counterfactual/data/raw/births_monthly_2000_2025.csv",
    "hourly_tokyo.csv": "F22_power_demand_forecast/data/hourly_tokyo.csv",
    "jnto_monthly_2003_2026.csv": "F68_inbound_seasonality_clusters/data/raw/jnto_monthly_2003_2026.csv",
}
for name, path in FILES.items():
    out = RAW / name
    if not out.exists():
        urllib.request.urlretrieve(BASE + path, out)
    print(name, out.stat().st_size)
