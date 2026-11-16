"""01：データの取得。この記事は 037 と同じ「不動産取引価格情報」（東京都・中古マンション等、2015年1〜3月期〜2026年1〜3月期）を使う。
GitHub の 037 のフォルダから zip を取ってきて data/raw に置く（元データは国土交通省 不動産情報ライブラリでダウンロードしたもの）。"""
from pathlib import Path
import urllib.request
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
# 037 の記事フォルダは削除したので、削除前の版（コミット c56ebc6）から取る
URL = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/c56ebc67126a738058bdae7c172e7b29473f9286/articles/037_tokyo_condo_hedonic/data/raw/Tokyo_20151_20261.zip"
f = RAW / "Tokyo_20151_20261.zip"
if not f.exists():
    urllib.request.urlretrieve(URL, f)
print(f, f.stat().st_size)
