"""01_取得：データの集め方

内閣府のサイトはこの分析の環境（コンテナ）から直接届かないため、ブラウザで 01_取得_browser.js を実行して
f73_watcher.json.gz を作り、data/raw/ に置く（または環境変数 F73_WATCHER でそのパスを指定する）。
- 景気判断理由集（現状 watcher4.csv・先行き watcher5.csv）：2010年1月〜2026年9月の201か月分（各月のページ）
- DI：原数値（watcher2-1.xls 現状、watcher2-4.xls 先行き の全国合計）と季節調整値（watcher5.xls）
景気動向指数（CI 一致）と景気基準日付は F13・F18 で取ったもの（data/raw/f13_ci.csv・cycle_dates.csv）を使う。
コメントの全文を含む f73_watcher.json.gz と data/_comments.parquet は GitHub には置いていない。
"""
from common import WATCHER_JSON
print("exists:", WATCHER_JSON.exists(), WATCHER_JSON)
