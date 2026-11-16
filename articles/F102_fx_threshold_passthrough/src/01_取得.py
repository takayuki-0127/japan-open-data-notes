"""F102 取得：新しく取ったデータはない。同じリポジトリの記事で取ったものを data/raw/ にコピーして使う。

- data/raw/boj_prices_fx.csv : 日本銀行 時系列統計データ（企業物価指数・ドル円）。035 と F39 で取得したもの
    FXERM07            東京市場 ドル・円 スポット 17時時点／月中平均
    PRCG20_2200000000  国内企業物価指数 総平均（2020年=100）
    PRCG20_2500000000  輸入物価指数 契約通貨ベース 総平均
    PRCG20_2600000000  輸入物価指数 円ベース 総平均
- data/raw/f12_mart_extract.csv : 総務省 消費者物価指数（生鮮食品を除く総合、2020年=100）ほか。F12 のデータマートから F39 が抜き出したもの

元のファイルは articles/F39_causal_discovery_macro/data/raw/ にあった。F39 は削除済みの記事（削除前の版：https://github.com/takayuki-0127/japan-open-data-notes/tree/c56ebc67126a738058bdae7c172e7b29473f9286/articles/F39_causal_discovery_macro）。
"""
import shutil
import urllib.request
from pathlib import Path
from common import RAW

SRC = Path(__file__).resolve().parents[2] / "F39_causal_discovery_macro" / "data" / "raw"
if SRC.exists():
    for f in ["boj_prices_fx.csv", "f12_mart_extract.csv"]:
        shutil.copy(SRC / f, RAW / f)
        print("copied", f)
else:
    # F39 の記事フォルダは削除したので、手元にないときは削除前の版（コミット c56ebc6）から取る
    for f in ["boj_prices_fx.csv", "f12_mart_extract.csv"]:
        urllib.request.urlretrieve("https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/c56ebc67126a738058bdae7c172e7b29473f9286/articles/F39_causal_discovery_macro/data/raw/" + f, RAW / f)
        print("取得（削除前の版）", f)
