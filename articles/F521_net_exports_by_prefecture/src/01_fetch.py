"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
内閣府「県民経済計算」（2011〜2023年度）主要系列表 1（経済活動別県内総生産・名目）と 4（県内総生産・支出側・名目）。"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BASE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2023/"
FILES = [("syuyo1.xlsx", "1. 経済活動別県内総生産（名目）2011〜2023年度（年度ごとのシート）"),
         ("syuyo4.xlsx", "4. 県内総生産（支出側、名目）2011〜2023年度（年度ごとのシート）")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, desc in FILES:
        url = BASE + name
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 掲載ページ：https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/main_2023.html",
              "", "出典：内閣府「県民経済計算」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
