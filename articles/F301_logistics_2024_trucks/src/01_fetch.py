"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
毎月勤労統計の累積 CSV は 20MB を超えるので、取得したバイト列をそのまま gzip で圧縮して保存する（中身は同じ）。"""
import datetime, gzip, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
TRUCK = {  # 自動車輸送統計月報 各年4月分の 総括表（１）輸送トン数・（２）輸送トンキロ
    2021: ("000032124998", "000032124999"), 2022: ("000032218539", "000032218540"), 2023: ("000040081521", "000040081522"),
    2024: ("000040198041", "000040198042"), 2025: ("000040304566", "000040304567"), 2026: ("000040527076", "000040527077"),
}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    url = BASE.format("000032189776", 1)
    b = get(url)
    with gzip.GzipFile(RAW / "maikin_jissu_cumulative.csv.gz", "wb", mtime=0) as f:
        f.write(b)
    lines.append(f"| maikin_jissu_cumulative.csv.gz | 厚生労働省「毎月勤労統計調査」全国調査 実数・指数累積データ 実数（CSV、Shift_JIS。gzip で圧縮して保存） | {url} | {today} |")
    for y, (ton, tkm) in TRUCK.items():
        for sid, kind in ((ton, "ton"), (tkm, "tonkm")):
            url = BASE.format(sid, 0)
            (RAW / f"truck_{kind}_{y}04.xlsx").write_bytes(get(url))
            lines.append(f"| truck_{kind}_{y}04.xlsx | 国土交通省「自動車輸送統計月報」{y}年4月分 総括表（{'１）輸送トン数' if kind == 'ton' else '２）輸送トンキロ'}の推移 | {url} | {today} |")
        print("saved", y)
    lines += ["", "- 毎月勤労統計調査の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450071&tstat=000001011791",
              "- 自動車輸送統計月報の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600330&tstat=000001017236",
              "- いずれも政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
