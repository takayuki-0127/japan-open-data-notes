"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
財務省「貿易統計」輸出入額の推移（年別、世界）と、日本銀行の為替（ドル円、月中平均）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "customs_world_total_yearly.csv": ("https://www.customs.go.jp/toukei/suii/html/data/d41ca.csv", "財務省 貿易統計 輸出入額の推移 世界 年別（総額、千円）"),
    "customs_world_exports_by_commodity_yearly.csv": ("https://www.customs.go.jp/toukei/suii/html/data/d51ca.csv", "同 世界 年別 輸出 主要商品別（金額・数量）"),
    "customs_world_imports_by_commodity_yearly.csv": ("https://www.customs.go.jp/toukei/suii/html/data/d61ca.csv", "同 世界 年別 輸入 主要商品別（金額・数量）"),
    "boj_usdjpy_monthly.json": ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07&startDate=198001&endDate=202512",
                                "日本銀行 時系列統計データ FM08 FXERM07 ドル・円 東京市場 17時時点 月中平均"),
    "boj_import_prices_monthly.json": ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&code=PRCG20_2600000000,PRCG20_2500000000,PRCG20_2400000000,PRCG20_2300000000&startDate=200001&endDate=202512",
                                       "日本銀行 企業物価指数 PR01 輸入物価指数・輸出物価指数 総平均（円ベース・契約通貨ベース、2020年=100）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        p = RAW / name
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
        print(name, p.stat().st_size)
    lines += ["", "出典：財務省「貿易統計」（税関ホームページ 輸出入額の推移）、日本銀行「時系列統計データ」。財務省の CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
