"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 総務省「家計調査」家計収支編 二人以上の世帯 詳細結果表（年）
  第4-6表 世帯主の年齢階級別／第4-3表 年間収入五分位階級別（品目分類、1世帯当たり年間の支出金額）2015〜2025年
- 総務省「消費者物価指数」2025年基準 全国 品目別価格指数（暦年の年平均）"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "f3-research-script/1.0 (python urllib)"}
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
T46 = {2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558", 2020: "000032048838",
       2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}
T43 = {2015: "000031370142", 2016: "000031534705", 2017: "000031674347", 2018: "000031795470", 2019: "000031909557", 2020: "000032048837",
       2021: "000032167633", 2022: "000040015263", 2023: "000040140560", 2024: "000040247211", 2025: "000040409548"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for tab, ids, lab in [("4-6", T46, "第4-6表 世帯主の年齢階級別（品目分類）"), ("4-3", T43, "第4-3表 年間収入五分位階級別（品目分類）")]:
        for y, sid in ids.items():
            url = EST.format(sid, 0); b = get(url); ext = "xlsx" if b[:2] == b"PK" else "xls"
            name = f"kakei_{tab}_{y}.{ext}"; (RAW / name).write_bytes(b)
            rows.append((name, f"総務省「家計調査」{y}年 二人以上の世帯 {lab}", url, hashlib.sha256(b).hexdigest()[:12])); print("saved", name)
    url = EST.format("000040482831", 1); b = get(url); (RAW / "cpi_item_annual.csv").write_bytes(b)
    rows.append(("cpi_item_annual.csv", "総務省「消費者物価指数」2025年基準 全国 品目別価格指数（暦年の年平均、CSV、Shift_JIS）", url, hashlib.sha256(b).hexdigest()[:12]))
    L = ["# 元データの出典（取得日と URL）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
         "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    L += ["", "- 家計調査 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001",
          "- 消費者物価指数：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876",
          "- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
