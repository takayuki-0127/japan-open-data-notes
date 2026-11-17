"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 国土交通省「建設総合統計」年度報（e-Stat）1996・2005・2015・2023年度
- 内閣府「県民経済計算」総括表 1. 県内総生産（名目）：1996〜2009年度版（平成12年基準）と 2011〜2023年度版（2015年基準）"""
import pathlib, urllib.request, hashlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
KM = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/"
FILES = [("nendo_1996.xls", ES.format("000001661823", 0), "建設総合統計 年度報 1996（平成8）年度"),
         ("nendo_2005.xls", ES.format("000001261515", 0), "建設総合統計 年度報 2005（平成17）年度"),
         ("nendo_2015.xlsx", ES.format("000032217667", 4), "建設総合統計 年度報 2015年度（2013年4月〜2022年5月の推計値）"),
         ("nendo_2023.xlsx", ES.format("000040286446", 4), "建設総合統計 年度報 2023年度（2025年度遡及値）"),
         ("gdp_1996_2009.xls", KM + "h20/soukatu1_1.xls", "県民経済計算 総括表 県内総生産（名目）1996〜2009年度（1993SNA・平成12年基準）"),
         ("gdp_2011_2023.xlsx", KM + "2023/soukatu1.xlsx", "県民経済計算 総括表 県内総生産（名目）2011〜2023年度（2008SNA・2015年基準）")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：国土交通省「建設総合統計」、内閣府「県民経済計算」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
