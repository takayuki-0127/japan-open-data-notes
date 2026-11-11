"""F243 01 取得：新しい取得はしない。既存の記事フォルダのデータを写して使う。
- data/raw/kakei_items_panel_f113.csv : 総務省「家計調査」品目別の年平均価格・購入数量・支出金額（二人以上の世帯、130品目、2002〜2024年）。
  F113 で整形し、F234 で使ったものと同じ（japan-open-data-notes/articles/F234_price_elasticity_practice/data/raw/）。
- data/raw/meti_dept_super_national.csv : 経済産業省「商業動態統計」百貨店・スーパーの全国・合計、販売額（百万円）と既存店の前年同月比（指数、前年=100）。
  F135 で取得したもの（articles/F135_rain_retail/data/retail_monthly.csv から抜き出し）。
再取得する場合は、F113・F135 の 01_取得 の手順に従う。
"""
import os
# - data/raw/item_fresh_flag_f234.csv : 品目が生鮮かどうかの印（F234 の data/panel_diff.csv の fresh 列）
for f in ["kakei_items_panel_f113.csv", "meti_dept_super_national.csv", "item_fresh_flag_f234.csv"]:
    p = os.path.join(os.path.dirname(__file__), "..", "data", "raw", f)
    print(f, "ok" if os.path.exists(p) else "missing")
