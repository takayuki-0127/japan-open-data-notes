"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
農林水産省「農林業センサス」の年齢別基幹的農業従事者数を data/raw/ に保存する。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "census_longterm_core_workers_by_age_1960_2020.xls": ("000040038990", "農林業センサス累年統計 表5-11 年齢別基幹的農業従事者数（1960〜2020年。2015年までは販売農家、2015・2020年は個人経営体。全国・地域・都道府県、男女、5歳階級は2005年から）"),
    "census2025_core_workers_by_age.xlsx": ("000040483794", "2025年農林業センサス 表2-54(1)ア 年齢階層別の基幹的農業従事者数（個人経営体。2025年と2020年、全国・地域・都道府県、男女）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, desc) in FILES.items():
        url = BASE.format(sid)
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
        print(name, p.stat().st_size)
    lines += ["", "出典：農林水産省「農林業センサス」（e-Stat）。基幹的農業従事者は、自営農業を主な仕事としている世帯員（個人経営体・販売農家の世帯員）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
