"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 内閣府「国民経済計算 2024年度年次推計」家計（個人企業を含む）の所得の使用勘定（家計貯蓄率）
- 総務省「家計調査（家計収支編）」長期時系列表2（二人以上の世帯、勤労者世帯、2000年〜）
- 同 年報 第3-2表 世帯主の年齢階級別（二人以上・勤労者・無職、2019年と2025年）
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "sna_2024_household_accounts.xlsx": ("https://www.esri.cao.go.jp/jp/sna/data/data_list/kakuhou/files/2024/tables/2024i5_jp.xlsx", "国民経済計算 2024年度年次推計 家計（個人企業を含む）制度部門別所得支出勘定（1994〜2024年）"),
    "kakei_longterm_two_plus.xlsx": (ES.format("000040270657", 4), "家計調査 長期時系列 表2 用途分類 二人以上の世帯（2000年〜）"),
    "kakei_longterm_workers.xlsx": (ES.format("000040270658", 4), "家計調査 長期時系列 表2 用途分類 二人以上の世帯のうち勤労者世帯（2000年〜）"),
    "kakei_by_age_2025.xlsx": (ES.format("000040409533", 0), "家計調査 2025年 第3-2表 世帯主の年齢階級別（二人以上・勤労者・無職）"),
    "kakei_by_age_2019.xls": (ES.format("000031909542", 0), "家計調査 2019年 第3-2表 世帯主の年齢階級別（二人以上・勤労者・無職）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256((RAW / name).read_bytes()).hexdigest()[:12]} |")
        print(name, (RAW / name).stat().st_size)
    lines += ["", "出典：内閣府経済社会総合研究所「国民経済計算」、総務省統計局「家計調査（家計収支編）」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
