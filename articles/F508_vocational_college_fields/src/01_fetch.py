"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校基本調査」（e-Stat の Excel）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
GAKKA = {1985: "000029084479", 1990: "000029026456", 1995: "000023596438", 2000: "000015170443", 2005: "000002946898",
         2010: "000008349864", 2015: "000031358003", 2020: "000032040615", 2025: "000040393885"}
FILES = [(f"senshu_{y}_gakka_seito." + ("xlsx" if y >= 2015 else "xls"), BASE.format(i), f"{y}年度 専修学校 設置者別学科別生徒数")
         for y, i in GAKKA.items()]
FILES += [("nenji_senshu_zaiseki.xlsx", BASE.format("000031852321"), "年次統計 専修学校の学校数，在籍者数，教職員数（昭和51年～）"),
          ("nenji_koto_nyugaku.xlsx", BASE.format("000031852309"), "年次統計 高等教育機関への入学状況（過年度高卒者等を含む）の推移")]


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
    lines += ["", "出典：文部科学省「学校基本調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400001&tstat=000001011528）。各年度5月1日時点。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
