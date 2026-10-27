"""データの取得元（ブラウザで取得して data/raw に置いた。コンテナからは各サイトに届かないため）

- 石油連盟「統計資料リスト 02. 石油製品バランス」paj-02_2610.xlsx（出所：経済産業省「資源・エネルギー統計」）
    https://www.paj.gr.jp/sites/default/files/2026-10/paj-02_2610.xlsx  シート「3.販売」ガソリン（kℓ、2017年1月〜2026年8月）
- 資源エネルギー庁「石油製品価格調査」週次ファイル 261021s5.xlsx（1990年8月〜2026年10月、レギュラー現金価格・全国、円/ℓ）
    https://www.enecho.meti.go.jp/statistics/petroleum_and_lpgas/pl007/xlsx/261021s5.xlsx
- 原油価格（ドバイ、ドル/バレル、月平均）：IMF Primary Commodity Prices（FRED: POILDUBUSDM）
    https://fred.stlouisfed.org/graph/fredgraph.csv?id=POILDUBUSDM
- ドル円（月中平均）：日本銀行 時系列統計データ（FM08 FXERM07）… 035/F39 で取得済みのもの
- 消費者物価指数（総合）：総務省 … F12 のデータマート（F39 の抽出）
- 家計調査（二人以上の世帯）ガソリンの支出金額（月次、2015年1月〜2026年8月）：e-Stat 長期時系列 000040270649〜51 … F11 で取得済み＋今回1本
"""
from common import RAW
need = ["paj-02_2610.xlsx", "261021s5.xlsx", "POILDUBUSDM.csv", "boj_prices_fx.csv", "cpi_f12.csv",
        "kakei_000040270649.csv", "kakei_000040270650.csv", "kakei_000040270651.csv"]
for n in need:
    p = RAW / n
    print(("OK " if p.exists() else "なし ") + n)
