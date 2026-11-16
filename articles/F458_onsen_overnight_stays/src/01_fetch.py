"""環境省「温泉利用状況経年変化表」（PDF）を取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.env.go.jp/nature/onsen/pdf/6-7_p_3.pdf"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=120) as r:
        b = r.read()
    (RAW / "onsen_trend_table.pdf").write_bytes(b)
    today = datetime.date.today().isoformat()
    (RAW / "SOURCES.md").write_text("\n".join([
        "# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
        "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|",
        f"| onsen_trend_table.pdf | 環境省「温泉利用状況経年変化表」（昭和32年度〜令和6年度、令和7年3月末現在） | {URL} | {hashlib.sha256(b).hexdigest()[:12]} |", "",
        "- 掲載ページ：環境省「温泉利用状況等について」https://www.env.go.jp/nature/onsen/data/index.html",
        "- 表は PDF だけで公開されているため、src/01b_extract.py で文字を取り出して data/onsen_trend.csv を作った（pdftotext を使う。一度だけ流す）。",
        "  run_all.sh は data/onsen_trend.csv から先を流す。取り出しの確かめ（源泉総数 = 利用源泉の計 + 未利用源泉の計 など）は 01b_extract.py の中で行っている。"]) + "\n", encoding="utf-8")
    print("saved", len(b))

if __name__ == "__main__":
    main()
