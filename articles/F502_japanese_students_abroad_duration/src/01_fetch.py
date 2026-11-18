"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
日本学生支援機構「日本人学生留学状況調査」各年度の結果（PDF）、文部科学省の公表資料（PDF）、
文部科学省「学校基本調査」年次統計（e-Stat の Excel）。取ったあと 01b_extract.py で PDF の表を CSV にする。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
J = "https://www.studyinjapan.go.jp/ja/_mt/"
PATH = {2019: "2021/03/date2019n.pdf", 2020: "2022/11/date2020n.pdf", 2021: "2023/02/date2021n.pdf",
        2022: "2024/04/data2022n.pdf", 2023: "2025/04/data2023n.pdf", 2024: "2026/05/data2024n.pdf"}
FILES = [(f"jasso_nippon_{y}.pdf", J + PATH.get(y, f"2020/08/date{y}n.pdf"), f"{y}年度 日本人学生留学状況調査結果（JASSO）")
         for y in range(2009, 2025)]
FILES += [
    ("mext_2024-05-24_release.pdf", "https://www.mext.go.jp/content/20260529-mxt_kotokoku02-000027891_3.pdf",
     "文部科学省「外国人留学生在籍状況調査」及び「日本人の海外留学者数」等について（2024年5月24日）"),
    ("mext_2025-04-30_release.pdf", "https://www.mext.go.jp/content/20250430-mxt_kotokoku02-000027891_2.pdf",
     "文部科学省「日本人学生の海外留学状況」及び「外国人留学生の在籍状況」を公表します（2025年4月30日）"),
    ("mext_2026-05-29_release.pdf", "https://www.mext.go.jp/content/20250430-mxt_kotokoku02-000027891_1.pdf",
     "文部科学省「日本人学生の海外留学状況」及び「外国人留学生の在籍状況」を公表します（2026年5月29日）"),
    ("nenji_02_enrollment.xlsx", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031852302&fileKind=0",
     "学校基本調査 年次統計 総括表2 在学者数（昭和23年～）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：独立行政法人日本学生支援機構「日本人学生留学状況調査」（https://www.studyinjapan.go.jp/ja/statistics/japanese-students/）、",
              "文部科学省「日本人の海外留学者数」（https://www.mext.go.jp/a_menu/koutou/ryugaku/1412692_00003.htm）、",
              "文部科学省「学校基本調査」年次統計（e-Stat）。",
              "注：文部科学省の PDF は、URL の日付と中身の公表日が違うものがある（ページのリンクのとおりに取った）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
