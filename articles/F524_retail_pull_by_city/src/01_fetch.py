"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [("shogyo2014_municipal.xlsx", "000031357335", "商業統計 2014年 第3巻 産業編（市区町村表）第1表 区市郡別・第2表 町村別"),
         ("ecensus2021_city.xlsx", "000040032863", "令和3年経済センサス‐活動調査 卸売業，小売業 産業編（市区町村表）DB1 産業小分類別（全国、都道府県、市区、郡部）"),
         ("ecensus2021_town.xlsx", "000040032864", "令和3年経済センサス‐活動調査 卸売業，小売業 産業編（市区町村表）DB2 産業分類別（全国、都道府県、市部、町村）"),
         ("census2020_t1_1.xlsx", "000040317616", "令和2年国勢調査 人口等基本集計 第1-1表（市区町村別の人口、2015年の人口（組替））"),
         ("census2020_t1_3.xlsx", "000040317618", "令和2年国勢調査 人口等基本集計 第1-3表（大都市圏の中心市と周辺市町村）"),
         ("census2020_t1_4.xlsx", "000040317619", "令和2年国勢調査 人口等基本集計 第1-4表（都市圏の中心市と周辺市町村）")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = ES.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：経済産業省「商業統計」、総務省・経済産業省「経済センサス‐活動調査」、総務省「国勢調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
