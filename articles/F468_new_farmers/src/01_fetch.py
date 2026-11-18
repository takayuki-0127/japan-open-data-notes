"""e-Stat から農林水産省「新規就農者調査」の各年の「表1 就農形態別新規就農者数」（年齢別）を取得して data/raw/ に保存する。
ネットが必要。run_all.sh からは呼ばない。各年の表には直近の2〜4年分が載る。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
# 公表の年（調査の年）: statInfId
FILES = {"2008": "000004589374", "2009": "000007368951", "2009b": "000008296901", "2010": "000012662734", "2011": "000017011324",
         "2012": "000026737780", "2013": "000031315051", "2014": "000031450435", "2015": "000031531132", "2016": "000031657572",
         "2017": "000031782099", "2018": "000031888094", "2019": "000032157757", "2020": "000032157770", "2021": "000032239050",
         "2022": "000040090402", "2023": "000040201055", "2024": "000040447030", "2025": "000040492350"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, sid in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(URL.format(sid), headers=UA), timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"shinki_t1_{k}.{ext}"
        (RAW / name).write_bytes(b)
        rows.append((name, f"新規就農者調査 表1 就農形態別（年齢別）新規就農者数（{k} 公表分）", URL.format(sid), hashlib.sha256(b).hexdigest()[:12]))
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", "- 新規就農者調査の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00500236&tstat=000001015194",
              "- 2009 は平成20年・19年の表、2009b は平成21年・20年の表（同じ調査年月で2つ公表されている）。",
              "- 出典：農林水産省「新規就農者調査」（e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
