"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 国土交通省「建設工事費デフレーター（2020年度基準）」年度別（e-Stat）
- 国土交通省「建設工事費デフレーター（平成23年度基準）」表-3 個別デフレーターウエイト表（国交省サイト）
- 厚生労働省「毎月勤労統計調査」実数・指数累積データ：現金給与総額指数・総実労働時間指数（5人以上、就業形態計）
- 日本銀行「企業物価指数（2020年基準）」国内企業物価指数の類別（月次、API）
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
BOJ_CODES = ["PRCG20_2200000000", "PRCG20_2200320001", "PRCG20_2200620001", "PRCG20_2200720001",
             "PRCG20_2200820001", "PRCG20_2200920001", "PRCG20_2201020001", "PRCG20_2201120001"]
FILES = [
    ("deflator_fy2020base", ES.format("000040459205", 0), "建設工事費デフレーター（2020年度基準）時系列（年度別）"),
    ("deflator_weights_2011base.xlsx", "https://www.mlit.go.jp/common/001190414.xlsx", "建設工事費デフレーター（平成23年度基準）表-3 個別デフレーターウエイト表"),
    ("maikin_wage_index", ES.format("000032189720", 4), "毎月勤労統計調査 実数・指数累積データ 表7 現金給与総額 指数（5人以上、就業形態計、産業別シート）"),
    ("maikin_hours_index", ES.format("000032189742", 4), "毎月勤労統計調査 実数・指数累積データ 表29 総実労働時間 指数（5人以上、就業形態計、産業別シート）"),
    ("boj_cgpi2020_monthly.json", "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&startDate=198001&endDate=202612&code=" + ",".join(BOJ_CODES),
     "日本銀行 企業物価指数（2020年基準）国内企業物価指数 総平均と類別（木材・木製品、石油・石炭製品、プラスチック製品、窯業・土石製品、鉄鋼、非鉄金属、金属製品）月次"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        fn = name if "." in name else name + (".xlsx" if b[:2] == b"PK" else ".xls")
        (RAW / fn).write_bytes(b)
        rows.append(f"| {fn} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(fn, len(b))
    rows += ["", "出典：国土交通省「建設工事費デフレーター」、厚生労働省「毎月勤労統計調査」、日本銀行「企業物価指数」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
