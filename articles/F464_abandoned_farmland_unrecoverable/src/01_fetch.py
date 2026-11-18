"""農林水産省「荒廃農地の発生・解消状況に関する調査」の各年の公表資料（PDF）を取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
B = "https://www.maff.go.jp/j/nousin/tikei/houkiti/"
PAGE = B + "index.html"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
# 調査の年（2021年からは年度）: (URL の相対パス, 公表資料の題)
FILES = {
    2011: ("pdf/kouhyo6.pdf", "平成23年の荒廃農地に関する調査の結果について"),
    2012: ("pdf/00_kouhyo25_tougou.pdf", "平成24年の荒廃農地の面積について"),
    2013: ("pdf/00_kouhyo26_tougou.pdf", "平成25年の荒廃農地の面積について"),
    2014: ("pdf/kouhyo27_tougou.pdf", "平成26年の荒廃農地の面積について"),
    2015: ("attach/pdf/index-1.pdf", "平成27年の荒廃農地面積について"),
    2016: ("attach/pdf/index-5.pdf", "平成28年の荒廃農地面積について"),
    2017: ("attach/pdf/index-3.pdf", "平成29年の荒廃農地面積について"),
    2018: ("attach/pdf/index-6.pdf", "平成30年の荒廃農地面積について"),
    2019: ("attach/pdf/index-7.pdf", "令和元年の荒廃農地面積について"),
    2020: ("attach/pdf/index-17.pdf", "令和2年の荒廃農地面積について"),
    2021: ("attach/pdf/index-9.pdf", "令和3年度の荒廃農地面積について"),
    2022: ("attach/pdf/index-18.pdf", "令和4年度の荒廃農地面積について"),
    2023: ("attach/pdf/index-33.pdf", "令和5年度の荒廃農地面積について"),
    2024: ("attach/pdf/index-47.pdf", "令和6年度の荒廃農地面積について"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, (rel, title) in FILES.items():
        url = B + rel
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        (RAW / f"kouhai_{y}.pdf").write_bytes(b)
        lines.append(f"| kouhai_{y}.pdf | {title}（公表資料。資料2が都道府県別の表） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", y, len(b), flush=True)
    lines += ["", f"- 掲載ページ：{PAGE}",
              "- 出典：農林水産省「荒廃農地の発生・解消状況に関する調査」（2021年度からは「遊休農地に関する措置の状況に関する調査」とあわせた集計）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "- 2011〜2020年は暦年の調査（各年の11月30日現在など）、2021年度からは年度末（3月30日・31日）現在。2021年度の調査から調査内容が見直されている（農水省の注記）。",
              "- PDF の表は src/01b_extract.py（pdftotext 24.02.0 を使う）で data/kouhai_pref_raw.csv に抜き出した。run_all.sh はこの CSV から先だけを流す。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
