"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "lfs_longterm_table2_annual_1953_2025.xlsx": ("000001082681", "総務省「労働力調査」長期時系列表 表2-1 主要項目（年平均、1953年〜）"),
    "shokugyo_shokai_longterm_table1_1963_2025.xlsx": ("000040518981", "厚生労働省「一般職業紹介状況」長期時系列表 第1表 労働市場関係指標"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, desc) in FILES.items():
        url = BASE.format(sid); p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
    lines += ["", "出典：総務省「労働力調査」、厚生労働省「一般職業紹介状況」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
