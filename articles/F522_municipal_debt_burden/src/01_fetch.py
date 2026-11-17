"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「市町村別決算状況調」の 都市別・町村別 の「(1) 概況」と「(5) 地方債現在高等」（2009・2014・2019・2024年度）。"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
S = "https://www.soumu.go.jp/"
FILES = [  # (保存名, URL, 掲載ページ)
    ("2009_city_01.xls", S + "iken/zaisei/xls/h21_shichouson_01.xls", "h21"), ("2009_city_05.xls", S + "iken/zaisei/xls/h21_shichouson_05.xls", "h21"),
    ("2009_town_01.xls", S + "iken/zaisei/xls/h21_shichouson_06.xls", "h21"), ("2009_town_05.xls", S + "iken/zaisei/xls/h21_shichouson_10.xls", "h21"),
    ("2014_city_01.xls", S + "main_content/000402330.xls", "h26"), ("2014_city_05.xls", S + "main_content/000402334.xls", "h26"),
    ("2014_town_01.xls", S + "main_content/000402335.xls", "h26"), ("2014_town_05.xls", S + "main_content/000402339.xls", "h26"),
    ("2019_city_01.xlsx", S + "main_content/000738076.xlsx", "r01"), ("2019_city_05.xlsx", S + "main_content/000738080.xlsx", "r01"),
    ("2019_town_01.xlsx", S + "main_content/000738081.xlsx", "r01"), ("2019_town_05.xlsx", S + "main_content/000738085.xlsx", "r01"),
    ("2024_city_01.xlsx", S + "main_content/001061669.xlsx", "r06"), ("2024_city_05.xlsx", S + "main_content/001061673.xlsx", "r06"),
    ("2024_town_01.xlsx", S + "main_content/001061674.xlsx", "r06"), ("2024_town_05.xlsx", S + "main_content/001061678.xlsx", "r06"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | URL | 掲載ページ | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, page in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {url} | {S}iken/zaisei/{page}_shichouson.html | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- city＝都市別（市と東京23区を除く。政令市を含む）、town＝町村別。01＝(1)概況、05＝(5)地方債現在高等。",
              "- 一覧：https://www.soumu.go.jp/iken/kessan_jokyo_2.html", "", "出典：総務省「市町村別決算状況調」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
