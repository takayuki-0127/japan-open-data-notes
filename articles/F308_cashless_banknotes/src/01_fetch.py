"""元データを公式サイトから取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 日本銀行「時系列統計データ検索サイト」API（JSON）：銀行券発行高（平均残高・月末の券種別）、無担保コールレート
- 総務省「家計消費状況調査」（e-Stat）年次 第2-1表 全国・地方・都市階級別 電子マネーの利用状況"""
import datetime, json, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BOJ = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}"
BOJ_SETS = {
    "boj_MD01_banknotes_avg.json": ("MD01", ["MABS2AN116", "MABS2AN117"]),
    "boj_MD05_banknotes_by_denomination.json": ("MD05", ["MACCV2", "MACCV2@01", "MACCV2@02", "MACCV201D5", "MACCV2@03", "MACCV2@05"]),
    "boj_FM02_call_rate.json": ("FM02", ["STRACLUCON"]),
}
ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
EMONEY = {2010: "000008636857", 2011: "000012715329", 2012: "000019218334", 2013: "000023621874", 2014: "000028391687", 2015: "000031372070", 2016: "000031532330", 2017: "000031670996", 2018: "000031794542", 2019: "000031909496", 2020: "000032048689", 2021: "000032167490", 2022: "000040013674", 2023: "000040140906", 2024: "000040247278", 2025: "000040408066"}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, (db, codes) in BOJ_SETS.items():
        url = BOJ.format(db=db, codes=",".join(codes))
        b = get(url)
        json.loads(b)  # JSON であることを確かめる
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 日本銀行 時系列統計データ（{db}：{', '.join(codes)}） | {url} | {today} |")
    for y, sid in EMONEY.items():
        url = ESTAT.format(sid); b = get(url)
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"kakei_shohi_emoney_{y}.{ext}").write_bytes(b)
        lines.append(f"| kakei_shohi_emoney_{y}.{ext} | 総務省「家計消費状況調査」{y}年 第2-1表 電子マネーの利用状況 | {url} | {today} |")
        print("saved", y)
    lines += ["", "- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/ （API 利用）",
              "- 家計消費状況調査の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00200565&tstat=000000660001",
              "- 出典を示して加工して使う（日本銀行の利用規約、政府標準利用規約（第2.0版））。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
