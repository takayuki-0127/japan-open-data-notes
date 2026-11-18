"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
日本学生支援機構（JASSO）「外国人留学生在籍状況調査」の結果（PDF）。2014〜2025年度。
あわせて、照合用に文部科学省「学校基本調査」2025年度の国籍別 外国人学生数（大学・大学院、Excel）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
J = "https://www.studyinjapan.go.jp/ja/_mt/"
FILES = [(f"jasso_{y}.pdf", J + p, f"{y}年度 外国人留学生在籍状況調査結果") for y, p in [
    (2014, "2020/08/date2014z.pdf"), (2015, "2020/08/date2015z.pdf"), (2016, "2020/08/date2016z.pdf"),
    (2017, "2020/08/date2017z.pdf"), (2018, "2020/08/date2018z.pdf"), (2019, "2020/08/date2019z.pdf"),
    (2020, "2021/04/date2020z.pdf"), (2021, "2022/03/date2021z.pdf"), (2022, "2023/03/date2022z.pdf"),
    (2023, "2024/04/data2023z.pdf"), (2024, "2025/04/data2024z.pdf"), (2025, "2026/05/data2025z.pdf")]]
FILES += [
    ("jasso_2025_suii_stage.pdf", J + "2026/05/2025_zaiseki_suii_22.pdf", "2025年度 在学段階別 留学生数の推移（1983〜2025年）"),
    ("gakko_2025_t22_univ_nationality.xlsx", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040392961&fileKind=0",
     "学校基本調査 2025年度 表22 国籍・地域別 関係学科別 外国人学生数（大学）"),
    ("gakko_2025_t24_grad_nationality.xlsx", "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040392963&fileKind=0",
     "学校基本調査 2025年度 表24 国籍・地域別 専攻分野別 外国人学生数（大学院）"),
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
    lines += ["", "出典：独立行政法人日本学生支援機構「外国人留学生在籍状況調査」（https://www.studyinjapan.go.jp/ja/statistics/zaiseki/）。各年5月1日時点。",
              "照合用：文部科学省「学校基本調査」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
