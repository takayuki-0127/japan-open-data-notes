"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
厚生労働省「人口動態統計」（確定数、令和7年）上巻の年次別の表（CSV、Shift_JIS）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
FILES = [
    ("vs2025_t10_5_divorce_duration.csv", "000040503733", "人口動態統計 上巻 離婚 第10.5表 年次別にみた同居期間別離婚件数及び百分率並びに平均同居期間（1947〜2025年）"),
    ("vs2025_t9_5_marriage_first_re.csv", "000040503697", "人口動態統計 上巻 婚姻 第9.5表 夫妻の初婚－再婚の組合せ別にみた年次別婚姻件数及び百分率（1952〜2025年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = ES.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：厚生労働省「人口動態統計」（確定数、e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
