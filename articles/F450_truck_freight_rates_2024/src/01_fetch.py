"""日本銀行 時系列統計データ検索サイトの API から CSV を取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db={db}&code={code}"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
SERIES = [
    ("PR02", "PRCS20_5200000000", "企業向けサービス価格指数（2020年基準） 総平均"),
    ("PR02", "PRCS20_52B0000000", "同 総平均（除く国際運輸）"),
    ("PR02", "PRCS20_5200630002", "同 小類別 道路貨物輸送"),
    ("PR02", "PRCS20_5200650002", "同 品目 宅配便・メール便"),
    ("PR02", "PRCS20_5200650003", "同 品目 自動車貨物輸送（農林水産・食料工業品）"),
    ("PR02", "PRCS20_5200650004", "同 品目 自動車貨物輸送（鉱産品・化学工業品）"),
    ("PR02", "PRCS20_5200650005", "同 品目 自動車貨物輸送（金属機械工業品）"),
    ("PR02", "PRCS20_5200650006", "同 品目 自動車貨物輸送（軽・雑工業品）"),
    ("PR02", "PRCS20_5200630001", "同 小類別 鉄道貨物輸送"),
    ("PR02", "PRCS20_5200730002", "同 小類別 内航貨物輸送"),
    ("PR02", "PRCS20_5200930001", "同 小類別 倉庫"),
    ("PR01", "PRCG20_2200650005", "国内企業物価指数（2020年基準） 品目 軽油"),
]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{today}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for db, code, desc in SERIES:
        url = API.format(db=db, code=code)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            b = r.read()
        (RAW / f"{code}.csv").write_bytes(b)
        lines.append(f"| {code}.csv | {desc}（月次） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print("saved", code, len(b))
    lines += ["", "- 出典：日本銀行「企業向けサービス価格指数」「企業物価指数」（時系列統計データ検索サイトの API）。",
              "- CSV は Shift_JIS（cp932）。先頭に API の応答の情報（STATUS など）の行がある。",
              "- 指数は消費税を除くベース（企業向けサービス価格指数）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
