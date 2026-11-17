"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「家計調査」：月別の品目別支出（二人以上の世帯、2015〜2026年）、長期時系列（1963〜2007年、年）、
年報 第4-6表（世帯主の年齢階級別、2015〜2025年）。総務省「消費者物価指数」2025年基準 品目別（暦年の年平均）。いずれも e-Stat。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "kakei_monthly_items_2015_2019.csv": (E.format("000040270649", 1), "家計調査 二人以上の世帯 品目分類 月別支出金額（2015〜2019年）"),
    "kakei_monthly_items_2020_2024.csv": (E.format("000040270650", 1), "家計調査 二人以上の世帯 品目分類 月別支出金額（2020〜2024年）"),
    "kakei_monthly_items_2025_2026.csv": (E.format("000040270651", 1), "家計調査 二人以上の世帯 品目分類 月別支出金額（2025年〜）"),
    "kakei_nonfarm_items_1963_2007.xls": (E.format("000040270670", 4), "家計調査 長期時系列 表20-3-a 二人以上の世帯（農林漁家世帯を除く）品目別 年間支出金額（1963〜2007年）"),
    "cpi_item_annual.csv": (E.format("000040482831", 1), "消費者物価指数 2025年基準 全国 品目別価格指数（暦年の年平均）"),
}
AGE = {2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558",
       2020: "000032048838", 2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}
for y, i in AGE.items():
    FILES[f"kakei_4-6_{y}.{'xls' if y <= 2019 else 'xlsx'}"] = (E.format(i, 0), f"家計調査 {y}年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類）")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：総務省統計局「家計調査（家計収支編）」「消費者物価指数」（e-Stat https://www.e-stat.go.jp/）。CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
