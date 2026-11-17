"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 総務省「消費者物価指数」2025年基準 品目別価格指数（月次）CSV（e-Stat）
- 気象庁「過去の気象データ検索」月ごとの値（年×月の表、monthly_s3.php）：野菜の主な産地に近い7地点の
  日平均気温（view=a1）、降水量（view=p5）、日照時間（view=p4）。HTML を gzip（mtime=0）で保存。
"""
import gzip, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
CPI = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040482945&fileKind=1"
STATIONS = {"47412": 14, "47629": 40, "47624": 42, "47648": 45, "47610": 48, "47636": 51, "47819": 86}  # 札幌・水戸・前橋・銚子・長野・名古屋・熊本
VIEWS = {"a1": "temp", "p5": "precip", "p4": "sunshine"}
URL = "https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no={p}&block_no={b}&year=&month=&day=&view={v}"


def get(u):
    time.sleep(1.0)
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()


def main():
    (RAW / "jma").mkdir(parents=True, exist_ok=True)
    (RAW / "cpi_item_monthly.csv").write_bytes(get(CPI))
    for b, p in STATIONS.items():
        for v, n in VIEWS.items():
            (RAW / "jma" / f"{b}_{n}.html.gz").write_bytes(gzip.compress(get(URL.format(p=p, b=b, v=v)), mtime=0))


if __name__ == "__main__":
    main()
