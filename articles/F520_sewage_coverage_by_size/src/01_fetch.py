"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 総務省「公共施設状況調経年比較表」市町村経年比較表（約45MB）→ data/download/（同梱しない）。src/01b_extract.py で使う列だけ抜き出す。
- 総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」市区町村別人口（2020年・2025年1月1日）。"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; DL = ROOT / "data" / "download"
FILES = [(DL, "municipal_keinen.xlsx", "https://www.soumu.go.jp/main_content/001068878.xlsx", "公共施設状況調経年比較表 市町村経年比較表（平成18年度〜令和6年度）。同梱せず、01b_extract.py で抜き出す"),
         (RAW, "jukijin_2025_municipal.xlsx", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040306653&fileKind=0", "住民基本台帳 2025年1月1日 【総計】市区町村別人口"),
         (RAW, "jukijin_2020_municipal.xls", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031971203&fileKind=0", "住民基本台帳 2020年1月1日 【総計】市区町村別人口")]


def main():
    RAW.mkdir(parents=True, exist_ok=True); DL.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for d, name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=300) as r:
            b = r.read()
        (d / name).write_bytes(b)
        lines.append(f"| {d.name}/{name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["| raw/sewage_extract.csv | 上の市町村経年比較表から src/01b_extract.py で「下水道等」の列だけを抜き出したもの（同梱） | — | — |", "",
              "- 公共施設状況調経年比較表：https://www.soumu.go.jp/iken/shisetsu/index.html",
              "- 国の発表（令和6年度末の汚水処理人口普及状況）：https://www.mlit.go.jp/report/press/mizukokudo13_hh_000669.html",
              "", "出典：総務省「公共施設状況調経年比較表」「住民基本台帳に基づく人口、人口動態及び世帯数調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
