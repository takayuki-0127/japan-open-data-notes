"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
厚生労働省「人口動態統計」（確定数、令和7年）上巻 婚姻 第9.18表 夫妻の国籍別にみた年次別婚姻件数（CSV、Shift_JIS）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040503714&fileKind=1"
NAME = "vs2025_t9_18_marriage_nationality.csv"


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=120) as r:
        b = r.read()
    (RAW / NAME).write_bytes(b)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|",
            f"| {NAME} | 厚生労働省「人口動態統計」（確定数、令和7年）上巻 婚姻 第9.18表 夫妻の国籍別にみた年次別婚姻件数（1965〜2025年） | {URL} | {hashlib.sha256(b).hexdigest()[:12]} |",
            "", "出典：厚生労働省「人口動態統計」（確定数、e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(NAME, len(b))


if __name__ == "__main__":
    main()
