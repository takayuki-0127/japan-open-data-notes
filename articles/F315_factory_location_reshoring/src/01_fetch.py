"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。"""
import datetime, json, pathlib, urllib.request
import pandas as pd

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (research script)"}
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read()
def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    u1 = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040463823&fileKind=0"
    (RAW / "kojo_ritchi_2025.xlsx").write_bytes(get(u1))
    u2 = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=200401"
    r = json.loads(get(u2).decode("utf-8"))["RESULTSET"][0]["VALUES"]
    pd.DataFrame({"ym": r["SURVEY_DATES"], "usdjpy": r["VALUES"]}).to_csv(RAW / "boj_usdjpy_monthly.csv", index=False)
    (RAW / "SOURCES.md").write_text("\n".join([
        "# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|",
        f"| kojo_ritchi_2025.xlsx | 経済産業省「工場立地動向調査」2025年調査 統計表（経年掲載：2006〜2025年） | {u1} | {today} |",
        f"| boj_usdjpy_monthly.csv | 日本銀行「外国為替相場」東京市場 ドル・円 スポット 17時時点／月中平均（FXERM07） | {u2} | {today} |", "",
        "- 工場立地動向調査（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00550510&tstat=000001024255",
        "- 日本銀行 時系列統計データ検索サイト API：https://www.stat-search.boj.or.jp/",
        "- e-Stat のデータは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。", ""]), encoding="utf-8")
if __name__ == "__main__":
    main()
