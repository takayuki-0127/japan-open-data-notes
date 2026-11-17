"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ」の2026年4月版（1990〜2024年度）と、照合用の2025年版（1990〜2023年度）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
B = "https://www.nies.go.jp/gio/archive/ghgdata/"
FILES = {
    "L5-7gas_2026_gioweb_ver1.0.xlsx": (B + "k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx", "2026年版（1990〜2024年度）"),
    "L5-7gas_2025_gioweb_1.0.xlsx": (B + "jqjm1000000ie8om-att/L5-7gas_2025_gioweb_1.0.xlsx", "2025年版（1990〜2023年度）照合用"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：国立環境研究所 温室効果ガスインベントリオフィス（GIO）「日本の温室効果ガス排出量データ」（https://www.nies.go.jp/gio/archive/ghgdata/index.html）。",
              "使うシート：1.Summary（ガス別の排出量）、8.F-gas（代替フロン等4ガスの用途別）。単位は百万トンCO2換算（Summary）、千トンCO2換算（F-gas）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
