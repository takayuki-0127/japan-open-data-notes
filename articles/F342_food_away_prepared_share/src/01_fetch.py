"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「家計調査（家計収支編）」長期時系列表。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "kakei_two_plus_items_nominal_2000_2025.csv": ("000040270652", 1, "表1-2 二人以上の世帯 品目分類（小分類まで）支出金額（年、2000年〜、円）"),
    "kakei_two_plus_items_real_growth_2000_2025.csv": ("000040270654", 1, "表1-2 二人以上の世帯 品目分類（小分類まで）実質増減率（年、2000年〜、%）"),
    "kakei_total_households_items_2000_2025.csv": ("000040270663", 1, "表5 総世帯 品目分類（小分類まで）支出金額（年、2000年〜）"),
    "kakei_single_items_2000_2025.csv": ("000040270666", 1, "表6 単身世帯 品目分類（小分類まで）支出金額（年、2000年〜）"),
    "kakei_nonfarm_items_1963_2007.xls": ("000040270670", 4, "表20-3-a 二人以上の世帯（農林漁家世帯を除く）品目分類 1世帯当たり年間の品目別支出金額（1963〜2007年）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, kind, desc) in FILES.items():
        url = BASE.format(sid, kind)
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
        print(name, p.stat().st_size)
    lines += ["", "出典：総務省統計局「家計調査（家計収支編）」長期時系列表（e-Stat）。CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
