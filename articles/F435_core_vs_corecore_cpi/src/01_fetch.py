"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、1970年1月〜、CSV、Shift_JIS）。e-Stat。
（総合・生鮮食品を除く総合・生鮮食品及びエネルギーを除く総合・食料（酒類を除く）及びエネルギーを除く総合・エネルギーの列を使う）"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "cpi_item_monthly.csv").write_bytes(urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=180).read())


if __name__ == "__main__":
    main()
