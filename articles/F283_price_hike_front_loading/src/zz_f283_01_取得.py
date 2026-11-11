"""F283 01 取得：元データの確認（md5）。

data/raw の4つのファイル：
- kakei_items_monthly_2015_2026.csv：家計調査 長期時系列表 品目分類 支出金額（月）
  e-Stat statInfId 000040270649（2015〜2019年）・000040270650（2020〜2024年）・000040270651（2025年〜）
  を2026-11-11 にブラウザで取得し、必要な行だけ残したもの（Shift_JIS → UTF-8）。
- kakei_3X7_2025_2026.csv：000040270651 の符号 3X7（2025年改定で名前が「発泡酒」）の1行。
- cpi_items_monthly_f209.csv.gz / cpi_items_meta_f209.csv：消費者物価指数 2020年基準 品目指数（月）。F209 で取得したもの。

取り直す場合は https://www.e-stat.go.jp/stat-search/file-download?statInfId=<id>&fileKind=1 から
CSV を取り、品目分類の列で同じ行を抜き出す。
"""
import hashlib
import pathlib

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
EXPECT = {
    "kakei_items_monthly_2015_2026.csv": "a41962e414b31762e2fdd98697ba633d",
    "kakei_3X7_2025_2026.csv": "cafb8dcdcf8bff5365e970f652174d20",
    "cpi_items_monthly_f209.csv.gz": "ffbfbb4be39f6e27e7012038f3d7819f",
    "cpi_items_meta_f209.csv": "0571a720092dda6836c7f2aba3afad63",
}
for name, md5 in EXPECT.items():
    got = hashlib.md5((RAW / name).read_bytes()).hexdigest()
    print(name, got, "OK" if got == md5 else "MISMATCH")
    assert got == md5, name
