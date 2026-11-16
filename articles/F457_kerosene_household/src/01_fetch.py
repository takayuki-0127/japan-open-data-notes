"""総務省「家計調査」（二人以上の世帯）の灯油の購入数量・支出金額を含む表を e-Stat から取得して data/raw/ に保存する。
- 長期時系列 表番号20-3-a（1963〜2007年、農林漁家世帯を除く）
- 各年の詳細結果表 表番号4-1（2007〜2025年。2007年は長期時系列表との重なりの確かめ用。2018年からは都道府県庁所在市別を含む）
.xls は取得したバイト列をそのまま gzip（mtime=0）で圧縮して保存する。ネットが必要。run_all.sh からは呼ばない。"""
import datetime, gzip, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
T41 = {2007: "000001158907", 2008: "000002209396", 2009: "000007370332", 2010: "000008635831", 2011: "000012687873", 2012: "000019023723",
       2013: "000023621378", 2014: "000028352467", 2015: "000031370133", 2016: "000031534696", 2017: "000031674338",
       2018: "000031795468", 2019: "000031909555", 2020: "000032048835", 2021: "000032167631", 2022: "000040015261",
       2023: "000040140558", 2024: "000040247209", 2025: "000040409546"}

def save(name, b):
    if b[:2] == b"PK":
        (RAW / f"{name}.xlsx").write_bytes(b); return f"{name}.xlsx"
    with gzip.GzipFile(RAW / f"{name}.xls.gz", "wb", mtime=0) as f:
        f.write(b)
    return f"{name}.xls.gz"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    items = [("long_20_3_a", BASE.format("000040270670", 4), "長期時系列 表番号20-3-a 品目分類（年）1世帯当たり年間の品目別支出金額及び購入数量（1963〜2007年、二人以上の世帯（農林漁家世帯を除く））")]
    items += [(f"t4_1_{y}", BASE.format(s, 0), f"{y}年 詳細結果表 表番号4-1 品目分類 1世帯当たり年間の支出金額、購入数量及び平均価格（二人以上の世帯）") for y, s in T41.items()]
    for name, url, desc in items:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
            b = r.read()
        fn = save(name, b)
        lines.append(f"| {fn} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", fn, len(b))
    lines += ["", "- 統計表の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001",
              "- 出典：総務省「家計調査」（政府統計の総合窓口 e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
