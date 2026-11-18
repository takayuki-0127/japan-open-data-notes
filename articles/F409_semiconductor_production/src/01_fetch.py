"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
CU = "https://www.customs.go.jp/toukei/suii/html/data/{}"
BOJ_CODES = [
    # 輸出物価（円ベース・契約通貨ベース）、輸入物価（円ベース）の集積回路。2015年基準（2015-01〜2022-04）と2020年基準（2020-01〜）
    "PRCG15_2400540003", "PRCG20_2400540002",  # 輸出・円・集積回路
    "PRCG15_2300540003", "PRCG20_2300540002",  # 輸出・契約通貨・集積回路
    "PRCG15_2300550005", "PRCG20_2300550006",  # 輸出・契約通貨・モス型メモリ集積回路
    "PRCG15_2600840003", "PRCG20_2600840002",  # 輸入・円・集積回路
    "PRCG20_2201550005",                       # 国内企業物価・集積回路
]
BOJ = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=csv&lang=jp&db=PR01&startDate=201001&endDate=202610&code="
       + ",".join(BOJ_CODES))
FILES = [
    (ES.format("000040172363"), "iip2020_gyoshu_sa.xlsx", "経済産業省「鉱工業指数」2020年基準 業種別 月次 季節調整済指数（生産・出荷・在庫・在庫率、2018年1月〜2026年9月）"),
    (ES.format("000040172367"), "iip2020_hinmoku_sa.xlsx", "経済産業省「鉱工業指数」2020年基準 品目別 月次 季節調整済指数（同）"),
    (ES.format("000032122500"), "iip2015_gyoshu_sa.xlsx", "経済産業省「鉱工業指数」2015年基準 業種別 月次 季節調整済指数（2013年1月〜2023年4月）"),
    (CU.format("d51ma.csv"), "customs_export_monthly.csv", "財務省「貿易統計」輸出入額の推移 世界 月別 輸出 主要商品別（千円、1988年1月〜、Shift_JIS）"),
    (CU.format("d61ma.csv"), "customs_import_monthly.csv", "財務省「貿易統計」輸出入額の推移 世界 月別 輸入 主要商品別（同）"),
    (BOJ, "boj_price_ic.csv", "日本銀行「企業物価指数」輸出・輸入物価指数の集積回路など9系列（時系列統計データ検索サイトの API、CSV、Shift_JIS）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for url, name, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        print(name, len(b))
    rows += ["", "- e-Stat の鉱工業指数の一覧：https://www.e-stat.go.jp/stat-search/files?layout=dataset&toukei=00550300",
             "- 財務省貿易統計 輸出入額の推移：https://www.customs.go.jp/toukei/suii/html/time.htm",
             "- 日本銀行 時系列統計データ検索サイト：https://www.stat-search.boj.or.jp/",
             "- 経済産業省のサイト（www.meti.go.jp/statistics/）は 403 を返したため、同じ指数を e-Stat の掲載分から取った（2026-11-18）。",
             "- 世界の半導体の売上（WSTS）は、業界団体の資料で再配布の扱いがはっきりしないため使っていない。世界の値動きは、日銀の輸出物価（契約通貨ベース、ドル建てなどの値段）で見る。",
             "", "出典：経済産業省「鉱工業指数」（e-Stat）、財務省「貿易統計」、日本銀行「企業物価指数」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
