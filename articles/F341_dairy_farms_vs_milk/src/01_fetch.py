"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "dairy_herd_national_1960_2025.xlsx": ("000040414813", "畜産統計 長期累年 表1 乳用牛飼養戸数・頭数累年統計 全国（1960〜2025年、各年2月1日現在）"),
    "dairy_herd_hokkaido_1960_2025.xlsx": ("000040414814", "同 北海道"),
    "dairy_herd_tofuken_1960_2025.xlsx": ("000040414815", "同 都府県"),
    "dairy_farms_by_size_national.xlsx": ("000040414879", "畜産統計 長期累年 表2 乳用牛成畜頭数規模別飼養戸数累年統計 全国（1962〜2025年）"),
    "dairy_adults_by_size_national.xlsx": ("000040414945", "畜産統計 長期累年 表3 乳用牛成畜頭数規模別成畜飼養頭数累年統計 全国（1962〜2025年）"),
    "raw_milk_production_1985_2024.xlsx": ("000040358547", "牛乳乳製品統計 長期累年 表1 生乳生産量累年統計 全国（1985〜2024年、月別）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, desc) in FILES.items():
        url = BASE.format(sid)
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
        print(name, p.stat().st_size)
    lines += ["", "出典：農林水産省「畜産統計調査」「牛乳乳製品統計調査」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
