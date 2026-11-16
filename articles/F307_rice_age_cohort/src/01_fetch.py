"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
総務省「家計調査」家計収支編 二人以上の世帯 詳細結果表 年次 第4-6表「世帯主の年齢階級別」（品目分類、1世帯当たり年間の支出金額・購入数量）
（F306 と同じファイル。2026-11-16 に同じ URL から取得したものを同梱）"""
import datetime, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
IDS = {2002: "000000331A71", 2003: "000000331AAA", 2004: "000000331AE3", 2005: "000000331B1C", 2006: "000000331D6E", 2007: "000001158916", 2008: "000002209407", 2009: "000007370343", 2010: "000008635842", 2011: "000012687884", 2012: "000019023734", 2013: "000023621389", 2014: "000028352478", 2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558", 2020: "000032048838", 2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for y, sid in IDS.items():
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"kakei_4-6_{y}.{ext}").write_bytes(b)
        lines.append(f"| kakei_4-6_{y}.{ext} | 総務省「家計調査」{y}年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | {url} | {today} |")
        print("saved", y)
    lines += ["", "- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001",
              "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
