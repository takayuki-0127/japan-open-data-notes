"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校基本調査」（e-Stat の Excel）と、文部科学省のページ「高等学校学科別生徒数・学校数」（照合用）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
SHO = {1985: "000029084361", 1990: "000029026357", 1995: "000023596318", 2000: "000015170293", 2005: "000002946746",
       2010: "000008349767", 2015: "000031357906", 2020: "000032040519", 2025: "000040393789"}
FILES = [(f"gakko_{y}_shogakka." + ("xlsx" if y >= 2015 else "xls"), BASE.format(i), f"{y}年度 高等学校 小学科別生徒数（本科）")
         for y, i in SHO.items()]
FILES += [("gakko_2010_pref_gakka.xls", BASE.format("000012449302"), "2010年度 高等学校 都道府県別学科別学年別生徒数（本科）"),
          ("gakko_2025_pref_gakka.xlsx", BASE.format("000040393253"), "2025年度 高等学校 都道府県別 学科別学年別生徒数（本科）（表番号 ey-168）"),
          ("mext_gakka_page.html", "https://www.mext.go.jp/a_menu/shotou/shinkou/genjyo/021201.htm",
           "文部科学省「高等学校学科別生徒数・学校数」（照合用。学科別の構成比の推移）")]


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
    lines += ["", "出典：文部科学省「学校基本調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400001&tstat=000001011528）。各年度5月1日時点。",
              "照合用：文部科学省「高等学校学科別生徒数・学校数」https://www.mext.go.jp/a_menu/shotou/shinkou/genjyo/021201.htm"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
