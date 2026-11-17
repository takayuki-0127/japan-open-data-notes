"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 総務省「公共施設状況調経年比較表」市町村経年比較表（平成18年度〜令和6年度）。約45MBあるので data/download/ に置き、
  src/01b_extract.py で使う列だけを data/raw/municipal_extract.csv に抜き出す（data/download/ は同梱しない）。
- 総務省「人口推計」都道府県別人口（各年10月1日現在）：長期時系列 第5表（2000〜2020年）と2024年 第5表（2020〜2024年）。"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; DL = ROOT / "data" / "download"
FILES = [
    (DL, "municipal_keinen.xlsx", "https://www.soumu.go.jp/main_content/001068878.xlsx", "公共施設状況調経年比較表 市町村経年比較表（平成18年度〜令和6年度）。同梱せず、01b_extract.py で抜き出す"),
    (RAW, "pop_pref_2000_2020.xlsx", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000013168605&fileKind=4", "人口推計 長期時系列 第5表 都道府県別人口（各年10月1日現在、2000〜2020年）"),
    (RAW, "pop_pref_2020_2024.xlsx", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040268859&fileKind=0", "人口推計 2024年 第5表 都道府県、男女別人口（各年10月1日現在）"),
]


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
    lines += ["| raw/municipal_extract.csv | 上の市町村経年比較表から、src/01b_extract.py で使う列だけを抜き出したもの（同梱） | — | — |", "",
              "- 公共施設状況調経年比較表：https://www.soumu.go.jp/iken/shisetsu/index.html",
              "- 人口推計：https://www.e-stat.go.jp/stat-search/files?toukei=00200524&tstat=000000090001",
              "", "出典：総務省「公共施設状況調経年比較表」「人口推計」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
