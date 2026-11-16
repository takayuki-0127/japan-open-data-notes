"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
# 総務省「労働力調査」基本集計 年平均 第II-2-1表 年齢階級，産業別就業者数
IDS = {2013: "000031573431", 2018: "000032173984", 2019: "000032174132", 2020: "000032174208", 2021: "000032173836",
       2022: "000040008559", 2023: "000040137558", 2024: "000040243359", 2025: "000040403928"}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for y, sid in IDS.items():
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"lfs_II-2-1_{y}.{ext}").write_bytes(b)
        lines.append(f"| lfs_II-2-1_{y}.{ext} | 総務省「労働力調査」基本集計 {y}年平均 第II-2-1表 年齢階級，産業別就業者数 | {url} | {today} |")
        print("saved", y)
    lines += ["", "- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200531&tstat=000001226583",
              "- 2018〜2021年の表は2022年3月に2020年国勢調査を基準に遡って改訂された値（公開日 2022-03-04）。2013年の表は旧基準。",
              "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
