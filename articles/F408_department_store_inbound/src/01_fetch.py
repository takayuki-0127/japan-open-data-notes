"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
KK = "https://www.mlit.go.jp/kankocho/content/{}"
FILES = [
    (ES.format("000031387994"), "meti_dept_super_timeseries.xlsx", "経済産業省「商業動態統計」時系列データ 百貨店・スーパー商品別販売額等（月次・年、1980年〜2026年9月）"),
    (ES.format("000031960815"), "meti_pref_2019.xls", "経済産業省「商業動態統計」参考表（年報）2019年 第3部第3表 都道府県別、百貨店・スーパー別、商品別販売額等"),
    (ES.format("000040471260"), "meti_pref_2025.xlsx", "経済産業省「商業動態統計」参考表（年報）2025年 第2表 都道府県別、百貨店・スーパー別、商品別販売額等"),
    ("https://www.jnto.go.jp/statistics/data/_files/20261021_1615-5.xlsx", "jnto_visitors_2003_2026.xlsx", "日本政府観光局（JNTO）「国籍/月別 訪日外客数（2003年～2026年）」（2026年10月21日掲載版）"),
    # 2026-11-18 レビューで変更：000040482959（品目別）は年度平均の表だったため、暦年の年平均の中分類指数の表に替えた
    ("https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482829&fileKind=1", "cpi_annual_middle_class.csv", "総務省「消費者物価指数」2025年基準 全国 中分類指数（暦年の年平均、1970〜2025年、CSV、Shift_JIS）"),
    (KK.format("002020401.xls"), "kanko_2019_annual.xls", "観光庁「訪日外国人消費動向調査」2019年 集計表（暦年・確報）"),
    (KK.format("002020300.xls"), "kanko_2023_annual.xls", "観光庁「インバウンド消費動向調査」2023年 集計表（暦年・確報）"),
    (KK.format("002022649.xls"), "kanko_2024_annual.xls", "観光庁「インバウンド消費動向調査」2024年 集計表（暦年・確報）"),
    (KK.format("002025515.xls"), "kanko_2025_annual.xls", "観光庁「インバウンド消費動向調査」2025年 集計表（暦年・確報）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for url, name, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "- e-Stat の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550030 （商業動態統計調査。時系列データと参考表（年報））",
             "- 観光庁の一覧：https://www.mlit.go.jp/kankocho/tokei_hakusyo/gaikokujinshohidoko.html",
             "- 日本百貨店協会の免税売上の統計は、取得を試みたが接続できなかったため使っていない（2026-11-18）。",
             "", "出典：経済産業省「商業動態統計」（e-Stat）、日本政府観光局「訪日外客数」、観光庁「訪日外国人消費動向調査」「インバウンド消費動向調査」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
