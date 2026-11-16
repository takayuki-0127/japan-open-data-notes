"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「住民基本台帳人口移動報告」年報（e-Stat、Excel）。
- 21大都市の、移動前の住所地（都道府県）別転入者数・移動後の住所地別転出者数（2014〜2025年）
  2014〜2019年は第7表（21大都市の分）、2020〜2025年は第6表
- 2025年 第8-3表：年齢（5歳階級）、住所地別転入超過数（都道府県、3大都市圏、21大都市）
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
CITY_TABLES = {2014: "000029036187", 2015: "000031403044", 2016: "000031562775", 2017: "000031688414", 2018: "000031819985",
               2019: "000031931400", 2020: "000032047088", 2021: "000032163821", 2022: "000040008247", 2023: "000040139267",
               2024: "000040243453", 2025: "000040407045"}
AGE_2025 = "000040407050"


def get(sid):
    req = urllib.request.Request(BASE.format(sid), headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    items = [(f"migration_city_{y}", sid, f"{y}年 21大都市の移動前（後）の住所地別転入者数・転出者数（{'第7表' if y < 2020 else '第6表'}）") for y, sid in CITY_TABLES.items()]
    items.append(("migration_age_net_2025", AGE_2025, "2025年 第8-3表 年齢（5歳階級）、男女、住所地別転入超過数"))
    for stem, sid, desc in items:
        b = get(sid)
        name = stem + (".xlsx" if b[:2] == b"PK" else ".xls")
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | 総務省「住民基本台帳人口移動報告」年報 {desc} | {BASE.format(sid)} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：総務省「住民基本台帳人口移動報告」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
