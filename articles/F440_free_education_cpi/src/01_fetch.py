"""01 取得（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない。data/raw に同梱済み）。
総務省「消費者物価指数」の長期時系列 品目別価格指数（e-Stat、CSV、Shift_JIS）を、2015年・2020年・2025年の3つの基準で取る。
無償化の時期の指数とウエイトは、その時期に公表に使われた基準の表で見る（2019〜2020年は2015年基準、2024〜2025年は2020年基準、2026年は2025年基準）。
暦年の値は暦年の表を使う（2025年基準 品目別 000040482831・中分類 000040482829。年度平均の表 000040482959・000040482957 は使わない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
FILES = [
    ("cpi2015_item_monthly.csv", "000031431698", "消費者物価指数 2015年基準 全国 品目別価格指数（月次、1970年1月〜2021年12月）"),
    ("cpi2015_item_annual.csv", "000031431772", "消費者物価指数 2015年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2021年）"),
    ("cpi2020_item_monthly.csv", "000032103844", "消費者物価指数 2020年基準 全国 品目別価格指数（月次、1970年1月〜）"),
    ("cpi2020_item_annual.csv", "000032103938", "消費者物価指数 2020年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年）"),
    ("cpi2025_item_monthly.csv", "000040482945", "消費者物価指数 2025年基準 全国 品目別価格指数（月次、1970年1月〜2026年9月）"),
    ("cpi2025_item_annual.csv", "000040482831", "消費者物価指数 2025年基準 全国 品目別価格指数（年平均＝暦年、1970年〜2025年）"),
    ("cpi2025_middle_annual.csv", "000040482829", "消費者物価指数 2025年基準 全国 中分類指数（年平均＝暦年、1970年〜2025年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, sid, desc in FILES:
        url = ES.format(sid)
        b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    txt = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py と同じ URL から取得）", "",
           "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"] + rows + [
           "", "- CSV は Shift_JIS（cp932）。1〜6行目が見出し（類・品目名、英語名、符号、連番、ウエイト、ウエイト1万分比）、7行目からが年（または年月）。",
           "- 暦年の値は「年平均」の表を使った（2025年基準：品目別 000040482831・中分類 000040482829、2020年基準：000032103938、2015年基準：000031431772）。年度平均の表（000040482959・000040482957 など）は使っていない。",
           "- e-Stat のデータは、政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。",
           "- 2015年基準の月次は全国の表（000031431698）を使った。はじめ 000031431788 を取ったが、総合のウエイト（256,632,267）が全国の年平均の表（3,139,338,474）と合わず、年平均も全国の値と一致しなかったため、全国の表ではない（推測：東京都区部の表）と判断して取り替えた。"]
    (RAW / "SOURCES.md").write_text("\n".join(txt) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
