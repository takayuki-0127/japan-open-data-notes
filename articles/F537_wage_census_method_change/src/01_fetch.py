"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
厚生労働省「賃金構造基本統計調査」：遡及集計（厚労省のサイト）、令和元年・令和2年の表と時系列表（e-Stat）。"""
import datetime, hashlib, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MH = "https://www.mhlw.go.jp/toukei/itiran/roudou/chingin/kouzou/detail/xls/{}"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("new_sokyu01_2015_2019.xlsx", MH.format("sokyu-01.xlsx"), "遡及集計（令和2年と同じ推計方法）第1表 一般労働者の産業大分類、性、学歴、年齢階級、企業規模別 2015〜2019年"),
    ("new_sokyu01_2009_2014.xlsx", MH.format("sokyu-01_2.xlsx"), "同 2009〜2014年"),
    ("new_sokyu01_2006_2008.xlsx", MH.format("sokyu-01_3.xlsx"), "同 2006〜2008年"),
    ("old_2019_t1.xls", ES.format("000031919751"), "令和元年調査 一般労働者 産業大分類 第1表 年齢階級別きまって支給する現金給与額、所定内給与額及び年間賞与その他特別給与額（産業計・産業別）"),
    ("old_timeseries_t3.xls", ES.format("000031919945"), "時系列表 第3表 所定内給与額の推移（昭和51年〜令和元年、男女計・男・女）"),
    ("new_2020_t1.xls", ES.format("000032069350"), "令和2年調査 一般労働者 産業大分類 第1表 年齢階級別きまって支給する現金給与額、所定内給与額及び年間賞与その他特別給与額"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        time.sleep(1)
    lines += ["",
              "- 遡及集計の説明：厚生労働省「令和2年賃金構造基本統計調査の変更に伴う遡及集計について」https://www.mhlw.go.jp/toukei/itiran/roudou/chingin/kouzou/detail/sokyu.html",
              "- 令和2年調査の変更点：同「令和2年調査の変更点」https://www.mhlw.go.jp/toukei/itiran/roudou/chingin/kouzou/detail/chousa_change.html",
              "- e-Stat の統計表一覧：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00450091&tstat=000001011429",
              "", "出典：厚生労働省「賃金構造基本統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
