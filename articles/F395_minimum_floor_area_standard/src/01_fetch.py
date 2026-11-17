"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「住宅・土地統計調査」最低居住面積水準・誘導居住面積水準の状況（2008・2013・2018・2023年）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("h2008_t57_tenure_size_japan", "000007372641", "平成20年 第57表 住宅の所有の関係・建て方、世帯人員、最低居住面積水準・誘導居住面積水準状況別主世帯数－全国"),
    ("h2008_t12_pref", "000007372761", "平成20年 第12表 最低居住面積水準・誘導居住面積水準状況別主世帯数－全国、都道府県、18大都市"),
    ("h2013_t68_tenure_size_japan", "000028504532", "平成25年 第68表 住宅の所有の関係・建て方、世帯人員、水準状況別主世帯数－全国"),
    ("h2013_t12_pref", "000028504668", "平成25年 第12表 水準状況別主世帯数－全国、都道府県、21大都市"),
    ("h2018_t76_1_tenure_size", "000031865799", "平成30年 第76-1表 住宅の所有の関係、世帯人員、水準状況別主世帯数－全国、都道府県、21大都市"),
    ("h2023_t75_1_tenure_size", "000040209973", "令和5年 第75-1表 住宅の所有の関係、世帯人員、水準状況別主世帯数－全国、都道府県、21大都市"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = ES.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        fn = name + (".xlsx" if b[:2] == b"PK" else ".xls")
        (RAW / fn).write_bytes(b)
        rows.append(f"| {fn} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(fn, len(b))
    rows += ["", "出典：総務省統計局「住宅・土地統計調査」（平成20年・平成25年・平成30年・令和5年、e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
