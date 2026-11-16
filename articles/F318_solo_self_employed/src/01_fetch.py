"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。"""
import datetime, pathlib, urllib.request
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000001082690&fileKind=0"
def main():
    RAW.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (research script)"}), timeout=120) as r:
        (RAW / "lfs_longterm_t4_1.xlsx").write_bytes(r.read())
    today = datetime.date.today().isoformat()
    (RAW / "SOURCES.md").write_text("\n".join([
        "# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|",
        f"| lfs_longterm_t4_1.xlsx | 総務省「労働力調査」基本集計 長期時系列表4(1) 従業上の地位別就業者数（1953年〜、年平均、男女別） | {URL} | {today} |", "",
        "- 労働力調査（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00200531&tstat=000001226583",
        "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。", ""]), encoding="utf-8")
if __name__ == "__main__":
    main()
