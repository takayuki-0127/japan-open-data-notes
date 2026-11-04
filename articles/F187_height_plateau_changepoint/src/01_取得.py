"""01 取得：年齢別の平均身長（学校保健統計調査 年次統計 表10）

元の表：文部科学省「学校保健統計調査」年次統計
  表10「年齢別 平均身長の推移（明治33年度〜令和7年度）」（e-Stat, toukei=00400002）
この Excel を年度×性×年齢の縦長に整形した表は、同じリポジトリの
articles/094_height/data/height_long.csv にある（094 の 02 整形で作成）。
このスクリプトはそれを取ってきて data/height_long.csv に置く。
data/ にすでに入っているので、普段は動かさなくてよい。
"""
from pathlib import Path
import urllib.request

URL = ("https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/"
       "main/articles/094_height/data/height_long.csv")
OUT = Path(__file__).resolve().parent.parent / "data" / "height_long.csv"

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        print("already exists:", OUT)
    else:
        urllib.request.urlretrieve(URL, OUT)
        print("saved:", OUT)
