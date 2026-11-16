"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 財務省「貿易統計」輸出入額の推移 世界 年別 輸入 主要商品別（金額・数量）d61ca.csv
- 日本銀行 時系列統計データ検索サイト API：ドル円（月中平均）、輸入物価指数（円ベース・契約通貨ベース）飲食料品・食料用農水産物と総平均
"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
FILES = {
    "d61ca.csv": "https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv",
    "boj_usdjpy_monthly.json": API.format(db="FM08", codes="FXERM07", s="198801", e="202512"),
    "boj_import_prices_monthly.json": API.format(db="PR01", codes="PRCG20_2600120001,PRCG20_2500120001,PRCG20_2600000000,PRCG20_2500000000", s="198801", e="202512"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read()
        if f.endswith(".json"):
            assert json.loads(b)["NEXTPOSITION"] is None
        (RAW / f).write_bytes(b)
        print(f, len(b))


if __name__ == "__main__":
    main()
