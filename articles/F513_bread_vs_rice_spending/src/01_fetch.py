"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「家計調査」家計収支編 二人以上の世帯 詳細結果表（年）第4-6表 世帯主の年齢階級別1世帯当たり支出金額、購入数量及び平均価格（2002〜2025年）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
T46 = {2002: "000000331A71", 2003: "000000331AAA", 2004: "000000331AE3", 2005: "000000331B1C", 2006: "000000331D6E", 2007: "000001158916",
       2008: "000002209407", 2009: "000007370343", 2010: "000008635842", 2011: "000012687884", 2012: "000019023734", 2013: "000023621389",
       2014: "000028352478", 2015: "000031370144", 2016: "000031534707", 2017: "000031674349", 2018: "000031795471", 2019: "000031909558",
       2020: "000032048838", 2021: "000032167634", 2022: "000040015264", 2023: "000040140561", 2024: "000040247212", 2025: "000040409549"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, sid in T46.items():
        url = EST.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"kakei_4-6_{y}.{ext}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 家計調査 {y}年 二人以上の世帯 第4-6表 世帯主の年齢階級別（品目分類） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 家計調査 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200561&tstat=000000330001",
              "", "出典：総務省「家計調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
