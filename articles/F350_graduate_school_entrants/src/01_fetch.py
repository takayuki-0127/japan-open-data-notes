"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校基本調査」。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
ADM = {2025: '000040392737', 2024: '000040230326', 2023: '000040128623', 2022: '000032265035', 2021: '000032155540', 2020: '000032040276', 2019: '000031894025', 2018: '000031776665', 2017: '000031656043', 2016: '000031504870', 2015: '000031358101', 2014: '000027597245', 2013: '000023610155', 2012: '000018428750', 2011: '000012683853', 2010: '000008349977'}
FILES = {f"gakkou_kihon_{y}_grad_admission_by_field." + ("xls" if y <= 2014 else "xlsx"): (sid, f"{y}年度 専攻分野別 大学院入学状況（修士・博士・専門職）") for y, sid in ADM.items()}
FILES["gakkou_kihon_nenji_13_graduates_1948_2025.xlsx"] = ("000031852313", "年次統計 表13 卒業者数（昭和23年〜）")
FILES["gakkou_kihon_nenji_k11_grad_enrollment_1950_2025.xlsx"] = ("000031852324", "年次統計 表11 大学院を設置する学校数、大学院の在籍者数（昭和25年〜）")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, desc) in sorted(FILES.items()):
        url = BASE.format(sid)
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
    lines += ["", "出典：文部科学省「学校基本調査」（e-Stat）。2014年度以前の入学状況の表は古い Excel 形式（.xls）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
