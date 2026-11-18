"""e-Stat から農林水産省「漁業・養殖業生産統計」「漁業産出額」の長期累年の表を取得して data/raw/ に保存する。ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
FILES = [
    ("vol_sector.xlsx", "000040416368", "漁業・養殖業生産統計 長期累年 表1 漁業・養殖業部門別累年統計 生産量（全国、1979〜2024年）"),
    ("vol_marine_gear.xlsx", "000040416369", "漁業・養殖業生産統計 長期累年 表2 海面漁業種類別漁獲量累年統計（全国、1956〜2024年）"),
    ("vol_marine_species.xlsx", "000040416370", "漁業・養殖業生産統計 長期累年 表3 海面漁業魚種別漁獲量累年統計（全国、1956〜2024年）"),
    ("vol_aqua_species.xlsx", "000040416372", "漁業・養殖業生産統計 長期累年 表6 養殖魚種別収獲量累年統計（全国、1956〜2024年）"),
    ("vol_inland.xlsx", "000040416373", "漁業・養殖業生産統計 長期累年 表7 内水面漁業・養殖業魚種別生産量累年統計（全国、1956〜2024年）"),
    ("val_summary.xls", "000040426424", "漁業産出額 長期累年 表1 産出額（総括表）累年統計（全国、1960〜2024年）"),
    ("val_aqua_species.xls", "000040426426", "漁業産出額 長期累年 表3 魚種別産出額累年統計 海面養殖業（全国、1960〜2024年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, sid, desc in FILES:
        with urllib.request.urlopen(urllib.request.Request(URL.format(sid), headers=UA), timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append((name, desc, URL.format(sid), hashlib.sha256(b).hexdigest()[:12]))
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", "- 漁業・養殖業生産統計 長期累年の一覧：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00500216&tstat=000001015174&cycle=0&tclass1=000001034726",
              "- 漁業産出額 長期累年の一覧：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00500208&tstat=000001015664&cycle=0&tclass1=000001034725",
              "- 出典：農林水産省「漁業・養殖業生産統計」「漁業産出額」（e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
