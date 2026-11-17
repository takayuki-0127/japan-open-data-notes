"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、1970年1月〜、CSV）。e-Stat。
- 日本銀行 ドル円（月中平均）。"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
FILES = {"cpi_item_monthly.csv": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1",
         "boj_usdjpy_monthly.json": "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=200001&endDate=202609"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        (RAW / f).write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=180).read())


if __name__ == "__main__":
    main()
