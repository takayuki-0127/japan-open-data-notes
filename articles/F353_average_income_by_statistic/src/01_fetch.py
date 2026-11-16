"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "nta_minkan_2025_table03_income_brackets.xlsx": ("https://www.nta.go.jp/publication/statistics/kokuzeicho/minkan2025/excel/2025_03.xlsx",
                                                     "国税庁「民間給与実態統計調査」令和7年分 第3表 給与階級別の総括表（その1・2、累年比較、乙欄適用者を除く）"),
    "mhlw_maikin_2025_annual_table01_wages.xlsx": ("https://www.mhlw.go.jp/toukei/itiran/roudou/monthly/r07/25cr/xls/25cc01r.xlsx",
                                                   "厚生労働省「毎月勤労統計調査」令和7年分結果確報 第1表 月間現金給与額（年平均）"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
    lines += ["", "出典：国税庁「民間給与実態統計調査」、厚生労働省「毎月勤労統計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
