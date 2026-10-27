"""F45 で使う元データを data/raw/ に取ってくる。

社人研・e-Stat のサイトに接続できる環境なら、そのまま取得できる。
接続できないときは、下の URL をブラウザで開いて同じファイル名で data/raw/ に置く。
"""
import urllib.request
from common import RAW

IPSS = "https://www.ipss.go.jp/pp-shicyoson/j/"
FILES = {
    # 社人研「日本の地域別将来推計人口」令和5(2023)年推計：結果と仮定値（生残率・純移動率・子ども女性比）
    "shicyoson23_3kekka_suikei_kekka.xlsx": IPSS + "shicyoson23/3kekka/suikei_kekka.xlsx",
    "shicyoson23_4shihyo_katei_suvr.xlsx": IPSS + "shicyoson23/4shihyo/katei_suvr.xlsx",
    "shicyoson23_4shihyo_katei_nmigr.xlsx": IPSS + "shicyoson23/4shihyo/katei_nmigr.xlsx",
    "shicyoson23_4shihyo_katei_cwr_0-4sr.xlsx": IPSS + "shicyoson23/4shihyo/katei_cwr_0-4sr.xlsx",
    # 平成30(2018)年推計
    "shicyoson18_3kekka_suikei_kekka.xls": IPSS + "shicyoson18/3kekka/suikei_kekka.xls",
    "shicyoson18_4shihyo_katei_suvr.xls": IPSS + "shicyoson18/4shihyo/katei_suvr.xls",
    "shicyoson18_4shihyo_katei_nmigr.xls": IPSS + "shicyoson18/4shihyo/katei_nmigr.xls",
    "shicyoson18_4shihyo_katei_cwr_0-4sr_revised180621.xls": IPSS + "shicyoson18/4shihyo/katei_cwr_0-4sr_revised180621.xls",
    # 平成25(2013)年推計（都道府県）
    "shicyoson13_3kekka_suikei_ken.xls": IPSS + "shicyoson13/3kekka/suikei_ken.xls",
    "shicyoson13_4shihyo_shihyo_ken.xls": IPSS + "shicyoson13/4shihyo/shihyo_ken.xls",
    # 総務省「令和7年国勢調査 人口等基本集計（不詳補完値）」第2-7表 男女・年齢（5歳階級）別人口（市区町村）
    "census2025_age5_000040506659.xlsx":
        "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000040506659&fileKind=0",
}

if __name__ == "__main__":
    for name, url in FILES.items():
        dest = RAW / name
        if dest.exists():
            print("あり:", name)
            continue
        try:
            urllib.request.urlretrieve(url, dest)
            print("取得:", name)
        except Exception as e:  # noqa: BLE001
            print("取得できませんでした（ブラウザで開いて data/raw/ に置いてください）:", name, url, e)
