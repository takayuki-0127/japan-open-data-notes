"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「住宅・土地統計調査」土地集計（現住居の敷地以外に所有する宅地など）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [  # (保存名, statInfId, 中身)
    ("hl2023_t252_1_use_japan", "000040260253", "令和5年 第252-1表 利用現況(13区分)別 宅地などを所有する主世帯数・所有件数・1件当たり面積－全国"),
    ("hl2023_t252_2_use_pref", "000040260254", "令和5年 第252-2表 利用現況(6区分)別 同－全国・都道府県・政令市"),
    ("hl2023_t249_acq_pref", "000040260250", "令和5年 第249表 取得方法(5区分)別 同－全国・都道府県・政令市"),
    ("hl2018_t253_1_use_japan", "000031917849", "平成30年 第253-1表 利用現況(13区分)別 宅地などを所有する普通世帯数・所有件数・1件当たり面積－全国"),
    ("hl2018_t253_2_use_pref", "000031917850", "平成30年 第253-2表 利用現況(6区分)別 同－全国・都道府県・政令市"),
    ("hl2018_t250_acq_pref", "000031917846", "平成30年 第250表 取得方法(5区分)別 同－全国・都道府県・政令市"),
    ("hl2013_t172_japan", "000028504645", "平成25年 第172表 所有形態・取得方法・取得時期・利用現況等別 同－全国"),
    ("hl2008_t145_japan", "000007372741", "平成20年 第145表 利用現況(12区分)等別 同－全国"),
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
        fn = name + (".xlsx" if b[:2] == b"PK" else ".xls")
        (RAW / fn).write_bytes(b)
        rows.append(f"| {fn} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(fn, len(b))
    rows += ["", "出典：総務省統計局「住宅・土地統計調査」（平成20年・平成25年・平成30年・令和5年）土地集計。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
