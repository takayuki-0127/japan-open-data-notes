"""データの取得。
- ドル円：日本銀行 時系列統計データ検索サイトの API（FM08 外国為替市況、FXERD04＝東京市場 ドル・円 スポット 17時時点、日次）
- 日経平均：FRED の NIKKEI225（出所 日本経済新聞社、終値、日次）
日経平均のデータは日本経済新聞社の著作物のため、このリポジトリには入れていません。
このスクリプトを実行すると data/raw/ に保存されます（ご自身の環境での分析用）。
"""
import io
import requests
import pandas as pd
from common import RAW

def boj():
    url = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode"
           "?format=csv&lang=en&db=FM08&code=FXERD04&startDate=198001")
    t = requests.get(url, timeout=60).text
    rows = [l.split(",") for l in t.splitlines() if l.startswith("FXERD04,")]
    df = pd.DataFrame({"date": [r[-2] for r in rows], "usdjpy_1700": [r[-1] for r in rows]})
    df = df[df.usdjpy_1700 != "null"]
    df.to_csv(RAW / "boj_fm08_fxerd04.csv", index=False)

def fred():
    t = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=NIKKEI225", timeout=60).text
    df = pd.read_csv(io.StringIO(t))
    df[df.observation_date >= "1997-12-01"].to_csv(RAW / "fred_nikkei225.csv", index=False)

if __name__ == "__main__":
    boj(); fred()
