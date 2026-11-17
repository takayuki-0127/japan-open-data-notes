"""観光庁「宿泊旅行統計調査」の年の確定値（集計結果 Excel）を取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.mlit.go.jp/kankocho/content/{}.xlsx"
PAGE = "https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
IDS = {2015: "002026815", 2016: "002026813", 2017: "002026811", 2018: "002026795", 2019: "002026792",
       2022: "002026772", 2023: "002026766", 2024: "002026764", 2025: "002026762"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, i in IDS.items():
        url = BASE.format(i)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
            b = r.read()
        (RAW / f"shukuhaku_{y}.xlsx").write_bytes(b)
        lines.append(f"| shukuhaku_{y}.xlsx | 宿泊旅行統計調査 {y}年1〜12月分（年の確定値）集計結果 | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", y, len(b), flush=True)
    lines += ["", f"- 掲載ページ：{PAGE}",
              "- 出典：観光庁「宿泊旅行統計調査」。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- 2020・2021年はコロナの影響が大きいので取得していない。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
