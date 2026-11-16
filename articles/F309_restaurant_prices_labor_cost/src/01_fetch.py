"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 総務省「消費者物価指数」2025年基準 長期時系列（全国、月次）：中分類指数、財・サービス分類指数（CSV、Shift_JIS）
- 厚生労働省「毎月勤労統計調査」実数・指数累積データ（実数）。20MB を超えるので、取得したバイト列のまま gzip で保存"""
import datetime, gzip, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
FILES = [("cpi_middle_class_index.csv", "000040482943", "消費者物価指数 2025年基準 全国 中分類指数（1970年1月〜最新月）"),
         ("cpi_goods_services_index.csv", "000040482946", "消費者物価指数 2025年基準 全国 財・サービス分類指数（1970年1月〜最新月）")]
MAIKIN = ("maikin_jissu_cumulative.csv.gz", "000032189776", "毎月勤労統計調査 全国調査 実数・指数累積データ 実数（gzip で圧縮して保存）")

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = BASE.format(sid); (RAW / name).write_bytes(get(url))
        lines.append(f"| {name} | 総務省「{desc}」 | {url} | {today} |")
    name, sid, desc = MAIKIN
    url = BASE.format(sid); b = get(url)
    with gzip.GzipFile(RAW / name, "wb", mtime=0) as f:
        f.write(b)
    lines.append(f"| {name} | 厚生労働省「{desc}」 | {url} | {today} |")
    lines += ["", "- 消費者物価指数の時系列データ：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876",
              "- 毎月勤労統計調査：https://www.e-stat.go.jp/stat-search/files?toukei=00450071&tstat=000001011791",
              "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
