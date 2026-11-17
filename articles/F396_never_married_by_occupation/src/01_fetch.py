"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「国勢調査」職業(大分類)×配偶関係×年齢(5歳階級)×男女別 15歳以上就業者数（2010・2015・2020年）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("census2010_t3_1_occ_marital.csv", "000014913541", 1, "平成22年国勢調査 職業等基本集計 第3-1表 職業(大分類)，配偶関係(3区分)，年齢(5歳階級)，男女別15歳以上就業者数－全国，都道府県"),
    ("census2015_t9_1_occ_marital.csv", "000031569366", 1, "平成27年国勢調査 就業状態等基本集計 第9-1表 職業(大分類)，配偶関係(3区分)，年齢(5歳階級)，男女別15歳以上就業者数－全国，都道府県ほか"),
    ("census2020_t9_1_occ_marital.xlsx", "000032201192", 0, "令和2年国勢調査 就業状態等基本集計 第9-1表 男女，年齢(5歳階級)，配偶関係，国籍総数か日本人，職業(大分類)別就業者数－全国，都道府県ほか"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, kind, desc in FILES:
        url = ES.format(sid, kind)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=300) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：総務省統計局「国勢調査」（平成22年・平成27年・令和2年、e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
