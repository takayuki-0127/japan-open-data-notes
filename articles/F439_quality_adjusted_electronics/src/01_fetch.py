"""01 取得（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない。data/raw に同梱済み）。
総務省「消費者物価指数」の長期時系列（e-Stat、CSV、Shift_JIS）と、財務省「貿易統計」輸出入額の推移（主要商品別、年別、輸入）。
暦年の値は暦年の表を使う（2025年基準 品目別 000040482831。年度平均の表 000040482959 は使わない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
FILES = [
    ("cpi2025_item_annual.csv", ES.format("000040482831"), "消費者物価指数 2025年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年）"),
    ("cpi2025_item_monthly.csv", ES.format("000040482945"), "消費者物価指数 2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月）"),
    ("cpi2020_item_annual.csv", ES.format("000032103938"), "消費者物価指数 2020年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年）"),
    ("cpi2015_item_annual.csv", ES.format("000031431772"), "消費者物価指数 2015年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2021年）"),
    ("trade_import_world_annual.csv", "https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv", "財務省 貿易統計 輸出入額の推移 輸入 世界 年別 主要商品別（金額・数量）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, url, desc in FILES:
        b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    txt = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py と同じ URL から取得）", "",
           "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"] + rows + [
           "", "- 消費者物価指数の CSV は Shift_JIS（cp932）。1〜6行目が見出し（類・品目名、英語名、符号、連番、ウエイト、ウエイト1万分比）、7行目からが年（または年月）。",
           "- 暦年の値は「年平均」の表（2025年基準は 000040482831）を使った。年度平均の表（000040482959）は使っていない。",
           "- 貿易統計の CSV も Shift_JIS。金額は千円、数量の単位は列ごとに書かれている（電算機類・電話機は台＝NO）。",
           "- e-Stat のデータ・貿易統計は、政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(txt) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
