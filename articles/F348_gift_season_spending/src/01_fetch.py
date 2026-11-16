"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「家計調査（家計収支編）」長期時系列表。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "kakei_two_plus_usage_monthly_2000_2026.xlsx": ("000040270657", 4, "表2 用途分類：収入及び支出金額・名目増減率・実質増減率（月・四半期・年・年度）二人以上の世帯（2000年1月〜）"),
    "kakei_nonfarm_usage_1963_2007.xls": ("000040270669", 4, "表20-1-b 二人以上の世帯（農林漁家世帯を除く）用途分類（年、1963〜2007年）"),
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
    lines += ["", "出典：総務省統計局「家計調査（家計収支編）」長期時系列表（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
