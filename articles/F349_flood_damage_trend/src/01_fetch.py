"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
国土交通省「水害統計調査」令和5年 参考表。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "suigai_hyo44_damage_1875_2023.xlsx": ("000040302510", 0, "表-44 明治以降の水害被害額等の推移（名目額・平成27年価格、1875〜2023年）"),
    "suigai_hyo45_damage_vs_income_1879_2023.xlsx": ("000040302511", 0, "表-45 国民所得に対する水害被害額の割合（1879〜2023年）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, kind, desc) in FILES.items():
        url = BASE.format(sid, kind)
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
    lines += ["", "出典：国土交通省「水害統計調査」（令和5年、参考表）（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
