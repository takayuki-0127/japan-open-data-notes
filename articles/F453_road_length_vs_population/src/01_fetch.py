"""国土交通省「道路統計年報」（道路統計調査）と総務省「人口推計」を e-Stat から取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
FILES = [
    ("road_t1_1_2025", "000040441669", 0, "道路統計年報2025年度 表1-1 道路現況の推移（その1）（昭和27年度〜令和5年度末）"),
    ("road_t4_2025", "000040441673", 0, "道路統計年報2025年度 表4 都道府県別道路現況（合計）（令和6年3月31日現在）"),
    ("road_t4_2016", "000031576255", 0, "道路統計年報2016年度 表04 都道府県別道路現況《合計》"),
    ("pop_pref_1920_2000", "000000090265", 0, "人口推計 長期時系列 第5表 都道府県別人口（各年10月1日現在）大正9年〜平成12年"),
    ("pop_pref_2000_2020", "000013168605", 4, "人口推計 長期時系列 表番号5 都道府県別人口（各年10月1日現在）2000年〜2020年"),
    ("pop_pref_2020_2024", "000040268859", 0, "人口推計 2024年 第5表 都道府県、男女別人口（各年10月1日現在）"),
]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, kind, desc in FILES:
        url = BASE.format(sid, kind)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"{name}.{ext}").write_bytes(b)
        lines.append(f"| {name}.{ext} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", name, len(b))
    lines += ["", "- 統計表の一覧：道路統計調査 https://www.e-stat.go.jp/stat-search/files?toukei=00600610&tstat=000001017725 ／ 人口推計 https://www.e-stat.go.jp/stat-search/files?toukei=00200524&tstat=000000090001",
              "- 出典：国土交通省「道路統計年報」、総務省「人口推計」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
