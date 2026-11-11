"""データの取得。
A: IBM のサンプルデータ「Telco Customer Churn」（架空の通信会社の顧客 7,043人、Apache License 2.0）
B: この連載 F28 の法人データ（国税庁 法人番号公表サイトの全件データから作成。2015年11月以降に設立された法人）
"""
import urllib.request, pathlib
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
SRC = {
    "Telco-Customer-Churn.csv": "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv",
    "houjin_new_2015_2026.csv.gz": "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F28_corporate_survival/data/raw/houjin_new_2015_2026.csv.gz",
}
for name, url in SRC.items():
    p = RAW / name
    if not p.exists():
        urllib.request.urlretrieve(url, p)
    print(name, p.stat().st_size)
