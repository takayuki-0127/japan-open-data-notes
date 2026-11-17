"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("000031387995", 0, "meti_cvs_timeseries.xlsx", "経済産業省「商業動態統計」時系列データ コンビニエンスストア商品別販売額等及び前年（度、同期、同月）比（月次・四半期・年、全国・経済産業局別、1997年〜）"),
    # 2026-11-18 レビューで変更：000040482959（品目別）は年度平均の表だったため、暦年の年平均の中分類指数の表に替えた
    ("000040482829", 1, "cpi_annual_middle_class.csv", "総務省「消費者物価指数」2025年基準 全国 中分類指数（暦年の年平均、1970〜2025年、CSV、Shift_JIS）"),
    ("000013168605", 4, "pop_pref_2000_2020.xlsx", "総務省「人口推計」長期時系列 第5表 都道府県別人口（各年10月1日現在、2000〜2020年）"),
    ("000040268859", 0, "pop_pref_2020_2024.xlsx", "総務省「人口推計」2024年 第5表 都道府県、男女別人口（各年10月1日現在、2020〜2024年）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for sid, kind, name, desc in FILES:
        url = BASE.format(sid, kind)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：経済産業省「商業動態統計」、総務省「消費者物価指数」「人口推計」（いずれも政府統計の総合窓口 e-Stat）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
