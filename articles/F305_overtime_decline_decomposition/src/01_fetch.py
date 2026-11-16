"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
毎月勤労統計の累積 CSV は 20MB を超えるので、取得したバイト列をそのまま gzip で圧縮して保存する（中身は同じ）。"""
import datetime, gzip, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032189776&fileKind=1"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        b = r.read()
    with gzip.GzipFile(RAW / "maikin_jissu_cumulative.csv.gz", "wb", mtime=0) as f:
        f.write(b)
    today = datetime.date.today().isoformat()
    (RAW / "SOURCES.md").write_text("\n".join([
        "# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|",
        f"| maikin_jissu_cumulative.csv.gz | 厚生労働省「毎月勤労統計調査」全国調査 実数・指数累積データ 実数（CSV、Shift_JIS。gzip で圧縮して保存） | {URL} | {today} |",
        "", "- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450071&tstat=000001011791",
        "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。", ""]), encoding="utf-8")
    print("saved", len(b))

if __name__ == "__main__":
    main()
