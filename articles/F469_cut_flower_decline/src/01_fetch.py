"""e-Stat から元データを取得して data/raw/ に保存する。ネットが必要。run_all.sh からは呼ばない。
- 農林水産省「作物統計（花き生産出荷統計）」長期累年：品目別作付面積及び出荷量累年統計（全国、1976〜2024年）の
  切り花類・球根類・鉢もの類・花壇用苗もの類、と、令和7年産（2025年）の全国の作付（収穫）面積及び出荷量
- 総務省「家計調査」二人以上の世帯 詳細結果表（年）第4-6表 世帯主の年齢階級別（2002〜2025年）と、
  長期時系列 表20-3-a（農林漁家世帯を除く、1963〜2007年）
- 総務省「消費者物価指数」2025年基準 品目別価格指数（全国、暦年）
- 財務省「貿易統計」統計品別表（輸入、各年1〜12月の確定値、2009〜2025年）。全品目の CSV なので
  gzip で縮めて置く（展開すると取得したバイト列と同じ。sha256 は展開後の値）
"""
import datetime, gzip, hashlib, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
FILES = {
    "kaki/kirihana_zenkoku.xls": ("000040385693", 0, "花き生産出荷統計 累年 切り花類 全国（1976〜2024年）"),
    "kaki/kyukon_zenkoku.xls": ("000040385750", 0, "花き生産出荷統計 累年 球根類 全国"),
    "kaki/hachimono_zenkoku.xls": ("000040385807", 0, "花き生産出荷統計 累年 鉢もの類 全国"),
    "kaki/naemono_zenkoku.xls": ("000040385864", 0, "花き生産出荷統計 累年 花壇用苗もの類 全国"),
    "kaki/r7_zenkoku.xlsx": ("000040515508", 0, "花き生産出荷統計 令和7年産 全国の作付（収穫）面積及び出荷量"),
    "kakei/kakei_nonfarm_items_1963_2007.xls": ("000040270670", 4, "家計調査 長期時系列 表20-3-a 二人以上の世帯（農林漁家世帯を除く）品目別 年間支出金額（1963〜2007年）"),
    "kakei/cpi_item_annual.csv": ("000040482831", 1, "消費者物価指数 2025年基準 全国 品目別価格指数（暦年の年平均）"),
}
T46 = {2002: "000000331A71", 2003: "000000331AAA", 2004: "000000331AE3", 2005: "000000331B1C", 2006: "000000331D6E", 2007: "000001158916",
       2008: "000002209407", 2009: "000007370343", 2010: "000008635842", 2011: "000012687884", 2012: "000019023734", 2013: "000023621389",
       2014: "000028352478", 2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558",
       2020: "000032048838", 2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}
IMPORT = {2009: "000007064293", 2010: "000008622910", 2011: "000012679370", 2012: "000018862159", 2013: "000023618925",
          2014: "000028156986", 2015: "000031362184", 2016: "000031528657", 2017: "000031670699", 2018: "000031792535",
          2019: "000031907313", 2020: "000032046081", 2021: "000032254759", 2022: "000040117466", 2023: "000040223254",
          2024: "000040368878", 2025: "000040524663"}


def get(sid, kind):
    with urllib.request.urlopen(urllib.request.Request(URL.format(sid, kind), headers=UA), timeout=180) as r:
        return r.read()


def main():
    for d in ["kaki", "kakei", "trade"]:
        (RAW / d).mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    rows = []
    for name, (sid, kind, desc) in FILES.items():
        b = get(sid, kind); (RAW / name).write_bytes(b)
        rows.append((name, desc, URL.format(sid, kind), hashlib.sha256(b).hexdigest()[:12])); time.sleep(0.5)
    for y, sid in T46.items():
        b = get(sid, 0)
        name = f"kakei/kakei_4-6_{y}.{'xlsx' if b[:2] == b'PK' else 'xls'}"
        (RAW / name).write_bytes(b)
        rows.append((name, f"家計調査 {y}年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類）", URL.format(sid, 0), hashlib.sha256(b).hexdigest()[:12]))
        print("kakei", y, flush=True); time.sleep(0.5)
    for y, sid in IMPORT.items():
        b = get(sid, 1)
        name = f"trade/import_{y}.csv.gz"
        (RAW / name).write_bytes(gzip.compress(b, compresslevel=9, mtime=0))
        rows.append((name, f"貿易統計 統計品別表 輸入 {y}年1〜12月（確定）", URL.format(sid, 1), hashlib.sha256(b).hexdigest()[:12]))
        print("import", y, flush=True); time.sleep(0.5)
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字（gz は展開後） |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["",
              "- 花き生産出荷統計の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00500215&tstat=000001013427&tclass1=000001032289",
              "- 家計調査の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001",
              "- 貿易統計（統計品別表 輸入）：https://www.e-stat.go.jp/stat-search/files?toukei=00350300&tstat=000001013141&tclass1=000001013183&tclass2=000001013185",
              "- 貿易統計の CSV は全品目の表。gzip で縮めただけで、中身は取得したままのバイト列（`gzip -dc` で戻る）。",
              "- 出典：農林水産省「作物統計（花き生産出荷統計）」、総務省「家計調査」「消費者物価指数」、財務省「貿易統計」（いずれも e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
