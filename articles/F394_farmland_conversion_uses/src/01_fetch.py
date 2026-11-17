"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
農林水産省「農地の移動と転用（農地の権利移動・借賃等調査）」用途別の農地転用面積の合計（都道府県別、2010〜2023年）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
IDS = {2010: "000014904050", 2011: "000023595552", 2012: "000028080704", 2013: "000030744763", 2014: "000031445509",
       2015: "000031675349", 2016: "000031799766", 2017: "000031915826", 2018: "000032060490", 2019: "000032183708",
       2020: "000040018997", 2021: "000040141583", 2022: "000040248101", 2023: "000040414265"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "農林水産省「農地の移動と転用（農地の権利移動・借賃等調査）」用途別の農地等の転用 ― 用途別の農地転用面積の合計（全国・ブロック・都道府県、ha）。", "",
            "| ファイル | 年 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, sid in IDS.items():
        url = ES.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        fn = f"conv_use_{y}" + (".xlsx" if b[:2] == b"PK" else ".xls")
        (RAW / fn).write_bytes(b)
        rows.append(f"| {fn} | {y} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(fn, len(b))
    rows += ["", "出典：農林水産省「農地の移動と転用（農地の権利移動・借賃等調査）」（e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
