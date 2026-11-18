"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
経済産業省「商業統計」（e-Stat の Excel）と、総務省統計局「消費者物価指数」（暦年の類別指数、e-Stat の CSV）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("shogyo_ts_pref_1972_2004.xls", URL.format("000002298158", 0), "商業統計 その他のデータ（時系列）表2 都道府県別（昭和47年～平成16年）"),
    ("shogyo_gyotai_pref_1991_1997.xls", URL.format("000002298159", 0), "商業統計 その他のデータ（時系列）表3 業態別、都道府県別（平成3年、6年、9年）"),
    ("shogyo_gyotai_pref_1999_2004.xls", URL.format("000002298160", 0), "商業統計 その他のデータ（時系列）表4 業態別、都道府県別（平成11年、14年、16年）"),
    ("shogyo_2007_gyotai.xls", URL.format("000006742472", 0), "平成19年商業統計 業態別統計編（小売業）業態別統計表"),
    ("shogyo_2014_gyotai.xlsx", URL.format("000031386576", 0), "平成26年商業統計 業態別統計編（小売業）統計表（参考）"),
    ("cpi_2025base_annual_class.csv", URL.format("000040482829", 1), "消費者物価指数 2025年基準 中分類指数 年平均（暦年）（CSV、Shift_JIS）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：経済産業省「商業統計」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00550020）、",
              "総務省統計局「消費者物価指数」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200573）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
