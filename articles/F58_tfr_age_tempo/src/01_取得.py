"""国立社会保障・人口問題研究所『人口統計資料集（2025年版）』の第4章の Excel を取得して CSV にする。

使う表（https://www.ipss.go.jp/syoushika/tohkei/Popular/Popular2025.asp?chap=4）
- 表4-9  女性の年齢（各歳）別出生率：1925～2023年（★のシート＝毎年）
- 表4-16 出生順位別合計特殊出生率および平均出生年齢：1950～2023年
- 表4-11 女性のコーホート別累積出生率：1947～2023年（★のシート＝毎年のコーホート）

記事を作ったときは、ブラウザのページの中で SheetJS を使って読み、data/raw/ に CSV として保存した。
このスクリプトは同じことを pandas で行う（研究所のサイトに直接つながる環境で動かす）。
"""
import pandas as pd
from common import RAW

BASE = "https://www.ipss.go.jp/syoushika/tohkei/Data/Popular2025/"
TABLES = {
    "T04-09": ("T04-09★", "ipss_T04-09_asfr_single_year.csv"),
    "T04-16": ("T04-16", "ipss_T04-16_tfr_by_order.csv"),
    "T04-11": ("T04-11★", "ipss_T04-11_cohort_cumulative.csv"),
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for t, (sheet, out) in TABLES.items():
        df = pd.read_excel(BASE + t + ".xlsx", sheet_name=sheet, header=None, dtype=str)
        df.to_csv(RAW / out, index=False, header=False, encoding="utf-8-sig")
        print(t, df.shape, "->", out)
