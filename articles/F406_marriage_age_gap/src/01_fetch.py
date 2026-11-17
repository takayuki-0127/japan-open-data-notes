"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
厚生労働省「人口動態統計」（確定数）の婚姻の表（CSV、Shift_JIS）を e-Stat から取る。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
FILES = [
    ("000040503709", "vs2025_t9_14_first_marriage_age_gap.csv", "令和7年 上巻 婚姻 第9.14表 初婚夫妻の年齢差別にみた年次別婚姻件数及び百分率（1970〜2025年）"),
    ("000040503704", "vs2025_t9_11_mean_marriage_age.csv", "令和7年 上巻 婚姻 第9.11表 全婚姻－初婚別にみた年次別夫妻の平均婚姻年齢及び夫妻の年齢差（1899〜2025年）"),
    ("000040503722", "vs2025_m5_age_cross_2025.csv", "令和7年 中巻 婚姻 第5表 婚姻件数，夫妻の初婚－再婚の組合せ・妻の年齢（各歳）・夫の年齢（各歳）別"),
    ("000032018443", "vs2015_m5_age_cross_2015.csv", "平成27年 中巻 婚姻 第5表 婚姻件数，夫の同居時の年齢（各歳）・妻の同居時の年齢（各歳）・夫妻の初婚－再婚別"),
    ("000002615914", "vs2005_m4_age_cross_2005.csv", "平成17年 中巻 婚姻 第4表 婚姻件数，夫の同居時の年齢（各歳）・妻の同居時の年齢（各歳）・夫妻の初婚－再婚別"),
    ("000018895352", "vs1995_m4_age_cross_1995.csv", "平成7年 中巻 婚姻 第4表 婚姻件数，夫の同居時の年齢（各歳）・妻の同居時の年齢（各歳）・夫妻の初婚－再婚別"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for sid, name, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | 厚生労働省「人口動態統計」（確定数）{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：厚生労働省「人口動態統計」（確定数、e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
