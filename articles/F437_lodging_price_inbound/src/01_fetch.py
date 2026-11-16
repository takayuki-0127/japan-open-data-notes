"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
総務省「消費者物価指数」2025年基準 品目別価格指数（全国・東京都区部、月次）と、日本政府観光局（JNTO）「訪日外客数」。"""
import pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
FILES = {
    "cpi_zenkoku_item_monthly.csv": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1",
    "cpi_kubu_item_monthly.csv": "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482967&fileKind=1",
    "jnto_visitors_2003_2026.xlsx": "https://www.jnto.go.jp/statistics/data/_files/20261021_1615-5.xlsx",
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for f, u in FILES.items():
        (RAW / f).write_bytes(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120).read())


if __name__ == "__main__":
    main()
