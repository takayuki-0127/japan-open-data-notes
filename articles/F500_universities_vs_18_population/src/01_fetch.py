"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校基本調査」年次統計（e-Stat の Excel）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("nenji_01_schools", "000031852301", "年次統計 総括表1 学校数（昭和23年～）"),
    ("nenji_09_entrants", "000031852309", "年次統計 総括表9 高等教育機関への入学状況（過年度高卒者等を含む）の推移"),
    ("nenji_13_graduates", "000031852313", "年次統計 総括表13 卒業者数（昭和23年～）"),
    ("nenji_k10_university", "000031852323", "年次統計 学校種ごと10 大学の学校数、在籍者数、教職員数（昭和23年～）"),
    ("nenji_k12_juniorcollege", "000031852325", "年次統計 学校種ごと12 短期大学の学校数、在籍者数、教職員数（昭和25年～）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        ext = ".xlsx" if b[:2] == b"PK" else ".xls"
        (RAW / (name + ext)).write_bytes(b)
        lines.append(f"| {name}{ext} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：文部科学省「学校基本調査」年次統計（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400001&tstat=000001011528&tclass1=000001021812）。",
              "各年5月1日時点。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
