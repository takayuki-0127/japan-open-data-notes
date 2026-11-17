"""01_fetch.py : e-Stat から家計消費状況調査 年報の表を取得して data/raw/ に保存し、SOURCES.md を書く。
ネットが必要。run_all.sh からは呼ばない（data/raw に同梱済み）。
"""
import datetime
import hashlib
import pathlib
import time
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
# 年: (第1-2表, 第6-1表, 第6-2表, 第4-2表) の statInfId（e-Stat のファイル一覧で確かめたもの）
IDS = {
    2015: ("000031372049", "000031372068", "000031372069", "000031372079"),
    2016: ("000031532308", "000031532327", "000031532328", "000031532339"),
    2017: ("000031670974", "000031670994", "000031670995", "000031671005"),
    2018: ("000031794520", "000031794540", "000031794541", "000031794551"),
    2019: ("000031909473", "000031909493", "000031909494", "000031909505"),
    2020: ("000032048666", "000032048686", "000032048687", "000032048698"),
    2021: ("000032167467", "000032167487", "000032167488", "000032167499"),
    2022: ("000040013651", "000040013671", "000040013672", "000040013683"),
    2023: ("000040140883", "000040140903", "000040140904", "000040140915"),
    2024: ("000040247255", "000040247275", "000040247276", "000040247287"),
    2025: ("000040408043", "000040408063", "000040408064", "000040408075"),
}
TABLES = [("t1_2", "第1-2表 世帯主の年齢階級別 インターネットを利用した1世帯当たり1か月間の支出"),
          ("t6_1", "第6-1表 全国・地方・都市階級別 支出世帯1世帯当たり1か月間の支出金額"),
          ("t6_2", "第6-2表 全国・地方・都市階級別 支出世帯の割合（10000世帯当たり）"),
          ("t4_2", "第4-2表 世帯主の年齢階級別 インターネットを利用した購入状況")]


def fetch(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=180) as r:
                return r.read()
        except Exception:
            time.sleep(5)
    raise RuntimeError(url)


def main():
    rows = []
    for y, ids in IDS.items():
        for (stem, desc), sid in zip(TABLES, ids):
            url = EST.format(sid)
            b = fetch(url)
            ext = ".xls" if b[:4] == b"\xd0\xcf\x11\xe0" else ".xlsx"
            name = f"kcs_{stem}_{y}{ext}"
            (RAW / name).write_bytes(b)
            rows.append((name, f"{y}年 {desc}", url, hashlib.sha256(b).hexdigest()[:12], len(b)))
            print(name, len(b))
            time.sleep(1)
    lines = ["# SOURCES（元データの取得元）", "",
             f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    lines += ["", "出典：総務省統計局「家計消費状況調査」年報（e-Stat、https://www.e-stat.go.jp/stat-search/files?toukei=00200565&tstat=000000660001）。",
              "政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
