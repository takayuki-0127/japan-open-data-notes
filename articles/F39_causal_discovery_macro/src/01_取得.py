"""F39 データの取得

新しく取ったデータはありません。同じリポジトリのほかの記事で取ったものを data/raw/ にコピーしています。

- boj_prices_fx.csv : 035_yen_prices_var/data/raw/boj_prices_fx.csv
    日本銀行「時系列統計データ検索サイト」API（企業物価指数・輸入物価指数・ドル円、月次、2026-10-22 取得）
- f12_mart_extract.csv : F12_stats_pipeline の DuckDB（mart_indicators_monthly）から抜き出したもの
    総務省「消費者物価指数」（生鮮食品を除く総合）、総務省「労働力調査」（完全失業率・季節調整値）、
    厚生労働省「毎月勤労統計調査」（現金給与総額・所定内給与の前年同月比、事業所規模5人以上、調査産業計）
- f18_long_rate.csv : F18_nowcast_dfm/data/monthly_levels.csv の「長期金利」列
    内閣府「景気動向指数」個別系列データの長期国債（10年）新発債流通利回り（月末）

取り直すときは、それぞれの記事の src/01_取得.py を動かしてから、このスクリプトでコピーしてください。
"""
import shutil
from pathlib import Path
from common import RAW

REPO = Path(__file__).resolve().parents[2]  # articles/

SOURCES = {
    "boj_prices_fx.csv": REPO / "035_yen_prices_var" / "data" / "raw" / "boj_prices_fx.csv",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, src in SOURCES.items():
        if src.exists():
            shutil.copy(src, RAW / name)
            print("copied", name)
        else:
            print("not found (using the file already in data/raw):", src)
    # F12（DuckDB）と F18 の抜き出しは、各記事のデータを作ったあとに次で作り直せます
    try:
        import duckdb
        import pandas as pd
        db = REPO / "F12_stats_pipeline" / "data" / "stats.duckdb"
        if db.exists():
            c = duckdb.connect(str(db), read_only=True)
            c.sql("select month,cpi_all,cpi_core,cpi_core_yoy,cpi_all_yoy,unemp_rate_sa,wage_total_idx,"
                  "wage_total_yoy,wage_scheduled_yoy from mart_indicators_monthly order by month").df() \
                .to_csv(RAW / "f12_mart_extract.csv", index=False)
            print("rebuilt f12_mart_extract.csv")
        f18 = REPO / "F18_nowcast_dfm" / "data" / "monthly_levels.csv"
        if f18.exists():
            pd.read_csv(f18)[["month", "長期金利"]].to_csv(RAW / "f18_long_rate.csv", index=False)
            print("rebuilt f18_long_rate.csv")
    except ImportError:
        pass
