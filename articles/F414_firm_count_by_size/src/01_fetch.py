"""元データを e-Stat から取る（run_all.sh では呼ばない）。"""
import hashlib, pathlib, urllib.request, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("census2012_t2_firms.csv", "000023603914", 1, "平成24年経済センサス‐活動調査 企業等に関する集計 産業横断的集計 第2表 企業産業(中分類)、企業常用雇用者規模(11区分)、経営組織(5区分)別企業等数ほか－全国（CSV、cp932）"),
    ("census2014_t1_firms.xls", "000031332527", 0, "平成26年経済センサス‐基礎調査 企業等に関する集計 全国結果 第1表 企業産業(中分類)、企業常用雇用者規模(海外を含む)(11区分)、経営組織(5区分)別企業等数ほか－全国"),
    ("census2016_t1_firms.csv", "000031721990", 1, "平成28年経済センサス‐活動調査 企業等に関する集計 産業横断的集計 第1表 企業産業(中分類)、企業常用雇用者規模(11区分)、経営組織(5区分)別企業等数ほか－全国（CSV、cp932）"),
    ("census2021_t1_firms.xlsx", "000040067954", 0, "令和3年経済センサス‐活動調査 企業等に関する集計 産業横断的集計 第1表 企業産業(中分類)、経営組織(5区分)、企業常用雇用者規模(11区分)別企業等数ほか－全国"),
    ("census2024_t1_firms.xlsx", "000040389342", 0, "令和6年経済センサス‐基礎調査 甲調査 企業等に関する集計 第1表 同（雇用者のいない個人経営の企業を除く）－全国"),
]
rows = []
for name, sid, kind, desc in FILES:
    url = URL.format(sid, kind)
    b = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=180).read()
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
(RAW / "SOURCES.md").write_text(
    "# 元データ（取得日 " + datetime.date.today().isoformat() + "）\n\n"
    "総務省・経済産業省「経済センサス」（政府統計の総合窓口 e-Stat の掲載ファイル）。\n\n"
    "| ファイル | 中身 | URL | sha256（先頭12桁） |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- 活動調査の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200552\n"
    "- 基礎調査の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200553\n", encoding="utf-8")
