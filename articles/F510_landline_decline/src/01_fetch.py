"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「情報通信統計データベース」契約数の表と、令和8年版情報通信白書の図表のCSV。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
DB = "https://www.soumu.go.jp/johotsusintokei/field/data/{}"
WP = "https://www.soumu.go.jp/johotsusintokei/whitepaper/ja/r08/csv/{}"
FILES = [
    ("gt010205.xls", DB.format("gt010205.xls"), "加入電話及びISDNの加入数（1989年度末〜2026年6月末、全体とNTT東西）"),
    ("gt010206.xls", DB.format("gt010206.xls"), "IP電話利用数の推移（050-IP・0ABJ-IP、2003年12月末〜2026年6月末）"),
    ("gt01020101.xls", DB.format("gt01020101.xls"), "携帯電話・PHSの加入契約数の推移（単純合算、1988年度末〜2026年6月末）"),
    ("wp_r08_f00126.csv", WP.format("f00126.csv"), "令和8年版情報通信白書 図表II-1-2-9 音声通信サービスの加入契約数の推移（2016〜2025年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 情報通信統計データベース（契約数）：https://www.soumu.go.jp/johotsusintokei/field/tsuushin02.html",
              "- 令和8年版情報通信白書 音声通信サービスの加入契約数の状況：https://www.soumu.go.jp/johotsusintokei/whitepaper/ja/r08/html/nd212270.html",
              "", "出典：総務省「情報通信統計データベース」・「令和8年版 情報通信白書」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
