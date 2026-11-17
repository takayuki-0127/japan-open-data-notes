"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 総務省「家計調査」家計収支編 二人以上の世帯
  長期時系列表 1-2（品目分類・年、2000〜2025年）支出金額・実質増減率、20-3-a（1963〜2007年）
  詳細結果表 第4-6表 世帯主の年齢階級別（品目分類、2002〜2025年）
- 総務省「消費者物価指数」2025年基準 全国 中分類指数（年平均＝暦年、1970〜2025年）"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "f3-research-script/1.0 (python urllib)"}
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
T46 = {2002: "000000331A71", 2003: "000000331AAA", 2004: "000000331AE3", 2005: "000000331B1C", 2006: "000000331D6E", 2007: "000001158916",
       2008: "000002209407", 2009: "000007370343", 2010: "000008635842", 2011: "000012687884", 2012: "000019023734", 2013: "000023621389",
       2014: "000028352478", 2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558",
       2020: "000032048838", 2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}
OTHER = [("kakei_longtime_1-2_items_2000_2025.csv", "000040270652", 1, "総務省「家計調査」長期時系列表 1-2 品目分類（小分類まで）支出金額（年、二人以上の世帯、2000〜2025年、CSV、Shift_JIS）"),
         ("kakei_longtime_1-2_real_growth_2000_2025.csv", "000040270654", 1, "同 1-2 実質増減率（年、2000〜2025年、CSV、Shift_JIS）"),
         ("kakei_longtime_20-3-a_1963_2007.xls", "000040270670", 4, "同 20-3-a 二人以上の非農林漁家世帯 品目別支出金額及び購入数量（年、1963〜2007年、Excel）"),
         ("cpi_annual_middle_class.csv", "000040482829", 1, "総務省「消費者物価指数」2025年基準 全国 中分類指数（年平均、1970〜2025年、CSV、Shift_JIS）")]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for y, sid in T46.items():
        url = EST.format(sid, 0); b = get(url); ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"kakei_4-6_{y}.{ext}"; (RAW / name).write_bytes(b)
        rows.append((name, f"総務省「家計調査」{y}年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類）", url, hashlib.sha256(b).hexdigest()[:12]))
    for name, sid, kind, lab in OTHER:
        url = EST.format(sid, kind); b = get(url); (RAW / name).write_bytes(b)
        rows.append((name, lab, url, hashlib.sha256(b).hexdigest()[:12]))
    L = ["# 元データの出典（取得日と URL）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
         "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    L += ["", "- 家計調査 長期時系列表：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001&tclass1=000001228280",
          "- 消費者物価指数 2025年基準 長期時系列：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876",
          "- 注：消費者物価指数の statInfId=000040482957（中分類）・000040482959（品目別）は「年度平均」の表で、暦年の年平均ではない（2025年の総合が100.4）。ここでは暦年の 000040482829 を使う。",
          "- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
