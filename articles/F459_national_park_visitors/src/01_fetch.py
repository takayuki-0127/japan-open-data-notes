"""環境省「自然公園等利用者数調」の Excel を取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.env.go.jp/park/doc/data/natural/{}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
FILES = [("naturalpark_02.xlsx", "自然公園の公園数、年間利用者数の推移（昭和26年〜令和6年）"),
         ("naturalpark_04.xlsx", "国立公園利用者数（公園、年次別）（昭和46年〜令和6年、万人）"),
         ("naturalpark_12.xlsx", "国立公園別訪日外国人利用者数推計値（参考）")]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, desc in FILES:
        url = BASE.format(name)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 環境省「自然公園等利用者数調」{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", name, len(b))
    lines += ["", "- 掲載ページ：環境省「自然公園の統計」https://www.env.go.jp/park/doc/data.html",
              "- 出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
