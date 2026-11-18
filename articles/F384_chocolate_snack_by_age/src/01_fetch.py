"""01 取得（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない。data/raw に同梱済み）。
- 総務省「家計調査」家計収支編 二人以上の世帯 詳細結果表（年）第4-6表
  世帯主の年齢階級別1世帯当たり品目別支出金額、購入数量及び平均価格（2005〜2025年、1年1ファイル。チョコレート菓子が品目として載るのは2005年から）
- 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（月次、CSV）"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
T46 = {2005: "000000331B1C", 2006: "000000331D6E", 2007: "000001158916",
       2008: "000002209407", 2009: "000007370343", 2010: "000008635842", 2011: "000012687884", 2012: "000019023734", 2013: "000023621389",
       2014: "000028352478", 2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558",
       2020: "000032048838", 2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}
CPI = "000040482945"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    L = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
         "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, sid in T46.items():
        url = EST.format(sid, 0)
        b = get(url)
        name = f"kakei_4-6_{y}.{'xlsx' if b[:2] == b'PK' else 'xls'}"
        (RAW / name).write_bytes(b)
        L.append(f"| {name} | 家計調査 {y}年 二人以上の世帯 第4-6表 世帯主の年齢階級別 品目別支出金額・購入数量・平均価格 | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    url = EST.format(CPI, 1)
    b = get(url)
    (RAW / "cpi_item_monthly.csv").write_bytes(b)
    L.append(f"| cpi_item_monthly.csv | 消費者物価指数 2025年基準 全国 品目別価格指数（月次、Shift_JIS） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    L += ["", "- 家計調査 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001",
          "- 消費者物価指数 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200573",
          "- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
