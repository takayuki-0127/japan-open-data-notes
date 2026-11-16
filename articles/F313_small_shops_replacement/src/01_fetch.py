"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。"""
import pathlib, urllib.request, datetime
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000002253716&fileKind=0"
NAME = "shogyo2007_vol1_sangyo_soukatsu.xls"
def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        (RAW / NAME).write_bytes(r.read())
    today = datetime.date.today().isoformat()
    (RAW / "SOURCES.md").write_text("\n".join([
        "# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|",
        f"| {NAME} | 経済産業省「平成19年商業統計表 第1巻 産業編（総括表）」（第1表：産業分類細分類別、年次別の事業所数（法人・個人別）、従業者数、年間商品販売額、商品手持額、売場面積、1982〜2007年） | {URL} | {today} |", "",
        "- 商業統計調査（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00550020&tstat=000001023268",
        "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。", ""]), encoding="utf-8")
if __name__ == "__main__":
    main()
