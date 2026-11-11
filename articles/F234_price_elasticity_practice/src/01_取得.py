"""F234 取得：新しい取得はしない。
- data/raw/kakei_items_panel_f113.csv：F113（articles/F113_price_index_formulas/data/items_panel.csv）の家計調査 品目別の
  年平均価格・購入数量・支出金額（二人以上の世帯、2002〜2024年、130品目）をそのまま写したもの
- data/raw/boj_import_prices_fx.csv：F210（articles/F210_prices_household_series_part2/data/raw/boj_import_prices_fx_tankan.csv）
  から、輸入物価指数（円ベース：総平均・飲食料品・石油石炭天然ガス）とドル円の月次を取り出したもの（日本銀行 時系列統計データ検索サイト API）
"""
import shutil, pathlib
here = pathlib.Path(__file__).resolve().parents[1]
repo = here.parent  # articles/
src = repo / "F113_price_index_formulas" / "data" / "items_panel.csv"
if src.exists():
    shutil.copy(src, here / "data" / "raw" / "kakei_items_panel_f113.csv")
print("data/raw を確認してください")
