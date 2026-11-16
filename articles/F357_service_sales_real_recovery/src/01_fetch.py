"""01_fetch.py : 公式サイトから元データを取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。

取得元
- 総務省「サービス産業動態統計調査」時系列 第1表（e-Stat statInfId=000040518944, aj10.xlsx）
- 総務省「サービス産業動向調査」年報 第3表 事業従事者規模別売上高（2018・2019・2023年, a030.xls）
- 日本銀行「企業向けサービス価格指数（2020年基準）」（時系列統計データ検索サイトの API）
- 総務省「消費者物価指数（2025年基準）」長期時系列 月次（中分類・財サービス分類・品目別, CSV）
"""
import json
import pathlib
import urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"

FILES = [
    # (保存名, statInfId, fileKind)
    ("mbss_ts_t1_aj10.xlsx", "000040518944", 4),
    ("mssi_annual_t3_2018_a030.xls", "000031870669", 0),
    ("mssi_annual_t3_2019_a030.xls", "000032013135", 0),
    ("mssi_annual_t3_2023_a030.xls", "000040215345", 4),
    ("cpi2025_monthly_chubunrui_zmi2025s.csv", "000040482943", 1),
    ("cpi2025_monthly_zaisa_zmi2025b.csv", "000040482946", 1),
    ("cpi2025_monthly_hinmoku_zmi2025a.csv", "000040482945", 1),
]

SPPI_CODES = [
    "5200000000", "4200000000",  # 総平均（消費税込み・除く）
    "5200010002", "5200320001", "5200420001",  # 不動産
    "5200010003", "5200530001", "5200530002", "5200630002", "5200720001",
    "5200920001", "5200930001", "5201120001", "5200530005",  # 運輸・郵便
    "5200010004", "5201220001", "5201320001", "5201420001", "5201520001", "5201620001",  # 情報通信
    "5200010005",  # リース・レンタル
    "5201920001",  # 広告
    "5200010007", "5202020001", "5202120001", "5202220001", "5202320001",
    "5202420001", "5202520001", "5202620001",  # 諸サービス
]


def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    for name, sid, kind in FILES:
        b = get(EST.format(sid, kind))
        (RAW / name).write_bytes(b)
        print(name, len(b))
    codes = ",".join("PRCS20_" + c for c in SPPI_CODES)
    url = ("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp"
           f"&db=PR02&startDate=201301&endDate=202612&code={codes}")
    b = get(url)
    d = json.loads(b)
    assert d["STATUS"] == 200, d.get("MESSAGE")
    (RAW / "boj_sppi2020_monthly.json").write_bytes(b)
    print("boj_sppi2020_monthly.json", len(b), len(d["RESULTSET"]))


if __name__ == "__main__":
    main()
