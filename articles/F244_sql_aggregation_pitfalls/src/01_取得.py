"""01 取得：この記事では新しい取得はしない。
- data/raw/retail_national_2014_2026.csv：経済産業省「商業動態統計」（全国・月次の販売額、百万円）。F135 で取得し F232 で整えたものをそのまま使う
  （japan-open-data-notes/articles/F232_hierarchical_retail_reconciliation/data/raw/ と同じファイル）
- data/raw/f232_nodes.csv：F232 で作った品目の階層表（どの品目が「いちばん細かい単位」か）
- data/raw/holidays_jp.csv：国民の祝日（内閣府「国民の祝日」に基づく。F233 で Python の jpholiday から作成）
- 注文データは架空のネット書店「あおば書店（架空）」のシミュレーションで、02_整形.py が作る
"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for f in ["retail_national_2014_2026.csv", "f232_nodes.csv", "holidays_jp.csv"]:
    p = os.path.join(ROOT, "data", "raw", f)
    print(f, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else None)
