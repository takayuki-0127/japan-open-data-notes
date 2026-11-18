"""e-Stat から次を取得して data/raw/ に保存する。ネットが必要。run_all.sh からは呼ばない。
- 作物統計（果樹生産出荷統計）長期累年「品目別結果樹面積、収穫量及び出荷量累年統計」：主な13品目の全国、みかん・ぶどうは47都道府県も
- 生産農業所得統計「年次別農業総産出額及び生産農業所得（全国、累年）」と、各年の「主要農産物の産出額と構成比」（2003〜2024年）
"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
# 果樹の累年（令和6年産の公表で更新されたもの）。全国の表の statInfId。都道府県は全国の次から北海道〜沖縄の順に続く
FRUIT = {"mikan": "000040421665", "ringo": "000040421905", "budou": "000040421953", "nashi": "000040422001",
         "younashi": "000040422049", "momo": "000040422097", "sumomo": "000040422145", "outou": "000040422193",
         "ume": "000040422241", "biwa": "000040422289", "kaki": "000040422337", "kuri": "000040422385", "kiwi": "000040422433"}
PREF_ITEMS = ["mikan", "budou"]
TOTAL = "000040426619"  # 農業総産出額（全国、累年）
TOP = {2003: "000005315967", 2004: "000005143072", 2005: "000001248401", 2006: "000001252140", 2007: "000006695596",
       2008: "000008255413", 2009: "000012660047", 2010: "000013163004", 2011: "000018382747", 2012: "000023621305",
       2013: "000028407520", 2014: "000031399991", 2015: "000031569915", 2016: "000031694493", 2017: "000031813183",
       2018: "000031926889", 2019: "000032073051", 2020: "000032183958", 2021: "000040030997", 2022: "000040156135",
       2023: "000040262921", 2024: "000040426676"}


def get(sid):
    with urllib.request.urlopen(urllib.request.Request(URL.format(sid), headers=UA), timeout=120) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "fruit").mkdir(exist_ok=True); (RAW / "sanshutsu").mkdir(exist_ok=True)
    today = datetime.date.today().isoformat()
    rows = []
    for k, sid in FRUIT.items():
        ids = [(f"fruit/{k}_00.xls", sid)]
        if k in PREF_ITEMS:
            ids += [(f"fruit/{k}_{i:02d}.xls", f"{int(sid) + i:012d}") for i in range(1, 48)]
        for name, s in ids:
            b = get(s); (RAW / name).write_bytes(b)
            rows.append((name, f"果樹生産出荷統計 累年（{k}、地域コード {name[-6:-4]}）", URL.format(s), hashlib.sha256(b).hexdigest()[:12]))
        print("fruit", k, flush=True)
    b = get(TOTAL); (RAW / "sanshutsu/total.xls").write_bytes(b)
    rows.append(("sanshutsu/total.xls", "生産農業所得統計 年次別農業総産出額（全国、累年）", URL.format(TOTAL), hashlib.sha256(b).hexdigest()[:12]))
    for y, s in TOP.items():
        b = get(s); (RAW / f"sanshutsu/top_{y}.xls").write_bytes(b)
        rows.append((f"sanshutsu/top_{y}.xls", f"生産農業所得統計 {y}年 主要農産物の産出額と構成比", URL.format(s), hashlib.sha256(b).hexdigest()[:12]))
        print("top", y, flush=True)
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", "- 果樹の統計表一覧（長期累年）：https://www.e-stat.go.jp/stat-search/files?toukei=00500215&tstat=000001013427&tclass1=000001032287&tclass2=000001037847&tclass3=000001241296",
              "- 生産農業所得統計の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00500206&tstat=000001015617",
              "- 地域コード 00 は全国、01〜47 は都道府県コード。",
              "- 出典：農林水産省「作物統計（果樹生産出荷統計）」「生産農業所得統計」（e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
