"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。"""
import pathlib, urllib.request, datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
B = "https://www.e-stat.go.jp/stat-search/file-download?statInfId="
FILES = [
    ("cpi_item_annual.csv", B + "000040482959&fileKind=1", "総務省「消費者物価指数」2025年基準 全国 品目別価格指数（年平均、1970年〜最新年、CSV）"),
    ("jutaku2023_t34_1_rent_timeseries.xlsx", B + "000040354072&fileKind=4", "総務省「令和5年住宅・土地統計調査」時系列統計表 第34-1表 住宅の所有の関係別 1か月当たり家賃及び1畳当たり家賃―全国（1973〜2023年）"),
    ("jutaku2023_t27_rent_by_movein_construction.xlsx", B + "000040353891&fileKind=4", "総務省「令和5年住宅・土地統計調査」第27表 入居時期・建築の時期別 借家数、1畳当たり家賃―全国"),
]
def main():
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {today} |")
    lines += ["", "- 消費者物価指数の時系列：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876",
              "- 令和5年住宅・土地統計調査：https://www.e-stat.go.jp/stat-search/files?toukei=00200522&tstat=000001207800",
              "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
