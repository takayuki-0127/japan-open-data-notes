"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」市区町村別人口、人口動態及び世帯数（e-Stat、Excel）。
各年1月1日の人口と、前年1年間の人口動態。2015〜2026年調査（人口動態は2014〜2025年）の総計と、2015年・2026年の日本人住民。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
TOTAL = {2015: "000030438568", 2016: "000031430150", 2017: "000031598538", 2018: "000031736913", 2019: "000031843908",
         2020: "000031971203", 2021: "000040306659", 2022: "000032224636", 2023: "000040306647", 2024: "000040306672",
         2025: "000040306653", 2026: "000040479049"}
JAPANESE = {2015: "000030438569", 2026: "000040479053"}


def get(sid):
    req = urllib.request.Request(BASE.format(sid), headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for kind, d, label in [("total", TOTAL, "総計"), ("japanese", JAPANESE, "日本人住民")]:
        for y, sid in d.items():
            b = get(sid)
            ext = "xlsx" if b[:2] == b"PK" else "xls"
            name = f"jumin_{y}_{kind}.{ext}"
            (RAW / name).write_bytes(b)
            rows.append(f"| {name} | {y}年1月1日の人口、{y-1}年の人口動態（市区町村別、{label}） | {BASE.format(sid)} | {hashlib.sha256(b).hexdigest()[:12]} |")
            print(name, len(b))
    rows += ["", "出典：総務省「住民基本台帳に基づく人口、人口動態及び世帯数調査」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
