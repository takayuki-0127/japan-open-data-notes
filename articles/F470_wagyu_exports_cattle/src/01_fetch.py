"""e-Stat から元データを取得して data/raw/ に保存する。ネットが必要。run_all.sh からは呼ばない。
- 農林水産省「畜産統計」長期累年：肉用牛飼養戸数・頭数累年統計（全国、1960〜2025年）
- 農林水産省「畜産物流通統計」長期累年：と畜頭数累年統計・枝肉生産量累年統計（全国、1985〜2024年）、
  食肉中央卸売市場の和牛計の取引頭数と価格（1996〜2024年）
- 財務省「貿易統計」統計品別表（輸出、各年1〜12月の確定値、2009〜2025年）。全品目の CSV なので、
  そのままの中身を gzip で縮めて置く（展開すると取得したバイト列と同じ。sha256 は展開後の値）
"""
import datetime, gzip, hashlib, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
XLS = {
    "chikusan_nikuyougyu_zenkoku.xls": ("000040415075", "畜産統計 長期累年 肉用牛飼養戸数・頭数累年統計 全国（1960〜2025年）"),
    "ryutsu_tochiku_tosu.xls": ("000040373516", "畜産物流通統計 長期累年 と畜頭数及びと畜場数累年統計 全国（1985〜2024年）"),
    "ryutsu_edaniku.xls": ("000040373564", "畜産物流通統計 長期累年 枝肉生産量累年統計 全国（1985〜2024年）"),
    "ryutsu_wagyu_price.xls": ("000040373614", "畜産物流通統計 長期累年 食肉中央卸売市場 和牛計 取引成立頭数と価格（1996〜2024年）"),
}
# 統計品別表（輸出）各年の 1〜12月 確定値の statInfId
EXPORT = {2009: "000007064292", 2010: "000008622909", 2011: "000012679369", 2012: "000018862158", 2013: "000023618924",
          2014: "000028156985", 2015: "000031362183", 2016: "000031528656", 2017: "000031670698", 2018: "000031792534",
          2019: "000031907312", 2020: "000032046080", 2021: "000032254758", 2022: "000040117465", 2023: "000040223253",
          2024: "000040368877", 2025: "000040524662"}


def get(sid, kind):
    with urllib.request.urlopen(urllib.request.Request(URL.format(sid, kind), headers=UA), timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "trade").mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    rows = []
    for name, (sid, desc) in XLS.items():
        b = get(sid, 0); (RAW / name).write_bytes(b)
        rows.append((name, desc, URL.format(sid, 0), hashlib.sha256(b).hexdigest()[:12]))
        time.sleep(0.5)
    for y, sid in EXPORT.items():
        b = get(sid, 1)
        name = f"trade/export_{y}.csv.gz"
        (RAW / name).write_bytes(gzip.compress(b, compresslevel=9, mtime=0))
        rows.append((name, f"貿易統計 統計品別表 輸出 {y}年1〜12月（確定）", URL.format(sid, 1), hashlib.sha256(b).hexdigest()[:12]))
        print("export", y, flush=True); time.sleep(0.5)
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字（gz は展開後） |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["",
              "- 畜産統計の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00500222&tstat=000001015614",
              "- 畜産物流通調査の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00500227&tstat=000001044816",
              "- 貿易統計（統計品別表 輸出）：https://www.e-stat.go.jp/stat-search/files?toukei=00350300&tstat=000001013141&tclass1=000001013183&tclass2=000001013184",
              "- 貿易統計の CSV は全品目の表。gzip で縮めただけで、中身は取得したままのバイト列（`gzip -dc` で戻る）。",
              "- 出典：農林水産省「畜産統計」「畜産物流通統計」、財務省「貿易統計」（いずれも e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
