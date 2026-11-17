"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 財務省「貿易取引通貨別比率」時系列 CSV（輸出・輸入、半期、2000年下半期〜）
- 財務省「貿易統計」輸出入額の推移 月別 輸出（世界 d51ma、米国 d52ma001、EU d52ma002、アジア d52ma003）
- 日本銀行 ドル円（月中平均）
"""
import json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
FILES = {
    "timeseriesSCT_e.csv": "https://www.customs.go.jp/toukei/shinbun/tuuka/timeseriesSCT_e.csv",
    "timeseriesSCT_i.csv": "https://www.customs.go.jp/toukei/shinbun/tuuka/timeseriesSCT_i.csv",
    **{f"{k}.csv": f"https://www.customs.go.jp/toukei/suii/html/data/{k}.csv" for k in ["d51ma", "d52ma001", "d52ma002", "d52ma003"]},
    "boj_usdjpy_monthly.json": "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=200001&endDate=202606",
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
