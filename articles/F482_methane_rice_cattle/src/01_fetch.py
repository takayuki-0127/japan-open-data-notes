"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ」2026年版・2025年版（シート 6.CH4）
- 農林水産省「作物統計調査」収穫量累年統計 水稲（全国）、「畜産統計調査」乳用牛・肉用牛の飼養戸数・頭数累年統計（全国）（e-Stat）"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
G = "https://www.nies.go.jp/gio/archive/ghgdata/"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "L5-7gas_2026_gioweb_ver1.0.xlsx": (G + "k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx", "温室効果ガス排出量 2026年版（1990〜2024年度）"),
    "L5-7gas_2025_gioweb_1.0.xlsx": (G + "jqjm1000000ie8om-att/L5-7gas_2025_gioweb_1.0.xlsx", "同 2025年版（1990〜2023年度）照合用"),
    "rice_suito_zenkoku.xls": (E.format("000040433903"), "作物統計 収穫量累年統計 水稲 全国（作付面積）"),
    "dairy_cattle_zenkoku.xls": (E.format("000040414813"), "畜産統計 乳用牛飼養戸数・頭数累年統計 全国"),
    "beef_cattle_zenkoku.xls": (E.format("000040415075"), "畜産統計 肉用牛飼養戸数・頭数累年統計 全国"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "出典：国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ」（https://www.nies.go.jp/gio/archive/ghgdata/index.html）、",
              "農林水産省「作物統計調査」「畜産統計調査」（e-Stat https://www.e-stat.go.jp/）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
