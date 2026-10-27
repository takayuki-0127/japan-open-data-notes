"""01 取得：使うファイルの一覧と取得方法

コンテナからは e-Stat に直接つながらないため、2026年10月にブラウザのページの中で
SheetJS を使って読み、必要な行だけを JSON / CSV にして data/raw/ に置いた。
e-Stat に届く環境なら、下の URL から同じファイルを取り直せる。

- data/raw/kakei_age_3-2.json
    家計調査 詳細結果表 年次 第3-2表「世帯主の年齢階級別」2008〜2025年
    （シート：全国・二人以上の世帯／全国・勤労者世帯。平均と年齢区分の列、主な行だけ）
- data/raw/kakei_long_monthly_subset.csv
    家計調査 長期時系列 品目分類 支出金額（月）2000年1月〜2026年8月（二人以上の世帯、主な項目だけ）
- data/raw/cpi_subset.csv
    消費者物価指数 2020年基準 中分類 月次（全国）
"""
import sys
from common import STAT_IDS_3_2, STAT_ID_LONG, STAT_ID_CPI

URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"

if __name__ == "__main__":
    print("第3-2表（Excel）:")
    for y, sid in STAT_IDS_3_2.items():
        print(y, URL.format(sid, 0))
    print("長期時系列（CSV）:", URL.format(STAT_ID_LONG, 1))
    print("消費者物価指数（CSV）:", URL.format(STAT_ID_CPI, 1))
    print("取得済みのファイルは data/raw/ にあります。", file=sys.stderr)
