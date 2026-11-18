"""元データを e-Stat から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
国土交通省「航空輸送統計調査」年報の 統計表2（国内定期航空 月別）と 統計表5（国際航空 月別）、2014〜2025年。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
# 年: (表2 の statInfId, 表5 の statInfId, fileKind)。2020年は fileKind=4 の Excel だけがある
FILES = {
    2014: ("000031507073", "000031507076", 0), 2015: ("000031487796", "000031487799", 0),
    2016: ("000031607433", "000031607436", 0), 2017: ("000031730080", "000031730083", 0),
    2018: ("000031842368", "000031842371", 0), 2019: ("000031959670", "000031959673", 0),
    2020: ("000032104086", "000032104089", 4), 2021: ("000032211478", "000032211481", 0),
    2022: ("000040074177", "000040074180", 0), 2023: ("000040191397", "000040191400", 0),
    2024: ("000040290548", "000040290551", 0), 2025: ("000040471583", "000040471586", 0),
}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, (t2, t5, kind) in FILES.items():
        for sid, tab, desc in ((t2, "t2", "統計表2 国内定期航空月別運航及び輸送実績"), (t5, "t5", "統計表5 国際航空月別運航及び輸送実績")):
            url = BASE.format(sid, kind)
            b = get(url)
            ext = "xlsx" if b[:2] == b"PK" else "xls"
            name = f"air_{y}_{tab}.{ext}"
            (RAW / name).write_bytes(b)
            lines.append(f"| {name} | {y}年 航空輸送統計年報 {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
            print("saved", name, len(b))
    lines += ["", "- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600360&tstat=000001018894",
              "- 出典：国土交通省「航空輸送統計調査」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- 調査の対象は日本の航空会社（本邦航空運送事業者）。国際線は日本の会社の便だけで、外国の航空会社の便は入らない。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
