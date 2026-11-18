"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
経済産業省「生産動態統計」の年報（e-Stat 掲載分）。経済産業省のサイト（www.meti.go.jp/statistics/）は 403 を返したため、e-Stat から取る。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("000022159811", "nenpo2012_paper.xls", "2012年 年報 紙・パルプ統計（製品時系列表：2008〜2012年の年計と月次、段ボールの消費部門別内訳）"),
    ("000031703020", "nenpo2017_paper.xls", "2017年 年報 紙・パルプ統計（製品時系列表：2013〜2017年）"),
    ("000031961792", "nenpo2020_paper.xls", "2020年 年報 紙・印刷・プラスチック・ゴム製品統計編（製品時系列表：2016〜2020年）"),
    ("000032213834", "nenpo2021.xlsx", "2021年 年報（全品目の月次の実数表）"),
    ("000040077080", "nenpo2022.xlsx", "2022年 年報（同）"),
    ("000040191921", "nenpo2023.xlsx", "2023年 年報（同）"),
    ("000040293825", "nenpo2024.xlsx", "2024年 年報（同）"),
    ("000040475159", "nenpo2025.xlsx", "2025年 年報（同）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for sid, name, desc in FILES:
        url = ES.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=300) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | 経済産業省「生産動態統計」{desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        print(name, len(b))
    rows += ["",
             "- e-Stat の一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00550200&tstat=000001022932",
             "- 経済産業省のサイト（www.meti.go.jp/statistics/tyo/seidou/）は 2026-11-18 に 403 を返したため、同じ年報を e-Stat から取った。",
             "- 2020年以前は分野別の年報（紙・パルプ統計）、2021年以降は全品目をまとめた年報（実数表、月次）。",
             "", "出典：経済産業省「生産動態統計」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
