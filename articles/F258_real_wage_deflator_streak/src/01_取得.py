"""データの入手先（記事 F101 で e-Stat から取得したファイルを再利用。新しい取得はしていない）。
このスクリプトはファイルの有無と大きさを確かめるだけ。

- cpi.csv  : 総務省「消費者物価指数」2020年基準 長期時系列（全国・月次の指数） e-Stat statInfId 000032103842
- wage.csv : 厚生労働省「毎月勤労統計調査」全国調査 長期時系列（指数・伸び率）
             調査産業計・事業所規模5人以上・就業形態計 e-Stat statInfId 000032189777
"""
from common import RAW
for f in sorted(RAW.iterdir()):
    print(f"{f.name:12s} {f.stat().st_size:>10,d} bytes")
