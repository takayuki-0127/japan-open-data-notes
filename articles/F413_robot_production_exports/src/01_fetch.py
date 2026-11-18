"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
1. 経済産業省「生産動態統計」年報（e-Stat 掲載分）：機械統計の時系列表（2012・2017・2020年版）と、全品目の年報（2021〜2025年版）→ data/raw/
2. 財務省「貿易統計」品別国別表（輸出、確定、16部 84-85類、1〜12月）2009〜2025年（e-Stat 掲載分、CSV）→ data/cache/（大きいので同梱しない。
   01b_extract.py で産業用ロボットの行だけを data/raw/customs_export_robots.csv に抜き出す）
3. 財務省 税関「Country code list」（国コードと国名・地域の対応、英語）→ data/raw/"""
import pathlib, urllib.request, hashlib, datetime, json

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, CACHE = ROOT / "data" / "raw", ROOT / "data" / "cache"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
PROD = [
    ("000022159804", "mach2012_ts1.xls", "2012年 年報 機械統計 時系列表その１（2008〜2012年。08 運搬機械及び産業用ロボット を含む）"),
    ("000031703015", "mach2017_ts1.xls", "2017年 年報 機械統計編 時系列表その１（2013〜2017年）"),
    ("000031961788", "mach2020_ts1.xls", "2020年 年報 機械統計編 時系列表その１（2016〜2020年）"),
    ("000032213834", "nenpo2021.xlsx", "2021年 年報（全品目の実数表。2017〜2021年の暦年の列を含む）"),
    ("000040077080", "nenpo2022.xlsx", "2022年 年報（同）"),
    ("000040191921", "nenpo2023.xlsx", "2023年 年報（同）"),
    ("000040293825", "nenpo2024.xlsx", "2024年 年報（月次）"),
    ("000040475159", "nenpo2025.xlsx", "2025年 年報（月次）"),
]
# 品別国別表（輸出）16部 84-85類 の各年 12月分（1〜12月の確定値。年の合計と月別の列がある）
CUSTOMS = {2009: "000007064263", 2010: "000008622880", 2011: "000012679340", 2012: "000018862129", 2013: "000023611819",
           2014: "000028156956", 2015: "000031362114", 2016: "000031528487", 2017: "000031670669", 2018: "000031792505",
           2019: "000031907283", 2020: "000032046051", 2021: "000032254729", 2022: "000040117436", 2023: "000040223224",
           2024: "000040368848", 2025: "000040524633"}
COUNTRY = ("https://www.customs.go.jp/toukei/sankou/code/country_e.htm", "customs_country_code_e.htm",
           "財務省 税関「Country code list - Trade Statistics of Japan」（国コード・国名・地域）")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "## 同梱しているファイル（data/raw/）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for sid, name, desc in PROD:
        url = ES.format(sid, 0); b = get(url); (RAW / name).write_bytes(b)
        rows.append(f"| {name} | 経済産業省「生産動態統計」{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        print(name, len(b))
    url, name, desc = COUNTRY; b = get(url); (RAW / name).write_bytes(b)
    rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
    rows += ["| customs_export_robots.csv | 下の品別国別表から、src/01b_extract.py で HS 8479.50（産業用ロボット（他の項に属しないもの））と HS 8428.70（産業用ロボット（持ち上げ・荷扱い用）、2017年から）の行だけを抜き出したもの | — | （01b_extract.py の実行で決まる） | — |",
             "", "## 同梱していないファイル（data/cache/、合計で約100MB）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    cache_meta = {}
    for y, sid in CUSTOMS.items():
        url = ES.format(sid, 1); b = get(url); name = f"customs_export_hs84_85_{y}.csv"
        (CACHE / name).write_bytes(b)
        h = hashlib.sha256(b).hexdigest()
        cache_meta[name] = {"url": url, "sha256": h, "bytes": len(b)}
        rows.append(f"| {name} | 財務省「貿易統計」{y}年分 品別国別表（輸出、1〜12月：確定）16部 84-85類（千円、CSV、Shift_JIS） | {url} | {h[:12]} | {len(b)} |")
        print(name, len(b))
    (CACHE / "cache_meta.json").write_text(json.dumps(cache_meta, indent=1), encoding="utf-8")
    rows += ["",
             "- e-Stat の一覧：生産動態統計 https://www.e-stat.go.jp/stat-search/files?toukei=00550200&tstat=000001022932 、普通貿易統計 https://www.e-stat.go.jp/stat-search/files?toukei=00350300&tstat=000001013141",
             "- 経済産業省のサイト（www.meti.go.jp/statistics/）は 2026-11-18 に 403 を返したため、同じ年報を e-Stat から取った。",
             "- 品別国別表の国コードは 103 韓国、105 中国、106 台湾、304 米国 など。対応は customs_country_code_e.htm。",
             "", "出典：経済産業省「生産動態統計」、財務省「貿易統計」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
