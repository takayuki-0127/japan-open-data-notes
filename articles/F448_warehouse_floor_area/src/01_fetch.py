"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
国土交通省「建築着工統計調査」建築物着工統計 時系列表【建築物】構造別 用途別 都道府県別（年度、e-Stat）"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [("chakko_yoto_pref_fy_000040451302.xls", ES.format("000040451302", 0),
          "建築着工統計調査 建築物着工統計 時系列表【建築物】構造別 用途別 都道府県別（年度、1988〜2025年度、シートは年度ごと）")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=300) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- ファイル一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600120&tstat=000001016965（時系列表・年度次）",
              "- 令和6年度は「4月〜12月」「1月〜3月」の2シートに分かれている（02_build.py で足す）。",
              "- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
              "", "出典：国土交通省「建築着工統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
