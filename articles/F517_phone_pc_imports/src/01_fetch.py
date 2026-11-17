"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
財務省「貿易統計」輸出入額の推移（主要商品別、年別、輸入）：世界・中国・ASEAN・米国。
日本銀行「外国為替市況」東京市場 ドル・円 スポット 17時時点／月中平均（時系列統計データ検索サイトの API）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
CU = "https://www.customs.go.jp/toukei/suii/html/data/{}"
FILES = [("d61ca.csv", CU.format("d61ca.csv"), "貿易統計 輸入 世界 年別 主要商品別（金額・数量）"),
         ("d62ca004.csv", CU.format("d62ca004.csv"), "貿易統計 輸入 中国 年別 主要商品別"),
         ("d62ca006.csv", CU.format("d62ca006.csv"), "貿易統計 輸入 ASEAN 年別 主要商品別"),
         ("d62ca001.csv", CU.format("d62ca001.csv"), "貿易統計 輸入 米国 年別 主要商品別"),
         ("boj_fxerm07.csv", "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=FM08&code=FXERM07&startDate=198801&endDate=202512",
          "日本銀行 東京市場 ドル・円 スポット 17時時点/月中平均（FXERM07、1988年1月〜2025年12月）")]


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
    lines += ["", "- 財務省貿易統計 輸出入額の推移：https://www.customs.go.jp/toukei/suii/html/time.htm",
              "- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/",
              "", "出典：財務省「貿易統計」、日本銀行「外国為替市況」。CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
