"""F102 取得：新しく取ったデータはない。同じリポジトリの記事で取ったものを data/raw/ にコピーして使う。

- data/raw/boj_prices_fx.csv : 日本銀行 時系列統計データ（企業物価指数・ドル円）。035 と F39 で取得したもの
    FXERM07            東京市場 ドル・円 スポット 17時時点／月中平均
    PRCG20_2200000000  国内企業物価指数 総平均（2020年=100）
    PRCG20_2500000000  輸入物価指数 契約通貨ベース 総平均
    PRCG20_2600000000  輸入物価指数 円ベース 総平均
- data/raw/f12_mart_extract.csv : 総務省 消費者物価指数（生鮮食品を除く総合、2020年=100）ほか。F12 のデータマートから F39 が抜き出したもの

元のファイルは articles/F39_causal_discovery_macro/data/raw/ にある。
"""
import shutil
from pathlib import Path
from common import RAW

SRC = Path(__file__).resolve().parents[2] / "F39_causal_discovery_macro" / "data" / "raw"
if SRC.exists():
    for f in ["boj_prices_fx.csv", "f12_mart_extract.csv"]:
        shutil.copy(SRC / f, RAW / f)
        print("copied", f)
else:
    print("F39 のフォルダがないので、data/raw/ に置いてあるファイルをそのまま使う")
